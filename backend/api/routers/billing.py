"""
backend/api/routers/billing.py
Stripe billing — checkout, webhook, portal
SECURITY: webhook signature verified on every call
"""
from __future__ import annotations
import logging
from typing import Annotated
import stripe
from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv(".env")
from api.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
stripe.api_key = settings.STRIPE_SECRET_KEY

PLAN_PRICE_MAP = {
    "pro": settings.STRIPE_PRICE_PRO_MONTHLY_ID,
    "business": settings.STRIPE_PRICE_BUSINESS_MONTHLY_ID,
}


class CheckoutRequest(BaseModel):
    plan: str
    email: str


@router.post("/checkout-session")
async def create_checkout_session(body: CheckoutRequest):
    price_id = PLAN_PRICE_MAP.get(body.plan)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {body.plan}")
    session = stripe.checkout.Session.create(
        customer_email=body.email,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=settings.STRIPE_CHECKOUT_SUCCESS_URL,
        cancel_url=settings.STRIPE_CHECKOUT_CANCEL_URL,
    )
    return {"url": session.url}


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: Annotated[str | None, Header(alias="stripe-signature")] = None,
):
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature")
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Invalid Stripe webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    logger.info(f"[webhook] {event['type']} id={event['id']}")
    return {"received": True, "type": event["type"]}
