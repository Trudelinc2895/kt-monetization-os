"""Central monetization usage metering service."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.usage_record import UsageRecord
from api.models.user import User
from api.services.credit_service import deduct_credits_by_user_id
from api.services.entitlements_service import get_entitlements, get_remaining_quota
from api.services.usage_service import _get_redis, record_usage


async def _mark_idempotency(idempotency_key: str) -> bool:
    redis = await _get_redis()
    created = await redis.set(f"usage:idempotency:{idempotency_key}", "1", nx=True, ex=3600)
    return bool(created)


async def check_and_charge_usage(
    user: User,
    usage_type: str,
    quantity: int,
    db: AsyncSession,
    *,
    module: str = "generic",
    tokens_used: int = 0,
    idempotency_key: str | None = None,
) -> tuple[bool, str, UsageRecord | None]:
    """Validate entitlement + charge overage if needed + log usage atomically."""
    if quantity <= 0:
        return True, "no_usage", None

    if idempotency_key:
        try:
            if not await _mark_idempotency(idempotency_key):
                return True, "duplicate", None
        except Exception:
            # Keep fail-open for idempotency infra, not for business checks.
            pass

    entitlements = await get_entitlements(user, db)
    quota = await get_remaining_quota(user, db, "ai_messages_per_month")

    if quota["limit"] == -1 or quota["used"] + quantity <= quota["limit"]:
        usage_row = await record_usage(
            user_id=user.id,
            module=module,
            tokens_used=tokens_used,
            db=db,
            unit_cost_credits=0,
        )
        await db.commit()
        return True, "within_limit", usage_row

    overage_allowed = entitlements.get("features_enabled", {}).get("overage_allowed", False)
    if not overage_allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Usage limit reached. Upgrade plan or purchase credits.",
        )

    credits_to_deduct = quantity
    async with db.begin_nested():
        try:
            usage_row = await record_usage(
                user_id=user.id,
                module=module,
                tokens_used=tokens_used,
                db=db,
                unit_cost_credits=credits_to_deduct,
            )
            await deduct_credits_by_user_id(
                user_id=user.id,
                amount=credits_to_deduct,
                reason=f"overage:{usage_type}",
                db=db,
                reference=str(usage_row.id),
                idempotency_key=idempotency_key,
                note=f"Overage usage charge for {usage_type}",
                commit=False,
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient credits for overage usage.",
            )

    await db.commit()
    return True, "credit_charged", usage_row
