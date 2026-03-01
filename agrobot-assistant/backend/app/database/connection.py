from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.schemas import Base
import os

# Database URL - defaults to SQLite for development
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./agrobot.db')

# Create engine
if 'sqlite' in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

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
