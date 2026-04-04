"""
backend/api/routers/digital_leverage.py — Module 7: Digital Leverage

  POST /leverage/generate  — generate leverage strategy (auth required)
  GET  /leverage/history   — list user's past results (auth required)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.core.deps import CurrentUser, DB
from api.services.digital_leverage_service import run_digital_leverage
from api.services.usage_service import check_and_charge_usage, record_usage

logger = logging.getLogger(__name__)
router = APIRouter()


class DigitalLeverageRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=8000, description="Input content")
    context: str | None = Field(None, max_length=2000)


class DigitalLeverageResponse(BaseModel):
    result: str
    module: str = "digital_leverage"


@router.post("/leverage/generate", response_model=DigitalLeverageResponse, status_code=status.HTTP_201_CREATED)
async def generate_digital_leverage(body: DigitalLeverageRequest, current_user: CurrentUser, db: DB):
    from api.services.billing_service import has_feature
    if not has_feature(current_user.plan, "api_access"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Digital Leverage nécessite un plan Pro ou supérieur.",
        )

    within_limit, _ = await check_and_charge_usage(current_user, db)
    if not within_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Limite mensuelle atteinte. Upgrade ton plan.",
        )

    result, tokens = await run_digital_leverage(body.content, body.context or "")
    await record_usage(current_user.id, "digital_leverage", tokens, db)
    return DigitalLeverageResponse(result=result)
