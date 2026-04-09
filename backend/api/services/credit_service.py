from __future__ import annotations

import logging
import uuid
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.credit_ledger import CreditLedger
from api.models.user import User

logger = logging.getLogger(__name__)

LedgerType = Literal["purchase", "usage", "adjustment"]

try:
    from prometheus_client import Counter
    _kt_credits_deducted = Counter(
        "kt_credits_deducted_total",
        "Overage credits deducted from user balance",
        ["reason"],
    )
    _kt_credits_added = Counter(
        "kt_credits_added_total",
        "Credits added to user balance",
        ["source"],
    )
    _HAS_PROM = True
except Exception:
    _HAS_PROM = False


async def _get_user_for_update(user_id: uuid.UUID, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id).with_for_update())
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError(f"User {user_id} not found")
    return user


async def get_balance(user_id: uuid.UUID, db: AsyncSession) -> int:
    result = await db.execute(
        select(CreditLedger.balance_after)
        .where(CreditLedger.user_id == user_id)
        .order_by(CreditLedger.created_at.desc(), CreditLedger.id.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if latest is not None:
        return int(latest)

    result_user = await db.execute(select(User.credits).where(User.id == user_id))
    user_credits = result_user.scalar_one_or_none()
    return int(user_credits or 0)


async def _apply_ledger_change(
    *,
    user_id: uuid.UUID,
    delta: int,
    entry_type: LedgerType,
    db: AsyncSession,
    source: str,
    reason: str | None = None,
    reference: str | None = None,
    idempotency_key: str | None = None,
    note: str | None = None,
    commit: bool = True,
) -> CreditLedger:
    if delta == 0:
        raise ValueError("Credit delta cannot be zero")

    if idempotency_key:
        existing_result = await db.execute(
            select(CreditLedger).where(CreditLedger.idempotency_key == idempotency_key)
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            return existing

    user = await _get_user_for_update(user_id, db)
    current_balance = await get_balance(user_id, db)
    new_balance = current_balance + delta
    if new_balance < 0:
        raise ValueError("Insufficient credits")

    entry = CreditLedger(
        user_id=user_id,
        type=entry_type,
        amount=delta,
        balance_after=new_balance,
        source=source,
        reference=reference,
        idempotency_key=idempotency_key,
        note=note or reason,
    )
    db.add(entry)

    # Backward-compatible denormalized projection for legacy code paths.
    user.credits = new_balance
    db.add(user)

    await db.flush()
    if commit:
        await db.commit()

    return entry


async def add_credits(
    user_id: uuid.UUID,
    amount: int,
    source: str,
    db: AsyncSession,
    idempotency_key: str | None = None,
    note: str | None = None,
    reference: str | None = None,
) -> CreditLedger:
    if amount <= 0:
        raise ValueError(f"add_credits: amount must be positive, got {amount}")

    entry = await _apply_ledger_change(
        user_id=user_id,
        delta=amount,
        entry_type="purchase",
        source=source,
        db=db,
        idempotency_key=idempotency_key,
        reference=reference,
        note=note,
    )
    if _HAS_PROM:
        _kt_credits_added.labels(source=source).inc(amount)
    logger.info("[credits] +%d user=%s balance=%d source=%s", amount, user_id, entry.balance_after, source)
    return entry


async def deduct_credits(
    user: User,
    source: str,
    db: AsyncSession,
    amount: int = 1,
    note: str | None = None,
    idempotency_key: str | None = None,
    reference: str | None = None,
) -> bool:
    if amount <= 0:
        raise ValueError("deduct_credits amount must be positive")

    try:
        entry = await _apply_ledger_change(
            user_id=user.id,
            delta=-amount,
            entry_type="usage",
            source=source,
            reason=note,
            db=db,
            idempotency_key=idempotency_key,
            reference=reference,
            commit=True,
        )
    except ValueError:
        return False

    user.credits = entry.balance_after
    if _HAS_PROM:
        _kt_credits_deducted.labels(reason=source).inc(amount)
    logger.info("[credits] -%d user=%s balance=%d source=%s", amount, user.id, entry.balance_after, source)
    return True


async def deduct_credits_by_user_id(
    user_id: uuid.UUID,
    amount: int,
    reason: str,
    db: AsyncSession,
    reference: str | None = None,
    idempotency_key: str | None = None,
    note: str | None = None,
    commit: bool = True,
) -> CreditLedger:
    if amount <= 0:
        raise ValueError("deduct_credits_by_user_id amount must be positive")

    entry = await _apply_ledger_change(
        user_id=user_id,
        delta=-amount,
        entry_type="usage",
        source=reason,
        db=db,
        idempotency_key=idempotency_key,
        reference=reference,
        note=note,
        commit=commit,
    )
    if _HAS_PROM:
        _kt_credits_deducted.labels(reason=reason).inc(amount)
    return entry


async def adjust_credits(
    user_id: uuid.UUID,
    amount: int,
    source: str,
    db: AsyncSession,
    note: str | None = None,
    reference: str | None = None,
) -> CreditLedger:
    if amount == 0:
        raise ValueError("adjust_credits amount cannot be zero")

    return await _apply_ledger_change(
        user_id=user_id,
        delta=amount,
        entry_type="adjustment",
        source=source,
        db=db,
        note=note,
        reference=reference,
    )


async def get_history(
    user_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 50,
) -> list[dict]:
    result = await db.execute(
        select(CreditLedger)
        .where(CreditLedger.user_id == user_id)
        .order_by(CreditLedger.created_at.desc())
        .limit(limit)
    )
    entries = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "type": e.type,
            "amount": e.amount,
            "balance_after": e.balance_after,
            "source": e.source,
            "reference": e.reference,
            "note": e.note,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]
