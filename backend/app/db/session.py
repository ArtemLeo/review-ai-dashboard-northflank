"""Database engine, session factory, and FastAPI session dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# PostgreSQL connections benefit from connection pooling and pre-ping so
# that closed connections are transparently replaced.
_engine_kwargs: dict[str, object] = {
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 20,
    "pool_recycle": 1800,
    "pool_timeout": 30,
}

engine: Engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session per request and close it upon completion.

    Any exception raised while handling the request rolls the transaction back
    so the session is never returned to the pool in a dirty state.

    Yields:
        Active SQLAlchemy Session object.
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
