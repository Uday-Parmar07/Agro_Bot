"""phase4 financial tools

Revision ID: 0005_phase4_finance
Revises: 0004_phase3_advisor
Create Date: 2026-08-23 00:04:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_phase4_finance"
down_revision: Union[str, None] = "0004_phase3_advisor"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _table_names()
    if "scheme_records" not in tables:
        op.create_table(
            "scheme_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("farm_id", sa.Integer(), nullable=False),
            sa.Column("scheme_name", sa.String(), nullable=False),
            sa.Column("source_url", sa.String(), nullable=True),
            sa.Column("summary", sa.String(), nullable=True),
            sa.Column("eligibility_text", sa.String(), nullable=True),
            sa.Column("estimated_benefit", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="saved"),
            sa.Column("applied_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["farm_id"], ["farms.id"]),
        )
        op.create_index("ix_scheme_records_id", "scheme_records", ["id"])
        op.create_index("ix_scheme_records_farm_id", "scheme_records", ["farm_id"])

    if "harvest_outcomes" not in tables:
        op.create_table(
            "harvest_outcomes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("farm_crop_id", sa.Integer(), nullable=False),
            sa.Column("actual_yield", sa.Float(), nullable=False),
            sa.Column("unit", sa.String(), nullable=False),
            sa.Column("sale_price_per_unit", sa.Float(), nullable=False),
            sa.Column("harvested_at", sa.Date(), nullable=False),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["farm_crop_id"], ["farm_crops.id"]),
        )
        op.create_index("ix_harvest_outcomes_id", "harvest_outcomes", ["id"])
        op.create_index("ix_harvest_outcomes_farm_crop_id", "harvest_outcomes", ["farm_crop_id"])


def downgrade() -> None:
    if "harvest_outcomes" in _table_names():
        op.drop_index("ix_harvest_outcomes_farm_crop_id", table_name="harvest_outcomes")
        op.drop_index("ix_harvest_outcomes_id", table_name="harvest_outcomes")
        op.drop_table("harvest_outcomes")
    if "scheme_records" in _table_names():
        op.drop_index("ix_scheme_records_farm_id", table_name="scheme_records")
        op.drop_index("ix_scheme_records_id", table_name="scheme_records")
        op.drop_table("scheme_records")
