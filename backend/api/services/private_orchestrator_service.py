"""Private/admin-only orchestrator scaffold for Nanovia."""
from __future__ import annotations

from typing import Any

import httpx

from api.config import settings

PRIVATE_ORCHESTRATOR_CONTEXT_KEY = "nanovia-private-admin-orchestrator"
PRIVATE_ORCHESTRATOR_ENDPOINTS = [
    "/api/v1/admin/orchestrator/overview",
    "/api/v1/admin/orchestrator/agents",
]

_DEFAULT_AGENT_CATALOG: dict[str, dict[str, str]] = {
    "operator": {
        "name": "AI Personal Operator",
        "description": "Assistant executif pour organisation, priorites et operations.",
    },
    "ghost_agency": {
        "name": "Ghost Automation Agency",
        "description": "Prospection et sequences commerciales admin-only en contexte prive.",
    },
    "decision_engine": {
        "name": "AI Decision Engine",
        "description": "Analyse de scenarios et arbitrages operationnels.",
    },
}


def get_allowed_agent_keys() -> list[str]:
    configured = settings.PRIVATE_ORCHESTRATOR_ALLOWED_AGENTS or list(_DEFAULT_AGENT_CATALOG)
    filtered: list[str] = []
    for key in configured:
        if key in _DEFAULT_AGENT_CATALOG and key not in filtered:
            filtered.append(key)
    return filtered or list(_DEFAULT_AGENT_CATALOG)


def get_static_agent_catalog() -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "name": _DEFAULT_AGENT_CATALOG[key]["name"],
            "description": _DEFAULT_AGENT_CATALOG[key]["description"],
            "allowed": True,
        }
        for key in get_allowed_agent_keys()
    ]


async def fetch_upstream_health() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.PRIVATE_ORCHESTRATOR_UPSTREAM_URL}/health")
            response.raise_for_status()
            data = response.json()
        return {
            "ok": data.get("status") == "ok",
            "status": str(data.get("status", "unknown")),
            "service": data.get("service"),
            "version": data.get("version"),
            "detail": None,
        }
    except httpx.TimeoutException:
        return {
            "ok": False,
            "status": "timeout",
            "service": None,
            "version": None,
            "detail": "Timed out while contacting the private orchestrator upstream.",
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": "unavailable",
            "service": None,
            "version": None,
            "detail": str(exc),
        }


async def fetch_upstream_agents() -> tuple[list[dict[str, Any]], str]:
    allowed_keys = set(get_allowed_agent_keys())
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.PRIVATE_ORCHESTRATOR_UPSTREAM_URL}/agents")
            response.raise_for_status()
            payload = response.json()

        agents = [
            {
                "key": item["key"],
                "name": item["name"],
                "description": item["description"],
                "allowed": True,
            }
            for item in payload
            if item.get("key") in allowed_keys
        ]
        return (agents or get_static_agent_catalog(), "upstream")
    except Exception:
        return (get_static_agent_catalog(), "fallback")


async def build_private_orchestrator_overview() -> dict[str, Any]:
    upstream = await fetch_upstream_health()
    return {
        "context_key": PRIVATE_ORCHESTRATOR_CONTEXT_KEY,
        "enabled": settings.PRIVATE_ORCHESTRATOR_ENABLED,
        "release_stage": "scaffold",
        "access": {
            "admin_only": True,
            "feature_flagged": True,
            "public_saas_exposure": False,
            "destructive_merge_with_my_agent_hub": False,
            "requires_private_admin_surface": True,
            "production_ip_allowlist_required": True,
        },
        "capabilities": {
            "agent_catalog_read": True,
            "upstream_health_read": True,
            "prompt_execution": False,
            "terminal_access": False,
            "filesystem_access": False,
            "browser_access": False,
            "billing_mutation": False,
            "user_impersonation": False,
        },
        "allowed_agent_keys": get_allowed_agent_keys(),
        "upstream": upstream,
        "endpoints": PRIVATE_ORCHESTRATOR_ENDPOINTS,
        "notes": [
            "Disabled by default via PRIVATE_ORCHESTRATOR_ENABLED.",
            "Admin-only surface; never link from public SaaS navigation.",
            "No terminal, filesystem, browser, billing mutation or user impersonation capabilities in this slice.",
            "No destructive merge with my_agent_hub is performed here; this is isolated repo-side scaffolding only.",
        ],
    }
