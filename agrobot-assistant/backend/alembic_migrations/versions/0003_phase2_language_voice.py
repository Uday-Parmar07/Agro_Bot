"""phase2 language voice

Revision ID: 0003_phase2_language
Revises: 0002_phase1_persistence
Create Date: 2026-08-23 00:02:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_phase2_language"
down_revision: Union[str, None] = "0002_phase1_persistence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    columns = _column_names("users")
    if "preferred_language" not in columns:
        op.add_column(
            "users",
            sa.Column("preferred_language", sa.String(), nullable=False, server_default="en"),
        )


def downgrade() -> None:
    if "preferred_language" in _column_names("users"):
        op.drop_column("users", "preferred_language")
