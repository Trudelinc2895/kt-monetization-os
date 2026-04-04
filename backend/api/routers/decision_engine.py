"""
backend/api/routers/decision_engine.py — Module 5: Decision Engine

  POST /decision/analyze   — analyze a situation and return structured decision (auth required)
  GET  /decision/history   — list user's past results (auth required)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.core.deps import CurrentUser, DB
from api.services.decision_engine_service import run_decision_engine
from api.services.usage_service import check_and_charge_usage, record_usage

logger = logging.getLogger(__name__)
router = APIRouter()


class DecisionEngineRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=8000, description="Input content")
    context: str | None = Field(None, max_length=2000)


class DecisionEngineResponse(BaseModel):
    result: str
    module: str = "decision_engine"


@router.post("/decision/analyze", response_model=DecisionEngineResponse, status_code=status.HTTP_201_CREATED)
async def analyze_decision_engine(body: DecisionEngineRequest, current_user: CurrentUser, db: DB):
    from api.services.billing_service import has_feature
    if not has_feature(current_user.plan, "automation"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Decision Engine nécessite un plan Pro ou supérieur.",
        )

    within_limit, _ = await check_and_charge_usage(current_user, db)
    if not within_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Limite mensuelle atteinte. Upgrade ton plan.",
        )

    result, tokens = await run_decision_engine(body.content, body.context or "")
    await record_usage(current_user.id, "decision_engine", tokens, db)
    return DecisionEngineResponse(result=result)
