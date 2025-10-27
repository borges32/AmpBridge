"""Database base configuration and utilities."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.settings import settings

# Create SQLAlchemy engine
if settings.db_url.startswith("sqlite"):
    # SQLite specific configuration
    engine = create_engine(
        settings.db_url,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            # Enable WAL mode for better concurrency
            "timeout": 20,
        },
        echo=settings.debug,
    )
    # Enable WAL mode for SQLite
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA synchronous=NORMAL"))
        conn.execute(text("PRAGMA cache_size=1000"))
        conn.execute(text("PRAGMA temp_store=MEMORY"))
        conn.commit()
else:
    # PostgreSQL configuration
    engine = create_engine(
        settings.db_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=settings.debug,
    )

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all tables."""
    Base.metadata.drop_all(bind=engine)