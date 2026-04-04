"""backend/api/routers/notifications.py — In-app notification endpoints.

Endpoints:
  GET /notifications           — list recent notifications (unread first)
  PUT /notifications/read-all  — mark all as read
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select, update

from api.core.deps import CurrentUser, DB
from api.models.notification import UserNotification

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/notifications")
async def list_notifications(
    current_user: CurrentUser,
    db: DB,
    limit: int = 20,
):
    """Return recent notifications for the authenticated user, unread first."""
    result = await db.execute(
        select(UserNotification)
        .where(UserNotification.user_id == current_user.id)
        .order_by(UserNotification.read.asc(), UserNotification.created_at.desc())
        .limit(limit)
    )
    notifications = result.scalars().all()

    return {
        "notifications": [
            {
                "id": str(n.id),
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "read": n.read,
                "data": n.data or {},
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ],
        "unread_count": sum(1 for n in notifications if not n.read),
    }


@router.put("/notifications/read-all", status_code=200)
async def mark_all_read(current_user: CurrentUser, db: DB):
    """Mark all notifications as read for the authenticated user."""
    await db.execute(
        update(UserNotification)
        .where(UserNotification.user_id == current_user.id)
        .values(read=True)
    )
    await db.commit()
    logger.info("[notifications] All marked read for user=%s", current_user.id)
    return {"status": "ok"}
