"""
backend/api/routers/offer_generator.py — Module 9: Offer Generator

  POST /offer/generate  — generate an irresistible offer (auth required)
  GET  /offer/history   — list user's past results (auth required)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.core.deps import CurrentUser, DB
from api.services.offer_generator_service import run_offer_generator
from api.services.usage_service import check_and_charge_usage, record_usage

logger = logging.getLogger(__name__)
router = APIRouter()


class OfferGeneratorRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=8000, description="Input content")
    context: str | None = Field(None, max_length=2000)


class OfferGeneratorResponse(BaseModel):
    result: str
    module: str = "offer_generator"


@router.post("/offer/generate", response_model=OfferGeneratorResponse, status_code=status.HTTP_201_CREATED)
async def generate_offer_generator(body: OfferGeneratorRequest, current_user: CurrentUser, db: DB):
    from api.services.billing_service import has_feature
    if not has_feature(current_user.plan, "api_access"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Offer Generator nécessite un plan Pro ou supérieur.",
        )

    within_limit, _ = await check_and_charge_usage(current_user, db)
    if not within_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Limite mensuelle atteinte. Upgrade ton plan.",
        )

    result, tokens = await run_offer_generator(body.content, body.context or "")
    await record_usage(current_user.id, "offer_generator", tokens, db)
    return OfferGeneratorResponse(result=result)
