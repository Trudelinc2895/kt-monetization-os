"""merge billing and branding heads

Revision ID: c4f7e9a1b2d3
Revises: 5d9f6e2a4c31, a1b2c3d4e5f6
Create Date: 2026-05-15 22:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union


revision: str = "c4f7e9a1b2d3"
down_revision: Union[str, tuple[str, str], None] = ("5d9f6e2a4c31", "a1b2c3d4e5f6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
