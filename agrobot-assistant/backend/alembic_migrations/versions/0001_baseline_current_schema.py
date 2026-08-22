"""baseline current schema

Revision ID: 0001_baseline
Revises: None
Create Date: 2026-08-23 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("hashed_password", sa.String(), nullable=False),
            sa.Column("full_name", sa.String(), nullable=False),
            sa.Column("phone_number", sa.String(), nullable=True),
            sa.Column("is_new_user", sa.Boolean(), nullable=True),
            sa.Column("onboarding_completed", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index(op.f("ix_users_id"), "users", ["id"])
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    if not _has_table("questionnaire_responses"):
        op.create_table(
            "questionnaire_responses",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("set_number", sa.Integer(), nullable=False),
            sa.Column("answers", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )
        op.create_index(
            op.f("ix_questionnaire_responses_id"),
            "questionnaire_responses",
            ["id"],
        )

    if not _has_table("recommendations"):
        op.create_table(
            "recommendations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("soil_health_score", sa.Float(), nullable=True),
            sa.Column("recommended_crops", sa.JSON(), nullable=True),
            sa.Column("farming_calendar", sa.JSON(), nullable=True),
            sa.Column("soil_improvement_tips", sa.JSON(), nullable=True),
            sa.Column("irrigation_recommendations", sa.JSON(), nullable=True),
            sa.Column("fertilizer_recommendations", sa.JSON(), nullable=True),
            sa.Column("pest_disease_prevention", sa.JSON(), nullable=True),
            sa.Column("generated_at", sa.DateTime(), nullable=True),
            sa.Column("next_review_date", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )
        op.create_index(op.f("ix_recommendations_id"), "recommendations", ["id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_recommendations_id"), table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_index(op.f("ix_questionnaire_responses_id"), table_name="questionnaire_responses")
    op.drop_table("questionnaire_responses")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
