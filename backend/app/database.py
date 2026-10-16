"""Database engine, session factory, and declarative base.

The engine is built from ``DATABASE_URL`` at import time (connections are
lazy). Tests and restarts can rebind it with :func:`configure`.
"""
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import Settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def normalize_database_url(url: str) -> str:
    """Map bare Postgres URLs to the psycopg2 driver, keeping query params.

    Neon and Heroku hand out ``postgresql://`` or ``postgres://`` URLs;
    the app ships psycopg2, so the driver is made explicit.

    Args:
        url: Raw database URL, e.g. ``postgresql://u:p@h/db?sslmode=require``.

    Returns:
        The URL with a ``postgresql+psycopg2://`` scheme, or ``url`` unchanged
        for any other scheme.

    Example:
        >>> normalize_database_url("postgres://u:p@h/db?sslmode=require")
        'postgresql+psycopg2://u:p@h/db?sslmode=require'
    """
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


SessionLocal = sessionmaker(expire_on_commit=False)
engine: Engine


def configure(url: str) -> Engine:
    """Create a new engine for ``url`` and bind ``SessionLocal`` to it.

    Args:
        url: Database URL; bare Postgres schemes are normalized.

    Returns:
        The new engine.
    """
    global engine
    engine = create_engine(normalize_database_url(url))
    SessionLocal.configure(bind=engine)
    return engine


configure(Settings().database_url)
