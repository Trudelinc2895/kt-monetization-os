"""
backend/api/routers/mobile.py

Endpoints dédiés au client mobile :
  GET  /modules/catalog        → catalogue modules avec visible_on_mobile
  GET  /modules/me             → modules accessibles par l'user (entitlements)
  GET  /users/me/sessions      → sessions actives (device tracking)
  DELETE /users/me/sessions/{id} → révoquer une session (kill switch)
  POST /notifications/register-device → enregistrer push token
  GET  /notifications/me       → notifications non lues
  PATCH /notifications/{id}/read → marquer lue
  GET  /vip/overview           → KPIs + alertes (role=vip ou admin)
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from api.core.deps import CurrentUser, DB
from api.models.device_session import DeviceSession
from api.models.notification import UserNotification
from api.services.billing_service import PLANS_CONFIG, compute_entitlements, get_active_subscription

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Modules config (mobile-aware) ───────────────────────────────────────────
MODULES_CATALOG = [
    {
        "key": "operator",
        "name": "AI Personal Operator",
        "description": "Ton assistant exécutif IA — emails, décisions, organisation",
        "category": "productivity",
        "icon": "robot",
        "enabled": True,
        "visible_on_mobile": True,
        "entitlements_required": ["free"],
        "roles_allowed": ["user", "admin", "vip"],
    },
    {
        "key": "content_cloner",
        "name": "Content Cloner Engine",
        "description": "Transforme contenu viral en multi-format automatiquement",
        "category": "marketing",
        "icon": "copy",
        "enabled": False,  # coming soon
        "visible_on_mobile": False,
        "entitlements_required": ["pro"],
        "roles_allowed": ["user", "admin", "vip"],
    },
    {
        "key": "micro_saas",
        "name": "Micro-SaaS Builder",
        "description": "Génère des outils SaaS ultra-spécifiques en 24h",
        "category": "automation",
        "icon": "code",
        "enabled": False,
        "visible_on_mobile": False,
        "entitlements_required": ["pro"],
        "roles_allowed": ["user", "admin", "vip"],
    },
    {
        "key": "ghost_agency",
        "name": "Ghost Automation Agency",
        "description": "Automatise prospection et outreach pour clients",
        "category": "sales",
        "icon": "ghost",
        "enabled": False,
        "visible_on_mobile": True,
        "entitlements_required": ["pro"],
        "roles_allowed": ["user", "admin", "vip"],
    },
    {
        "key": "decision_engine",
        "name": "AI Decision Engine",
        "description": "Prise de décision augmentée — business, stratégie, investissement",
        "category": "intelligence",
        "icon": "brain",
        "enabled": False,
        "visible_on_mobile": True,
        "entitlements_required": ["pro"],
        "roles_allowed": ["user", "admin", "vip"],
    },
    {
        "key": "knowledge_weapon",
        "name": "Knowledge Weapon System",
        "description": "Transforme livres/vidéos en plans d'action exécutables",
        "category": "intelligence",
        "icon": "book",
        "enabled": False,
        "visible_on_mobile": False,
        "entitlements_required": ["pro"],
        "roles_allowed": ["user", "admin", "vip"],
    },
    {
        "key": "digital_leverage",
        "name": "Digital Leverage Builder",
        "description": "Crée des assets digitaux qui travaillent pour toi",
        "category": "automation",
        "icon": "trending-up",
        "enabled": False,
        "visible_on_mobile": False,
        "entitlements_required": ["business"],
        "roles_allowed": ["user", "admin", "vip"],
    },
    {
        "key": "reverse_engineering",
        "name": "AI Reverse Engineering",
        "description": "Analyse concurrents → recrée en mieux avec IA",
        "category": "intelligence",
        "icon": "search",
        "enabled": False,
        "visible_on_mobile": False,
        "entitlements_required": ["business"],
        "roles_allowed": ["user", "admin", "vip"],
    },
    {
        "key": "offer_generator",
        "name": "Hyper-Personalized Offer Generator",
        "description": "Génère des offres ultra-ciblées par profil client",
        "category": "sales",
        "icon": "target",
        "enabled": False,
        "visible_on_mobile": False,
        "entitlements_required": ["pro"],
        "roles_allowed": ["user", "admin", "vip"],
    },
    {
        "key": "execution_service",
        "name": "Execution-as-a-Service",
        "description": "Tu délègues — l'IA exécute tout à ta place",
        "category": "automation",
        "icon": "zap",
        "enabled": False,
        "visible_on_mobile": False,
        "entitlements_required": ["business"],
        "roles_allowed": ["user", "admin", "vip"],
    },
]

_PLAN_HIERARCHY = {"free": 0, "pro": 1, "business": 2}


def _user_has_access(user_plan: str, required: list[str]) -> bool:
    user_level = _PLAN_HIERARCHY.get(user_plan, 0)
    return any(_PLAN_HIERARCHY.get(r, 0) <= user_level for r in required)


# ─── Module catalog ───────────────────────────────────────────────────────────

@router.get("/modules/catalog")
async def get_modules_catalog(current_user: CurrentUser, db: DB):
    """Full module catalog with user access computed per module."""
    result = []
    for m in MODULES_CATALOG:
        entry = dict(m)
        entry["is_available"] = (
            m["enabled"]
            and current_user.plan in m["entitlements_required"]
            or _user_has_access(current_user.plan, m["entitlements_required"])
        )
        result.append(entry)
    return result


@router.get("/modules/catalog/mobile")
async def get_mobile_modules(current_user: CurrentUser, db: DB):
    """Modules visible_on_mobile only — for the mobile client."""
    return [
        {
            **m,
            "is_available": m["enabled"] and _user_has_access(current_user.plan, m["entitlements_required"]),
        }
        for m in MODULES_CATALOG
        if m["visible_on_mobile"]
    ]


@router.get("/modules/me")
async def get_my_modules(current_user: CurrentUser, db: DB):
    """Modules the current user has access to (enabled + plan check)."""
    return [
        {**m, "is_available": True}
        for m in MODULES_CATALOG
        if m["enabled"] and _user_has_access(current_user.plan, m["entitlements_required"])
    ]


# ─── Sessions (device tracking + kill switch) ─────────────────────────────────

class DeviceRegistrationRequest(BaseModel):
    push_token: str = Field(..., min_length=10)
    device_id: str = Field(..., min_length=10)
    device_name: str = Field(default="Mobile", max_length=255)
    platform: str = Field(default="ios", pattern="^(ios|android|web)$")


@router.post("/notifications/register-device", status_code=status.HTTP_201_CREATED)
async def register_device(body: DeviceRegistrationRequest, current_user: CurrentUser, db: DB, request: Request):
    """Register or update push token for a device. Idempotent by device_id."""
    result = await db.execute(
        select(DeviceSession).where(
            DeviceSession.user_id == current_user.id,
            DeviceSession.device_id == body.device_id,
        )
    )
    session = result.scalar_one_or_none()

    ip = request.client.host if request.client else None

    if session is None:
        session = DeviceSession(
            user_id=current_user.id,
            device_id=body.device_id,
            device_name=body.device_name,
            platform=body.platform,
            push_token=body.push_token,
            ip_address=ip,
        )
        db.add(session)
    else:
        session.push_token = body.push_token
        session.device_name = body.device_name
        session.last_seen = datetime.now(timezone.utc)
        session.ip_address = ip
        session.is_active = True

    await db.commit()
    return {"registered": True, "device_id": body.device_id}


@router.get("/users/me/sessions")
async def get_my_sessions(current_user: CurrentUser, db: DB):
    """List all active device sessions for the current user."""
    result = await db.execute(
        select(DeviceSession).where(
            DeviceSession.user_id == current_user.id,
            DeviceSession.is_active == True,  # noqa: E712
        ).order_by(DeviceSession.last_seen.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "device_id": s.device_id,
            "device_name": s.device_name,
            "platform": s.platform,
            "ip_address": s.ip_address,
            "last_seen": s.last_seen.isoformat(),
        }
        for s in sessions
    ]


@router.delete("/users/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(session_id: str, current_user: CurrentUser, db: DB):
    """Revoke (kill) a device session. Users can only revoke their own."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    result = await db.execute(
        select(DeviceSession).where(
            DeviceSession.id == sid,
            DeviceSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_active = False
    await db.commit()


# ─── Notifications ────────────────────────────────────────────────────────────

@router.get("/notifications/me")
async def get_my_notifications(current_user: CurrentUser, db: DB):
    """Return last 50 notifications for current user."""
    result = await db.execute(
        select(UserNotification)
        .where(UserNotification.user_id == current_user.id)
        .order_by(UserNotification.created_at.desc())
        .limit(50)
    )
    notifs = result.scalars().all()
    return [
        {
            "id": str(n.id),
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "read": n.read,
            "data": n.data,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifs
    ]


@router.patch("/notifications/{notification_id}/read", status_code=status.HTTP_200_OK)
async def mark_notification_read(notification_id: str, current_user: CurrentUser, db: DB):
    """Mark a notification as read."""
    try:
        nid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID")

    result = await db.execute(
        select(UserNotification).where(
            UserNotification.id == nid,
            UserNotification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.read = True
    await db.commit()
    return {"read": True}


# ─── VIP Panel ────────────────────────────────────────────────────────────────

@router.get("/vip/overview")
async def get_vip_overview(current_user: CurrentUser, db: DB):
    """VIP dashboard — KPIs + alerts. Requires vip or admin role."""
    if current_user.plan not in ("pro", "business") and current_user.plan != "admin":
        raise HTTPException(status_code=403, detail="VIP access requires Pro or Business plan")

    sub = await get_active_subscription(current_user.id, db)
    entitlements = compute_entitlements(current_user, sub)

    from api.services.usage_service import get_monthly_usage
    usage = await get_monthly_usage(current_user.id, db)

    msg_limit = entitlements["limits"]["ai_messages_per_month"]
    msg_used = usage.get("messages_count", 0)
    msg_display = "∞" if msg_limit == -1 else str(msg_limit)
    trend = "stable"
    if msg_limit != -1 and msg_limit > 0:
        ratio = msg_used / msg_limit
        trend = "warning" if ratio >= 0.8 else ("critical" if ratio >= 1.0 else "stable")

    kpis = [
        {
            "key": "plan",
            "label": "Plan actuel",
            "value": current_user.plan.upper(),
            "trend": "stable",
        },
        {
            "key": "messages_used",
            "label": "Messages utilisés ce mois",
            "value": msg_used,
            "limit": msg_display,
            "unit": "msgs",
            "trend": trend,
        },
        {
            "key": "tokens_used",
            "label": "Tokens consommés",
            "value": usage.get("tokens_total", 0),
            "unit": "tokens",
            "trend": "stable",
        },
        {
            "key": "cost_usd",
            "label": "Coût IA ce mois",
            "value": round(usage.get("cost_usd_total", 0.0), 4),
            "unit": "USD",
            "trend": "stable",
        },
        {
            "key": "modules_available",
            "label": "Modules actifs",
            "value": entitlements["limits"]["active_modules"],
            "unit": "modules",
            "trend": "stable",
        },
        {
            "key": "credits",
            "label": "Crédits disponibles",
            "value": getattr(current_user, "credits", 0),
            "unit": "crédits",
            "trend": "stable",
        },
    ]

    alerts = []
    if sub and sub.status == "past_due":
        alerts.append({
            "id": "billing-past-due",
            "severity": "critical",
            "message": "Paiement en retard — mettre à jour ta carte de crédit",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    return {
        "kpis": kpis,
        "alerts": alerts,
        "subscription": {
            "status": sub.status if sub else "free",
            "current_period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
        },
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/vip/kpis")
async def get_vip_kpis(current_user: CurrentUser, db: DB):
    """KPIs synthétiques — usage des modules, progression."""
    if current_user.plan not in ("pro", "business"):
        raise HTTPException(status_code=403, detail="Requires Pro or Business plan")
    sub = await get_active_subscription(current_user.id, db)
    entitlements = compute_entitlements(current_user, sub)
    return {"kpis": [
        {"key": "plan", "label": "Plan", "value": current_user.plan, "trend": "stable"},
        {"key": "active_modules", "label": "Modules", "value": entitlements["limits"]["active_modules"]},
        {"key": "ai_messages", "label": "Msgs/mois", "value": entitlements["limits"]["ai_messages_per_month"]},
    ]}
