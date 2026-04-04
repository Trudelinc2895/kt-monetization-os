"""
backend/api/routers/reverse_engineering.py — Module 8: Reverse Engineering

  POST /reverse/analyze    — analyze competitor and generate replication playbook (auth required)
  GET  /reverse/history    — list user's past results (auth required)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.core.deps import CurrentUser, DB
from api.services.reverse_engineering_service import run_reverse_engineering
from api.services.usage_service import check_and_charge_usage, record_usage

logger = logging.getLogger(__name__)
router = APIRouter()


class ReverseEngineeringRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=8000, description="Input content")
    context: str | None = Field(None, max_length=2000)


class ReverseEngineeringResponse(BaseModel):
    result: str
    module: str = "reverse_engineering"


@router.post("/reverse/analyze", response_model=ReverseEngineeringResponse, status_code=status.HTTP_201_CREATED)
async def analyze_reverse_engineering(body: ReverseEngineeringRequest, current_user: CurrentUser, db: DB):
    from api.services.billing_service import has_feature
    if not has_feature(current_user.plan, "automation"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reverse Engineering nécessite un plan Pro ou supérieur.",
        )

    within_limit, _ = await check_and_charge_usage(current_user, db)
    if not within_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Limite mensuelle atteinte. Upgrade ton plan.",
        )

    result, tokens = await run_reverse_engineering(body.content, body.context or "")
    await record_usage(current_user.id, "reverse_engineering", tokens, db)
    return ReverseEngineeringResponse(result=result)
