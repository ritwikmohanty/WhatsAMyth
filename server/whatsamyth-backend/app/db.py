"""
Database configuration and session management.
Uses SQLAlchemy 2.0 with synchronous sessions for simplicity.
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Determine if we're using SQLite (for testing) or PostgreSQL
is_sqlite = settings.database_url.startswith("sqlite")

# Engine configuration
if is_sqlite:
    # SQLite specific settings for testing
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
else:
    # PostgreSQL settings for production
    engine = create_engine(
        settings.database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False
    )

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    Ensures proper cleanup after request completion.
    
    Usage in FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    Should be called on application startup.
    """
    from app.models import Base
    
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")


def drop_db() -> None:
    """
    Drop all database tables.
    Use with caution - mainly for testing.
    """
    from app.models import Base
    
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped.")


def check_db_connection() -> bool:
    """
    Check if database connection is working.
    Returns True if connection is successful, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


# Enable SQLite foreign key support if using SQLite
if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
