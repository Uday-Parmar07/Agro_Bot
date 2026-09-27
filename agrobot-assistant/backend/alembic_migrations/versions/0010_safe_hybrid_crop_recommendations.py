"""safe hybrid crop recommendation history

Revision ID: 0010_safe_crop_hybrid
Revises: 0009_crop_market_news
Create Date: 2026-09-04 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_safe_crop_hybrid"
down_revision: Union[str, None] = "0009_crop_market_news"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _foreign_key_columns(table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(constraint.get("constrained_columns") or [])
        for constraint in sa.inspect(op.get_bind()).get_foreign_keys(table_name)
    }


def upgrade() -> None:
    columns = _column_names("recommendations")
    additions = {
        "status": sa.String(),
        "input_snapshot": sa.JSON(),
        "data_quality": sa.JSON(),
        "model_version": sa.String(),
        "model_supported_crop_count": sa.Integer(),
        "crop_catalog_version": sa.String(),
        "prompt_version": sa.String(),
        "ranking_rule_version": sa.String(),
        "weather_source": sa.String(),
        "generation_mode": sa.String(),
        "model_status": sa.String(),
        "final_candidates": sa.JSON(),
        "coverage": sa.JSON(),
        "general_advice": sa.JSON(),
        "disclaimer": sa.String(),
    }
    for name, type_ in additions.items():
        if name not in columns:
            op.add_column("recommendations", sa.Column(name, type_, nullable=True))

    # Phase 1 added these columns before their ORM foreign keys existed. Repair
    # the farm boundary here so database constraints match authenticated routing.
    for table_name in ("questionnaire_responses", "recommendations"):
        if ("farm_id",) not in _foreign_key_columns(table_name):
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.create_foreign_key(
                    f"fk_{table_name}_farm_id_farms",
                    "farms",
                    ["farm_id"],
                    ["id"],
                )


def downgrade() -> None:
    for table_name in ("recommendations", "questionnaire_responses"):
        names = {
            constraint.get("name")
            for constraint in sa.inspect(op.get_bind()).get_foreign_keys(table_name)
        }
        constraint_name = f"fk_{table_name}_farm_id_farms"
        if constraint_name in names:
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.drop_constraint(constraint_name, type_="foreignkey")
    columns = _column_names("recommendations")
    for name in (
        "disclaimer",
        "general_advice",
        "coverage",
        "final_candidates",
        "model_status",
        "generation_mode",
        "weather_source",
        "ranking_rule_version",
        "prompt_version",
        "crop_catalog_version",
        "model_supported_crop_count",
        "model_version",
        "data_quality",
        "input_snapshot",
        "status",
    ):
        if name in columns:
            op.drop_column("recommendations", name)
