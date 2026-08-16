from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.schemas import Base
from dotenv import load_dotenv, dotenv_values
from pathlib import Path
import os

# Load env files before reading DATABASE_URL.
# Keep service keys from app/.env, but do not let that file force a remote
# database URL during local development.
current_file = Path(__file__).resolve()
backend_root = current_file.parents[2]  # .../backend
app_root = current_file.parents[1]      # .../backend/app

load_dotenv(backend_root / ".env")

app_env_path = app_root / ".env"
if app_env_path.exists():
    app_env = dotenv_values(app_env_path)
    for key, value in app_env.items():
        if key != "DATABASE_URL" and value is not None and os.getenv(key) is None:
            os.environ[key] = value

# Database URL - defaults to SQLite for development
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./agrobot.db')

# Prefer psycopg v3 driver over psycopg2 for better local compatibility
if DATABASE_URL.startswith("postgresql+psycopg2://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)

# Create engine
if 'sqlite' in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
