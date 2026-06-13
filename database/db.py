"""
Database session management and initialization.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from config.logging_config import get_logger
from config.settings import settings
from database.models import Base

logger = get_logger(__name__)

# Build engine kwargs — check_same_thread is SQLite-specific
_connect_args: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=_connect_args,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully.")


def drop_db() -> None:
    """Drop all database tables (use with caution)."""
    Base.metadata.drop_all(bind=engine)
    logger.warning("Database tables dropped.")


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session() -> Session:
    """Get a raw database session (caller must manage lifecycle)."""
    return SessionLocal()
