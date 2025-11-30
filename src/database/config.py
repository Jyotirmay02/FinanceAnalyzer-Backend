"""
Database Configuration
Handles database connection, session management, and initialization
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pathlib import Path
import os

# Database file location - stored in user's Documents folder for persistence
DB_DIR = Path.home() / "Documents" / "FinanceAnalyzer"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "finance_data.db"

# Database URL
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Dependency function to get database session
    Usage in FastAPI: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables
    Call this on application startup
    """
    from .models import Base
    Base.metadata.create_all(bind=engine)
    print(f"✓ Database initialized at: {DB_PATH}")


def get_db_info():
    """Get database file information"""
    if DB_PATH.exists():
        size_mb = DB_PATH.stat().st_size / (1024 * 1024)
        return {
            "path": str(DB_PATH),
            "size_mb": round(size_mb, 2),
            "exists": True
        }
    return {
        "path": str(DB_PATH),
        "size_mb": 0,
        "exists": False
    }
