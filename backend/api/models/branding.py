"""White-label branding settings per workspace/platform."""
from __future__ import annotations
import uuid
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base

class Branding(Base):
    __tablename__ = "branding_settings"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    company_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    accent_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    support_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    custom_domain: Mapped[str | None] = mapped_column(String(253), nullable=True)
