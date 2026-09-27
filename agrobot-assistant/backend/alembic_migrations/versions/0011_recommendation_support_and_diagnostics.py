"""recommendation support categories and safe explanation diagnostics

Revision ID: 0011_rec_support
Revises: 0010_safe_crop_hybrid
Create Date: 2026-09-04 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_rec_support"
down_revision: Union[str, None] = "0010_safe_crop_hybrid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names() -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("recommendations")
    }


def upgrade() -> None:
    columns = _column_names()
    additions = {
        "explanation_status": sa.String(),
        "llm_failure_reasons": sa.JSON(),
        "preliminary_candidates": sa.JSON(),
        "global_warnings": sa.JSON(),
        "missing_inputs": sa.JSON(),
        "required_actions": sa.JSON(),
        "recommendation_message": sa.String(),
    }
    for name, type_ in additions.items():
        if name not in columns:
            op.add_column("recommendations", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    columns = _column_names()
    for name in (
        "recommendation_message",
        "required_actions",
        "missing_inputs",
        "global_warnings",
        "preliminary_candidates",
        "llm_failure_reasons",
        "explanation_status",
    ):
        if name in columns:
            op.drop_column("recommendations", name)
