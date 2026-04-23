"""Admin-only private orchestrator routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.config import settings
from api.core.deps import AdminUser
from api.schemas.private_orchestrator import (
    PrivateOrchestratorAgentsResponse,
    PrivateOrchestratorOverview,
)
from api.services import private_orchestrator_service

router = APIRouter()


def _require_private_orchestrator_enabled() -> None:
    if not settings.PRIVATE_ORCHESTRATOR_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/orchestrator/overview", response_model=PrivateOrchestratorOverview)
async def admin_private_orchestrator_overview(_: AdminUser):
    """Return the bounded contract for the private orchestrator slice."""
    _require_private_orchestrator_enabled()
    return await private_orchestrator_service.build_private_orchestrator_overview()


@router.get("/orchestrator/agents", response_model=PrivateOrchestratorAgentsResponse)
async def admin_private_orchestrator_agents(_: AdminUser):
    """Return the allowlisted private/admin agent catalog."""
    _require_private_orchestrator_enabled()
    agents, source = await private_orchestrator_service.fetch_upstream_agents()
    return {
        "enabled": True,
        "source": source,
        "agents": agents,
    }
