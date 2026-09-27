#!/usr/bin/env python3
"""Copy data from a SQLite dev database into PostgreSQL.

Usage:
  ./scripts/migrate_sqlite_to_postgres.py \
    --source sqlite:///./agrobot.db \
    --dest postgresql+psycopg://user:pass@host:5432/dbname?sslmode=require

This script preserves primary keys and foreign keys by copying rows in the
correct order. It creates missing tables in the destination database before
copying data.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database.schemas import (
    AdvisorFarmerLink,
    Base,
    CropMarketNews,
    DiseasePrediction,
    Farm,
    FarmCrop,
    Mandi,
    MandiPriceSnapshot,
    QuestionnaireResponse,
    Recommendation,
    SchemeRecord,
    User,
    WeatherSnapshot,
)


TABLES_IN_COPY_ORDER = (
    User,
    Farm,
    QuestionnaireResponse,
    Recommendation,
    DiseasePrediction,
    WeatherSnapshot,
    FarmCrop,
    AdvisorFarmerLink,
    SchemeRecord,
    Mandi,
    MandiPriceSnapshot,
    CropMarketNews,
)


def build_engine(url: str):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


def clone_row(row, model_cls):
    data = {}
    for column in model_cls.__table__.columns:
        if column.name == "id":
            data["id"] = row.id
            continue
        data[column.name] = getattr(row, column.name)
    return model_cls(**data)


def copy_table(source: Session, destination: Session, model_cls) -> int:
    rows = source.query(model_cls).order_by(model_cls.id).all()
    if not rows:
        return 0

    for row in rows:
        destination.merge(clone_row(row, model_cls))
    destination.commit()
    return len(rows)


def reset_postgres_sequences(engine, tables: Iterable[type]) -> None:
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as conn:
        for model_cls in tables:
            table_name = model_cls.__tablename__
            pk_name = "id"
            result = conn.execute(
                text(
                    """
                    SELECT pg_get_serial_sequence(:table_name, :pk_name)
                    """
                ),
                {"table_name": table_name, "pk_name": pk_name},
            ).scalar_one_or_none()
            if not result:
                continue

            max_id = conn.execute(
                text(f'SELECT COALESCE(MAX("{pk_name}"), 0) FROM "{table_name}"')
            ).scalar_one()
            if max_id:
                conn.execute(
                    text("SELECT setval(:sequence_name, :next_value, true)"),
                    {"sequence_name": result, "next_value": max_id},
                )
            else:
                conn.execute(
                    text("SELECT setval(:sequence_name, 1, false)"),
                    {"sequence_name": result},
                )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=str((BACKEND_ROOT / "agrobot.db").resolve().as_uri().replace("file://", "sqlite:///")),
        help="Source database URL. Defaults to a local SQLite file.",
    )
    parser.add_argument(
        "--dest",
        required=True,
        help="Destination PostgreSQL URL, for example postgresql+psycopg://user:pass@host:5432/dbname?sslmode=require",
    )
    parser.add_argument(
        "--reset-sequences-only",
        action="store_true",
        help="Only reset destination PostgreSQL sequences; do not copy data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    source_engine = build_engine(args.source)
    dest_engine = build_engine(args.dest)

    Base.metadata.create_all(bind=dest_engine)

    if args.reset_sequences_only:
        reset_postgres_sequences(dest_engine, TABLES_IN_COPY_ORDER)
        print("Reset destination sequences")
        return

    SourceSession = sessionmaker(bind=source_engine, autocommit=False, autoflush=False)
    DestSession = sessionmaker(bind=dest_engine, autocommit=False, autoflush=False)

    source_session = SourceSession()
    dest_session = DestSession()
    try:
        copied_counts = {}
        for model_cls in TABLES_IN_COPY_ORDER:
            copied_counts[model_cls.__tablename__] = copy_table(source_session, dest_session, model_cls)

        reset_postgres_sequences(dest_engine, TABLES_IN_COPY_ORDER)

        for table_name, count in copied_counts.items():
            print(f"Copied {count} rows into {table_name}")
    finally:
        source_session.close()
        dest_session.close()


if __name__ == "__main__":
    main()
