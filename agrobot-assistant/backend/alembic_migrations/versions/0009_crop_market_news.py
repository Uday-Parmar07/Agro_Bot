"""crop market news

Revision ID: 0009_crop_market_news
Revises: 0008_remove_legacy_modules
Create Date: 2026-08-23 16:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_crop_market_news"
down_revision: Union[str, None] = "0008_remove_legacy_modules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "crop_market_news" in _table_names():
        return

    op.create_table(
        "crop_market_news",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("crop", sa.String(), nullable=False),
        sa.Column("headline", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("published_or_found_at", sa.DateTime(), nullable=True),
        sa.Column("cached_for_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("crop", "cached_for_date", "headline", name="uq_crop_market_news_crop_date_headline"),
    )
    op.create_index("ix_crop_market_news_id", "crop_market_news", ["id"])
    op.create_index("ix_crop_market_news_crop", "crop_market_news", ["crop"])
    op.create_index("ix_crop_market_news_cached_for_date", "crop_market_news", ["cached_for_date"])


def downgrade() -> None:
    if "crop_market_news" in _table_names():
        op.drop_table("crop_market_news")
