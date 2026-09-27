from pathlib import Path
import os

from alembic import command
from alembic.config import Config

from app.database.connection import DATABASE_URL


def run_migrations() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    alembic_cfg = Config(str(backend_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_root / "alembic_migrations"))
    migration_url = (
        os.getenv("DATABASE_MIGRATION_URL")
        or os.getenv("DATABASE_URL_UNPOOLED")
        or DATABASE_URL
    ).strip().strip("\"'")
    if migration_url.startswith("postgresql+psycopg2://"):
        migration_url = migration_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    alembic_cfg.set_main_option("sqlalchemy.url", migration_url)
    command.upgrade(alembic_cfg, "head")
