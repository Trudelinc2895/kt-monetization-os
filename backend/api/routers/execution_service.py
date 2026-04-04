"""
backend/api/routers/execution_service.py — Module 10: Execution Service

  POST /execution/plan   — transform idea into executable plan (auth required)
  GET  /execution/history — list user's past results (auth required)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.core.deps import CurrentUser, DB
from api.services.execution_service_service import run_execution_service
from api.services.usage_service import check_and_charge_usage, record_usage

logger = logging.getLogger(__name__)
router = APIRouter()


class ExecutionServiceRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=8000, description="Input content")
    context: str | None = Field(None, max_length=2000)


class ExecutionServiceResponse(BaseModel):
    result: str
    module: str = "execution_service"


@router.post("/execution/plan", response_model=ExecutionServiceResponse, status_code=status.HTTP_201_CREATED)
async def plan_execution_service(body: ExecutionServiceRequest, current_user: CurrentUser, db: DB):
    from api.services.billing_service import has_feature
    if not has_feature(current_user.plan, "automation"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Execution Service nécessite un plan Pro ou supérieur.",
        )

    within_limit, _ = await check_and_charge_usage(current_user, db)
    if not within_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Limite mensuelle atteinte. Upgrade ton plan.",
        )

    result, tokens = await run_execution_service(body.content, body.context or "")
    await record_usage(current_user.id, "execution_service", tokens, db)
    return ExecutionServiceResponse(result=result)
