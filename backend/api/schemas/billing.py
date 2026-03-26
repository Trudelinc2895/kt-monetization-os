"""
backend/api/schemas/billing.py — Billing request/response schemas
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class PlanLimits(BaseModel):
    ai_messages_per_month: int
    conversations: int
    active_modules: int


class PlanPublic(BaseModel):
    slug: str
    name: str
    price_monthly_usd: int
    price_yearly_usd: int
    limits: PlanLimits
    features: list[str]


class CheckoutRequest(BaseModel):
    plan: str = Field(..., pattern="^(pro|business)$")
    interval: str = Field(default="monthly", pattern="^(monthly|yearly)$")


class CheckoutResponse(BaseModel):
    url: str


class PortalResponse(BaseModel):
    url: str


class SubscriptionInfo(BaseModel):
    id: str | None
    plan: str
    status: str
    current_period_end: str | None
    cancel_at_period_end: bool


class EntitlementsResponse(BaseModel):
    plan: str
    status: str
    limits: dict[str, Any]
    features: list[str]
    subscription: dict[str, Any]


class CreditPurchaseRequest(BaseModel):
    quantity: int = Field(default=1, ge=1, le=100)


class CreditPurchaseResponse(BaseModel):
    url: str
    credits_to_add: int
