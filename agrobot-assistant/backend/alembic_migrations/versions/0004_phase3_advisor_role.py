"""phase3 advisor role

Revision ID: 0004_phase3_advisor
Revises: 0003_phase2_language
Create Date: 2026-08-23 00:03:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_phase3_advisor"
down_revision: Union[str, None] = "0003_phase2_language"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _column_names(table_name: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    if "role" not in _column_names("users"):
        op.add_column("users", sa.Column("role", sa.String(), nullable=False, server_default="farmer"))

    if "advisor_farmer_links" not in _table_names():
        op.create_table(
            "advisor_farmer_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("advisor_id", sa.Integer(), nullable=False),
            sa.Column("farmer_id", sa.Integer(), nullable=False),
            sa.Column("assigned_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["advisor_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["farmer_id"], ["users.id"]),
        )
        op.create_index("ix_advisor_farmer_links_id", "advisor_farmer_links", ["id"])
        op.create_index("ix_advisor_farmer_links_advisor_id", "advisor_farmer_links", ["advisor_id"])
        op.create_index("ix_advisor_farmer_links_farmer_id", "advisor_farmer_links", ["farmer_id"])


def downgrade() -> None:
    if "advisor_farmer_links" in _table_names():
        op.drop_index("ix_advisor_farmer_links_farmer_id", table_name="advisor_farmer_links")
        op.drop_index("ix_advisor_farmer_links_advisor_id", table_name="advisor_farmer_links")
        op.drop_index("ix_advisor_farmer_links_id", table_name="advisor_farmer_links")
        op.drop_table("advisor_farmer_links")
    if "role" in _column_names("users"):
        op.drop_column("users", "role")
