"""mandi prices

Revision ID: 0007_mandi_prices
Revises: 0006_phase5_marketplace
Create Date: 2026-08-23 00:06:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_mandi_prices"
down_revision: Union[str, None] = "0006_phase5_marketplace"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _column_names(table_name: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    farm_columns = _column_names("farms")
    if "latitude" not in farm_columns:
        op.add_column("farms", sa.Column("latitude", sa.Float(), nullable=True))
    if "longitude" not in farm_columns:
        op.add_column("farms", sa.Column("longitude", sa.Float(), nullable=True))

    tables = _table_names()
    if "mandis" not in tables:
        op.create_table(
            "mandis",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("market_name", sa.String(), nullable=False),
            sa.Column("state", sa.String(), nullable=False),
            sa.Column("district", sa.String(), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("market_name", "state", "district", name="uq_mandis_market_state_district"),
        )
        op.create_index("ix_mandis_id", "mandis", ["id"])
        op.create_index("ix_mandis_market_name", "mandis", ["market_name"])
        op.create_index("ix_mandis_state", "mandis", ["state"])

    if "mandi_price_snapshots" not in tables:
        op.create_table(
            "mandi_price_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("commodity", sa.String(), nullable=False),
            sa.Column("market_name", sa.String(), nullable=False),
            sa.Column("state", sa.String(), nullable=True),
            sa.Column("district", sa.String(), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("min_price", sa.Float(), nullable=True),
            sa.Column("max_price", sa.Float(), nullable=True),
            sa.Column("modal_price", sa.Float(), nullable=True),
            sa.Column("arrival_qty", sa.Float(), nullable=True),
            sa.Column("price_date", sa.Date(), nullable=False),
            sa.Column("fetched_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("commodity", "market_name", "price_date", name="uq_mandi_price_commodity_market_date"),
        )
        op.create_index("ix_mandi_price_snapshots_id", "mandi_price_snapshots", ["id"])
        op.create_index("ix_mandi_price_snapshots_commodity", "mandi_price_snapshots", ["commodity"])
        op.create_index("ix_mandi_price_snapshots_market_name", "mandi_price_snapshots", ["market_name"])
        op.create_index("ix_mandi_price_snapshots_price_date", "mandi_price_snapshots", ["price_date"])

    _seed_mandis()


def _seed_mandis() -> None:
    bind = op.get_bind()
    rows = [
        ("Pune", "Maharashtra", "Pune", 18.5204, 73.8567),
        ("Mumbai", "Maharashtra", "Mumbai", 19.0760, 72.8777),
        ("Nagpur", "Maharashtra", "Nagpur", 21.1458, 79.0882),
        ("Nashik", "Maharashtra", "Nashik", 19.9975, 73.7898),
        ("Bengaluru", "Karnataka", "Bengaluru Urban", 12.9716, 77.5946),
        ("Delhi", "NCT of Delhi", "Delhi", 28.6139, 77.2090),
        ("Indore", "Madhya Pradesh", "Indore", 22.7196, 75.8577),
        ("Jaipur", "Rajasthan", "Jaipur", 26.9124, 75.7873),
        ("Lucknow", "Uttar Pradesh", "Lucknow", 26.8467, 80.9462),
        ("Ahmedabad", "Gujarat", "Ahmedabad", 23.0225, 72.5714),
    ]
    for market_name, state, district, lat, lon in rows:
        existing = bind.execute(
            sa.text(
                "SELECT id FROM mandis WHERE lower(market_name)=lower(:market_name) "
                "AND lower(state)=lower(:state) AND lower(coalesce(district, ''))=lower(:district)"
            ),
            {"market_name": market_name, "state": state, "district": district or ""},
        ).fetchone()
        if not existing:
            bind.execute(
                sa.text(
                    "INSERT INTO mandis (market_name, state, district, latitude, longitude, created_at) "
                    "VALUES (:market_name, :state, :district, :latitude, :longitude, CURRENT_TIMESTAMP)"
                ),
                {
                    "market_name": market_name,
                    "state": state,
                    "district": district,
                    "latitude": lat,
                    "longitude": lon,
                },
            )


def downgrade() -> None:
    if "mandi_price_snapshots" in _table_names():
        op.drop_table("mandi_price_snapshots")
    if "mandis" in _table_names():
        op.drop_table("mandis")
    columns = _column_names("farms")
    if "longitude" in columns:
        op.drop_column("farms", "longitude")
    if "latitude" in columns:
        op.drop_column("farms", "latitude")
