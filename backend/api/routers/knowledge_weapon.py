"""
backend/api/routers/knowledge_weapon.py — Module 6: Knowledge Weapon

  POST /knowledge/extract  — extract structured action plan from content (auth required)
  GET  /knowledge/history  — list user's past results (auth required)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.core.deps import CurrentUser, DB
from api.services.knowledge_weapon_service import run_knowledge_weapon
from api.services.usage_service import check_and_charge_usage, record_usage

logger = logging.getLogger(__name__)
router = APIRouter()


class KnowledgeWeaponRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=8000, description="Input content")
    context: str | None = Field(None, max_length=2000)


class KnowledgeWeaponResponse(BaseModel):
    result: str
    module: str = "knowledge_weapon"


@router.post("/knowledge/extract", response_model=KnowledgeWeaponResponse, status_code=status.HTTP_201_CREATED)
async def extract_knowledge_weapon(body: KnowledgeWeaponRequest, current_user: CurrentUser, db: DB):
    from api.services.billing_service import has_feature
    if not has_feature(current_user.plan, "api_access"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Knowledge Weapon nécessite un plan Pro ou supérieur.",
        )

    within_limit, _ = await check_and_charge_usage(current_user, db)
    if not within_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Limite mensuelle atteinte. Upgrade ton plan.",
        )

    result, tokens = await run_knowledge_weapon(body.content, body.context or "")
    await record_usage(current_user.id, "knowledge_weapon", tokens, db)
    return KnowledgeWeaponResponse(result=result)
