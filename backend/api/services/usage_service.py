"""
backend/api/services/usage_service.py
Usage tracking and plan-limit enforcement for metered AI consumption.

GPT-4o-mini pricing: $0.000002 per token (~$0.002 / 1K tokens).

IMPORTANT: Plan limits are read from PLANS_CONFIG (billing_service) — single
source of truth. Never hardcode limits here.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import redis.asyncio as aioredis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models.usage_record import UsageRecord

# Cost per token in USD (gpt-4o-mini blended rate)
_COST_PER_TOKEN = Decimal("0.000002")

# ── Prometheus counters (graceful fallback if not installed) ──────────────────
try:
    from prometheus_client import Counter
    _kt_messages_total = Counter(
        "kt_usage_messages_total",
        "Total AI messages processed",
        ["plan", "module", "reason"],
    )
    _kt_overage_total = Counter(
        "kt_overage_credits_deducted_total",
        "Overage credits deducted for usage",
        ["plan"],
    )
    _HAS_PROM = True
except Exception:
    _HAS_PROM = False

_redis_pool: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
    return _redis_pool


def _month_key(user_id: uuid.UUID) -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"usage:{user_id}:{month}"


def _get_plan_limit(plan: str) -> int:
    """
    Read ai_messages_per_month from PLANS_CONFIG — single source of truth.
    Returns -1 for unlimited. Falls back to free limit on unknown plan.
    """
    from api.services.billing_service import PLANS_CONFIG
    cfg = PLANS_CONFIG.get(plan, PLANS_CONFIG["free"])
    return cfg["limits"].get("ai_messages_per_month", 50)


async def record_usage(
    user_id: uuid.UUID,
    module: str,
    tokens_used: int,
    db: AsyncSession,
    unit_cost_credits: int = 0,
) -> UsageRecord:
    """
    Persist a usage record and increment the Redis monthly counter.
    Returns the saved UsageRecord.
    unit_cost_credits: 0 = within plan, 1 = 1 overage credit deducted.
    """
    cost = _COST_PER_TOKEN * tokens_used
    record = UsageRecord(
        user_id=user_id,
        module=module,
        tokens_used=max(tokens_used, 0),
        cost_usd=cost,
        unit_cost_credits=unit_cost_credits,
    )
    db.add(record)
    await db.flush()

    # Increment Redis counter for fast limit checks (fire-and-forget; fail open)
    try:
        redis = await _get_redis()
        key = _month_key(user_id)
        count = await redis.incr(key)
        if count == 1:
            # Set TTL: expire after ~35 days to auto-clean old keys
            await redis.expire(key, 35 * 24 * 3600)
    except Exception:
        pass

    if _HAS_PROM:
        _kt_messages_total.labels(plan='unknown', module=module, reason='recorded').inc()

    return record


async def get_monthly_usage(user_id: uuid.UUID, db: AsyncSession) -> dict:
    """
    Return usage stats for the current calendar month.
    Message count from Redis (fast), token/cost totals from DB.
    """
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    month_start = datetime.strptime(month, "%Y-%m").replace(tzinfo=timezone.utc)

    # Redis counter for message count
    messages_count = 0
    try:
        redis = await _get_redis()
        raw = await redis.get(_month_key(user_id))
        messages_count = int(raw) if raw else 0
    except Exception:
        pass

    # DB aggregates for token and cost totals
    result = await db.execute(
        select(
            func.coalesce(func.sum(UsageRecord.tokens_used), 0).label("tokens_total"),
            func.coalesce(func.sum(UsageRecord.cost_usd), Decimal("0")).label("cost_total"),
            func.count(UsageRecord.id).label("db_count"),
        ).where(
            UsageRecord.user_id == user_id,
            UsageRecord.created_at >= month_start,
        )
    )
    row = result.one()

    # Prefer DB count as ground truth if Redis is out of sync
    if messages_count == 0 and row.db_count > 0:
        messages_count = row.db_count

    return {
        "month": month,
        "messages_count": messages_count,
        "tokens_total": int(row.tokens_total),
        "cost_usd_total": float(row.cost_total),
    }


async def check_usage_limit(
    user_id: uuid.UUID,
    plan: str,
    db: AsyncSession,  # noqa: ARG001 — reserved for DB-backed fallback
) -> bool:
    """
    Return True if the user is within their monthly message limit.
    Returns True (fail open) if Redis is unavailable.
    -1 limit means unlimited (business plan).
    """
    limit = _get_plan_limit(plan)
    if limit == -1:
        return True

    try:
        redis = await _get_redis()
        raw = await redis.get(_month_key(user_id))
        count = int(raw) if raw else 0
        return count < limit
    except Exception:
        # Redis unavailable — fail open to avoid blocking users
        return True


async def check_and_charge_usage(
    user: object,
    db: AsyncSession,
    *,
    usage_type: str = "ai_message",
) -> tuple[bool, str]:
    """Backward-compatible wrapper to central usage_metering_service."""
    from fastapi import HTTPException
    from api.services.usage_metering_service import check_and_charge_usage as _metering_check

    try:
        allowed, reason, _ = await _metering_check(
            user=user, usage_type=usage_type, quantity=1, db=db, module="gate"
        )
    except HTTPException:
        return False, "limit_exceeded"
    return allowed, reason


async def get_usage_history(
    user_id: uuid.UUID,
    db: AsyncSession,
    days: int = 30,
    limit: int = 200,
) -> list[dict]:
    """
    Return per-record usage history for the last N days.
    Used by analytics dashboard (data lock-in feature).
    """
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(UsageRecord)
        .where(UsageRecord.user_id == user_id, UsageRecord.created_at >= cutoff)
        .order_by(UsageRecord.created_at.desc())
        .limit(limit)
    )
    records = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "module": r.module,
            "tokens_used": r.tokens_used,
            "cost_usd": float(r.cost_usd),
            "unit_cost_credits": r.unit_cost_credits,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


async def get_module_breakdown(user_id: uuid.UUID, db: AsyncSession, days: int = 30) -> list[dict]:
    """
    Return usage grouped by module for the last N days.
    Powers the analytics pie chart.
    """
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            UsageRecord.module,
            func.count(UsageRecord.id).label("message_count"),
            func.coalesce(func.sum(UsageRecord.tokens_used), 0).label("tokens_total"),
            func.coalesce(func.sum(UsageRecord.cost_usd), Decimal("0")).label("cost_total"),
            func.coalesce(func.sum(UsageRecord.unit_cost_credits), 0).label("credits_spent"),
        )
        .where(UsageRecord.user_id == user_id, UsageRecord.created_at >= cutoff)
        .group_by(UsageRecord.module)
        .order_by(func.count(UsageRecord.id).desc())
    )
    rows = result.all()
    return [
        {
            "module": r.module,
            "message_count": r.message_count,
            "tokens_total": int(r.tokens_total),
            "cost_usd_total": float(r.cost_total),
            "credits_spent": int(r.credits_spent),
        }
        for r in rows
    ]

_redis_pool: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
    return _redis_pool


def _month_key(user_id: uuid.UUID) -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"usage:{user_id}:{month}"


async def record_usage(
    user_id: uuid.UUID,
    module: str,
    tokens_used: int,
    db: AsyncSession,
) -> UsageRecord:
    """
    Persist a usage record and increment the Redis monthly counter.
    Returns the saved UsageRecord.
    """
    cost = _COST_PER_TOKEN * tokens_used
    record = UsageRecord(
        user_id=user_id,
        module=module,
        tokens_used=max(tokens_used, 0),
        cost_usd=cost,
    )
    db.add(record)
    await db.flush()

    # Increment Redis counter for fast limit checks (fire-and-forget; fail open)
    try:
        redis = await _get_redis()
        key = _month_key(user_id)
        count = await redis.incr(key)
        if count == 1:
            # Set TTL: expire after ~35 days to auto-clean old keys
            await redis.expire(key, 35 * 24 * 3600)
    except Exception:
        pass

    return record


async def get_monthly_usage(user_id: uuid.UUID, db: AsyncSession) -> dict:
    """
    Return usage stats for the current calendar month.
    Message count from Redis (fast), token/cost totals from DB.
    """
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    month_start = datetime.strptime(month, "%Y-%m").replace(tzinfo=timezone.utc)

    # Redis counter for message count
    messages_count = 0
    try:
        redis = await _get_redis()
        raw = await redis.get(_month_key(user_id))
        messages_count = int(raw) if raw else 0
    except Exception:
        pass

    # DB aggregates for token and cost totals
    result = await db.execute(
        select(
            func.coalesce(func.sum(UsageRecord.tokens_used), 0).label("tokens_total"),
            func.coalesce(func.sum(UsageRecord.cost_usd), Decimal("0")).label("cost_total"),
            func.count(UsageRecord.id).label("db_count"),
        ).where(
            UsageRecord.user_id == user_id,
            UsageRecord.created_at >= month_start,
        )
    )
    row = result.one()

    # Prefer DB count as ground truth if Redis is out of sync
    if messages_count == 0 and row.db_count > 0:
        messages_count = row.db_count

    return {
        "month": month,
        "messages_count": messages_count,
        "tokens_total": int(row.tokens_total),
        "cost_usd_total": float(row.cost_total),
    }


async def check_usage_limit(
    user_id: uuid.UUID,
    plan: str,
    db: AsyncSession,  # noqa: ARG001 — reserved for DB-backed fallback
) -> bool:
    """
    Return True if the user is within their monthly message limit.
    Returns True (fail open) if Redis is unavailable.
    -1 limit means unlimited (business plan).
    """
    limit = _PLAN_LIMITS.get(plan, _PLAN_LIMITS["free"])
    if limit == -1:
        return True

    try:
        redis = await _get_redis()
        raw = await redis.get(_month_key(user_id))
        count = int(raw) if raw else 0
        return count < limit
    except Exception:
        # Redis unavailable — fail open to avoid blocking users
        return True


async def get_usage_history(
    user_id: uuid.UUID,
    db: AsyncSession,
    days: int = 30,
    limit: int = 200,
) -> list[dict]:
    """
    Return per-record usage history for the last N days.
    Used by analytics dashboard (data lock-in feature).
    """
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(UsageRecord)
        .where(UsageRecord.user_id == user_id, UsageRecord.created_at >= cutoff)
        .order_by(UsageRecord.created_at.desc())
        .limit(limit)
    )
    records = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "module": r.module,
            "tokens_used": r.tokens_used,
            "cost_usd": float(r.cost_usd),
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


async def get_module_breakdown(user_id: uuid.UUID, db: AsyncSession, days: int = 30) -> list[dict]:
    """
    Return usage grouped by module for the last N days.
    Powers the analytics pie chart.
    """
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            UsageRecord.module,
            func.count(UsageRecord.id).label("message_count"),
            func.coalesce(func.sum(UsageRecord.tokens_used), 0).label("tokens_total"),
            func.coalesce(func.sum(UsageRecord.cost_usd), Decimal("0")).label("cost_total"),
        )
        .where(UsageRecord.user_id == user_id, UsageRecord.created_at >= cutoff)
        .group_by(UsageRecord.module)
        .order_by(func.count(UsageRecord.id).desc())
    )
    rows = result.all()
    return [
        {
            "module": r.module,
            "message_count": r.message_count,
            "tokens_total": int(r.tokens_total),
            "cost_usd_total": float(r.cost_total),
        }
        for r in rows
    ]
