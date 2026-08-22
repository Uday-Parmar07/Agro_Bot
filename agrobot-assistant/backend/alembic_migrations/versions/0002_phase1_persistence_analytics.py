"""phase1 persistence analytics

Revision ID: 0002_phase1_persistence
Revises: 0001_baseline
Create Date: 2026-08-23 00:01:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_phase1_persistence"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _column_names(table_name: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table_name)}


def _has_index(table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in sa.inspect(op.get_bind()).get_indexes(table_name))


def _create_index_once(name: str, table_name: str, columns: list[str], unique: bool = False) -> None:
    if not _has_index(table_name, name):
        op.create_index(name, table_name, columns, unique=unique)


def upgrade() -> None:
    tables = _table_names()

    if "farms" not in tables:
        op.create_table(
            "farms",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False, server_default="Default Farm"),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("area_acres", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )
        op.create_index(op.f("ix_farms_id"), "farms", ["id"])
        op.create_index("ix_farms_user_id", "farms", ["user_id"])

    for table_name in ("questionnaire_responses", "recommendations"):
        columns = _column_names(table_name)
        if "farm_id" not in columns:
            op.add_column(table_name, sa.Column("farm_id", sa.Integer(), nullable=True))
            _create_index_once(f"ix_{table_name}_farm_id", table_name, ["farm_id"])

    if "disease_predictions" not in tables:
        op.create_table(
            "disease_predictions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("farm_id", sa.Integer(), nullable=False),
            sa.Column("image_path", sa.String(), nullable=True),
            sa.Column("predicted_class", sa.String(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("treatment_text", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=False, server_default="cnn"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["farm_id"], ["farms.id"]),
        )
        op.create_index(op.f("ix_disease_predictions_id"), "disease_predictions", ["id"])
        op.create_index("ix_disease_predictions_farm_id", "disease_predictions", ["farm_id"])

    if "weather_snapshots" not in tables:
        op.create_table(
            "weather_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("farm_id", sa.Integer(), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("temp", sa.Float(), nullable=True),
            sa.Column("humidity", sa.Float(), nullable=True),
            sa.Column("rainfall_mm", sa.Float(), nullable=True),
            sa.Column("raw_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["farm_id"], ["farms.id"]),
            sa.UniqueConstraint("farm_id", "date", name="uq_weather_snapshots_farm_date"),
        )
        op.create_index(op.f("ix_weather_snapshots_id"), "weather_snapshots", ["id"])
        op.create_index("ix_weather_snapshots_farm_id", "weather_snapshots", ["farm_id"])

    if "farm_crops" not in tables:
        op.create_table(
            "farm_crops",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("farm_id", sa.Integer(), nullable=False),
            sa.Column("crop_name", sa.String(), nullable=False),
            sa.Column("variety", sa.String(), nullable=True),
            sa.Column("area_acres", sa.Float(), nullable=True),
            sa.Column("planting_date", sa.Date(), nullable=True),
            sa.Column("expected_harvest_date", sa.Date(), nullable=True),
            sa.Column("added_by", sa.String(), nullable=False, server_default="user"),
            sa.Column("status", sa.String(), nullable=False, server_default="active"),
            sa.Column("added_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["farm_id"], ["farms.id"]),
        )
        op.create_index(op.f("ix_farm_crops_id"), "farm_crops", ["id"])
        op.create_index("ix_farm_crops_farm_id", "farm_crops", ["farm_id"])

    _backfill_default_farms()


def _backfill_default_farms() -> None:
    bind = op.get_bind()
    users = bind.execute(sa.text("SELECT id FROM users")).fetchall()

    for user_row in users:
        user_id = user_row[0]
        existing = bind.execute(
            sa.text("SELECT id FROM farms WHERE user_id = :user_id ORDER BY id LIMIT 1"),
            {"user_id": user_id},
        ).fetchone()
        if existing:
            farm_id = existing[0]
        else:
            env_response = bind.execute(
                sa.text(
                    "SELECT answers FROM questionnaire_responses "
                    "WHERE user_id = :user_id AND set_number = 4 "
                    "ORDER BY updated_at DESC LIMIT 1"
                ),
                {"user_id": user_id},
            ).fetchone()
            location = None
            area_acres = None
            if env_response and env_response[0]:
                try:
                    import json

                    answers = env_response[0]
                    if isinstance(answers, str):
                        answers = json.loads(answers)
                    district = answers.get("district")
                    state = answers.get("state")
                    location = ", ".join(part for part in [district, state] if part)
                    area = answers.get("total_area")
                    unit = answers.get("area_unit")
                    if area is not None:
                        area_acres = float(area)
                        if unit == "hectare":
                            area_acres *= 2.47105
                except Exception:
                    location = None
                    area_acres = None

            result = bind.execute(
                sa.text(
                    "INSERT INTO farms (user_id, name, location, area_acres, created_at, updated_at) "
                    "VALUES (:user_id, :name, :location, :area_acres, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {
                    "user_id": user_id,
                    "name": "Default Farm",
                    "location": location,
                    "area_acres": area_acres,
                },
            )
            farm_id = result.lastrowid

        bind.execute(
            sa.text(
                "UPDATE questionnaire_responses SET farm_id = :farm_id "
                "WHERE user_id = :user_id AND farm_id IS NULL"
            ),
            {"farm_id": farm_id, "user_id": user_id},
        )
        bind.execute(
            sa.text(
                "UPDATE recommendations SET farm_id = :farm_id "
                "WHERE user_id = :user_id AND farm_id IS NULL"
            ),
            {"farm_id": farm_id, "user_id": user_id},
        )


def downgrade() -> None:
    op.drop_index("ix_farm_crops_farm_id", table_name="farm_crops")
    op.drop_index(op.f("ix_farm_crops_id"), table_name="farm_crops")
    op.drop_table("farm_crops")

    op.drop_index("ix_weather_snapshots_farm_id", table_name="weather_snapshots")
    op.drop_index(op.f("ix_weather_snapshots_id"), table_name="weather_snapshots")
    op.drop_table("weather_snapshots")

    op.drop_index("ix_disease_predictions_farm_id", table_name="disease_predictions")
    op.drop_index(op.f("ix_disease_predictions_id"), table_name="disease_predictions")
    op.drop_table("disease_predictions")

    for table_name in ("recommendations", "questionnaire_responses"):
        columns = _column_names(table_name)
        if "farm_id" in columns:
            op.drop_index(f"ix_{table_name}_farm_id", table_name=table_name)
            op.drop_column(table_name, "farm_id")

    op.drop_index("ix_farms_user_id", table_name="farms")
    op.drop_index(op.f("ix_farms_id"), table_name="farms")
    op.drop_table("farms")
