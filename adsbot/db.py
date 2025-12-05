"""Database helpers for Adsbot."""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import Config

Base = declarative_base()

# Import all models to register them with Base metadata
# (This must happen after Base is created but before create_all is called)
def _register_models():
    """Register all models with SQLAlchemy Base."""
    # Avoid circular imports by importing here
    from . import models  # noqa: F401
    return models

_models_registered = False


def create_session_factory(config: Config) -> sessionmaker:
    """Create a SQLAlchemy session factory."""
    global _models_registered
    
    # Register models if not already done
    if not _models_registered:
        _register_models()
        _models_registered = True

    engine = create_engine(config.database_url, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def get_session(session_factory: sessionmaker) -> Session:
    """Get a new database session."""
    return session_factory()


@contextmanager
def session_scope(session_factory: sessionmaker):
    """Provide a transactional scope around a series of operations."""

    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
