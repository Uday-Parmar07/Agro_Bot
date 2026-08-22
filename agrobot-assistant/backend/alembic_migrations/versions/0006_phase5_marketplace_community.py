"""phase5 marketplace community

Revision ID: 0006_phase5_marketplace
Revises: 0005_phase4_finance
Create Date: 2026-08-23 00:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_phase5_marketplace"
down_revision: Union[str, None] = "0005_phase4_finance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _table_names()
    if "marketplace_listings" not in tables:
        op.create_table(
            "marketplace_listings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("farmer_id", sa.Integer(), nullable=False),
            sa.Column("crop_name", sa.String(), nullable=False),
            sa.Column("quantity", sa.Float(), nullable=False),
            sa.Column("unit", sa.String(), nullable=False),
            sa.Column("price", sa.Float(), nullable=False),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("contact_pref", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="active"),
            sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["farmer_id"], ["users.id"]),
        )
        op.create_index("ix_marketplace_listings_id", "marketplace_listings", ["id"])
        op.create_index("ix_marketplace_listings_farmer_id", "marketplace_listings", ["farmer_id"])

    if "forum_posts" not in tables:
        op.create_table(
            "forum_posts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("region", sa.String(), nullable=False),
            sa.Column("crop_tag", sa.String(), nullable=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("body", sa.String(), nullable=False),
            sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )
        op.create_index("ix_forum_posts_id", "forum_posts", ["id"])
        op.create_index("ix_forum_posts_user_id", "forum_posts", ["user_id"])
        op.create_index("ix_forum_posts_region", "forum_posts", ["region"])

    if "forum_replies" not in tables:
        op.create_table(
            "forum_replies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("body", sa.String(), nullable=False),
            sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["post_id"], ["forum_posts.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )
        op.create_index("ix_forum_replies_id", "forum_replies", ["id"])
        op.create_index("ix_forum_replies_post_id", "forum_replies", ["post_id"])
        op.create_index("ix_forum_replies_user_id", "forum_replies", ["user_id"])

    if "reports" not in tables:
        op.create_table(
            "reports",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("target_type", sa.String(), nullable=False),
            sa.Column("target_id", sa.Integer(), nullable=False),
            sa.Column("reported_by", sa.Integer(), nullable=False),
            sa.Column("reason", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="open"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["reported_by"], ["users.id"]),
        )
        op.create_index("ix_reports_id", "reports", ["id"])
        op.create_index("ix_reports_reported_by", "reports", ["reported_by"])


def downgrade() -> None:
    for table_name in ("reports", "forum_replies", "forum_posts", "marketplace_listings"):
        if table_name in _table_names():
            op.drop_table(table_name)
