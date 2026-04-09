"""add credit ledger reference column

Revision ID: 4d2f8f7d2f10
Revises: b9f3a2c1d8e7
Create Date: 2026-04-06 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4d2f8f7d2f10"
down_revision: Union[str, None] = "b9f3a2c1d8e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("credit_ledger", sa.Column("reference", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_credit_ledger_reference"), "credit_ledger", ["reference"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_credit_ledger_reference"), table_name="credit_ledger")
    op.drop_column("credit_ledger", "reference")
