"""
backend/api/services/billing_service.py

Single source of truth for all monetization logic:
- Plan config (never trust client-side values)
- Stripe customer management
- Subscription sync from webhook events
- Entitlement computation from DB state
- Webhook idempotency
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models.subscription import Subscription
from api.models.user import User
from api.models.webhook_event import WebhookEvent

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


# ─── Plan configuration — server-side ONLY, never from client ────────────────
def _build_plans() -> dict[str, dict]:
    return {
        "free": {
            "name": "Free",
            "price_monthly_usd": 0,
            "price_yearly_usd": 0,
            "stripe_price_monthly": None,
            "stripe_price_yearly": None,
            "limits": {
                "ai_messages_per_month": 50,
                "conversations": 5,
                "active_modules": 1,
            },
            "features": ["1 AI module", "50 messages/month", "Community support"],
        },
        "pro": {
            "name": "Pro",
            "price_monthly_usd": 29,
            "price_yearly_usd": 290,
            "stripe_price_monthly": settings.STRIPE_PRICE_PRO_MONTHLY_ID or None,
            "stripe_price_yearly": settings.STRIPE_PRICE_PRO_YEARLY_ID or None,
            "limits": {
                "ai_messages_per_month": 1000,
                "conversations": 100,
                "active_modules": 5,
            },
            "features": ["5 AI modules", "1,000 messages/month", "Priority support", "API access"],
        },
        "business": {
            "name": "Business",
            "price_monthly_usd": 99,
            "price_yearly_usd": 990,
            "stripe_price_monthly": settings.STRIPE_PRICE_BUSINESS_MONTHLY_ID or None,
            "stripe_price_yearly": settings.STRIPE_PRICE_BUSINESS_YEARLY_ID or None,
            "limits": {
                "ai_messages_per_month": -1,  # -1 = unlimited
                "conversations": -1,
                "active_modules": 10,
            },
            "features": [
                "All 10 AI modules",
                "Unlimited messages",
                "Dedicated support",
                "White-label option",
                "API access",
            ],
        },
    }


PLANS_CONFIG: dict[str, dict] = _build_plans()

# Reverse map: stripe_price_id → plan slug (built once at import)
_PRICE_TO_PLAN: dict[str, str] = {
    price_id: slug
    for slug, cfg in PLANS_CONFIG.items()
    for key in ("stripe_price_monthly", "stripe_price_yearly")
    if (price_id := cfg.get(key))
}


def price_id_to_plan(price_id: str | None) -> str:
    if not price_id:
        return "free"
    return _PRICE_TO_PLAN.get(price_id, "pro")


# ─── Stripe customer ──────────────────────────────────────────────────────────

async def get_or_create_stripe_customer(user: User, db: AsyncSession) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=user.full_name,
        metadata={"user_id": str(user.id), "app": settings.APP_NAME},
    )
    user.stripe_customer_id = customer.id
    db.add(user)
    await db.commit()
    logger.info(f"[billing] Created Stripe customer {customer.id} for user {user.id}")
    return customer.id


# ─── Subscription sync ────────────────────────────────────────────────────────

async def get_active_subscription(user_id: uuid.UUID, db: AsyncSession) -> Subscription | None:
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def sync_subscription_from_stripe(
    stripe_sub: dict[str, Any], db: AsyncSession
) -> Subscription | None:
    """
    Upsert Subscription row from Stripe subscription object.
    Idempotent — safe to call multiple times with same data.
    Syncs User.plan to match subscription status.
    """
    stripe_sub_id = stripe_sub["id"]
    stripe_customer_id = stripe_sub["customer"]

    result = await db.execute(
        select(User).where(User.stripe_customer_id == stripe_customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning(f"[billing] No user for Stripe customer {stripe_customer_id}")
        return None

    price_id = None
    items = stripe_sub.get("items", {}).get("data", [])
    if items:
        price_id = items[0]["price"]["id"]
    plan = price_id_to_plan(price_id)

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        sub = Subscription(user_id=user.id)
        db.add(sub)

    sub.stripe_subscription_id = stripe_sub_id
    sub.stripe_price_id = price_id
    sub.plan = plan
    sub.status = stripe_sub["status"]
    sub.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)

    if stripe_sub.get("current_period_start"):
        sub.current_period_start = datetime.fromtimestamp(
            stripe_sub["current_period_start"], tz=timezone.utc
        )
    if stripe_sub.get("current_period_end"):
        sub.current_period_end = datetime.fromtimestamp(
            stripe_sub["current_period_end"], tz=timezone.utc
        )

    # Keep User.plan in sync
    if stripe_sub["status"] == "active":
        user.plan = plan
    elif stripe_sub["status"] in ("canceled", "unpaid", "incomplete_expired"):
        user.plan = "free"
    db.add(user)

    await db.commit()
    await db.refresh(sub)
    logger.info(f"[billing] Synced sub {stripe_sub_id} plan={plan} status={stripe_sub['status']}")
    return sub


async def handle_checkout_completed(session: dict[str, Any], db: AsyncSession) -> None:
    """
    Link Stripe customer to our user on checkout.session.completed.
    client_reference_id = str(user.id) — set when creating the checkout session.
    """
    customer_id = session.get("customer")
    user_id_str = session.get("client_reference_id")
    if not customer_id or not user_id_str:
        logger.warning("[billing] checkout.session.completed missing customer or client_reference_id")
        return

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        logger.error(f"[billing] Invalid client_reference_id: {user_id_str}")
        return

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.error(f"[billing] No user for id={user_id_str}")
        return

    if not user.stripe_customer_id:
        user.stripe_customer_id = customer_id
        db.add(user)
        await db.commit()
        logger.info(f"[billing] Linked customer {customer_id} to user {user_id}")


# ─── Webhook idempotency ──────────────────────────────────────────────────────

async def is_event_processed(event_id: str, db: AsyncSession) -> bool:
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.stripe_event_id == event_id)
    )
    return result.scalar_one_or_none() is not None


async def mark_event(
    event_id: str,
    event_type: str,
    status: str,
    error: str | None,
    db: AsyncSession,
) -> None:
    we = WebhookEvent(
        stripe_event_id=event_id,
        event_type=event_type,
        processed_at=datetime.now(timezone.utc),
        status=status,
        error=error,
    )
    db.add(we)
    await db.commit()


# ─── Entitlement computation — always from DB, never from client ──────────────

def compute_entitlements(user: User, sub: Subscription | None) -> dict:
    plan_key = user.plan if user.plan in PLANS_CONFIG else "free"

    # Degrade to free if subscription is in bad standing
    if sub and sub.status in ("past_due", "canceled", "unpaid", "incomplete_expired"):
        plan_key = "free"

    plan_cfg = PLANS_CONFIG[plan_key]
    now = datetime.now(timezone.utc)

    is_sub_active = (
        sub is not None
        and sub.status == "active"
        and (sub.current_period_end is None or sub.current_period_end > now)
    )
    effective_status = "active" if (plan_key == "free" or is_sub_active) else (
        sub.status if sub else "inactive"
    )

    return {
        "plan": plan_key,
        "status": effective_status,
        "limits": plan_cfg["limits"],
        "features": plan_cfg["features"],
        "subscription": {
            "id": sub.stripe_subscription_id if sub else None,
            "current_period_end": (
                sub.current_period_end.isoformat() if sub and sub.current_period_end else None
            ),
            "cancel_at_period_end": sub.cancel_at_period_end if sub else False,
        },
    }
