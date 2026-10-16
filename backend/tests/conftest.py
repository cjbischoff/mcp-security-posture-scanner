"""Shared test fixtures for all plans in Phase 1.

Provides an in-memory SQLite database session and model factories.
Uses create_all instead of Alembic for test isolation.
"""
import sys
from pathlib import Path

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.database import Base
from app.models.scan_target import ScanTarget
from app.models.scan import Scan
from app.models.finding import Finding  # noqa: F401 -- registers model


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory SQLite database per test."""
    engine = create_engine("sqlite://", echo=False)
    # Enable foreign key support for cascade to work
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))  # noqa
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, class_=Session)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def scan_target(db_session):
    """Create a ScanTarget fixture."""
    target = ScanTarget(name="test-target", transport="stdio")
    db_session.add(target)
    db_session.commit()
    return target


@pytest.fixture
def scan(db_session, scan_target):
    """Create a Scan fixture linked to scan_target."""
    s = Scan(target_id=scan_target.id)
    db_session.add(s)
    db_session.commit()
    return s
