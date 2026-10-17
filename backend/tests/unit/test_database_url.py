"""Tests for DATABASE_URL normalization (Neon/Heroku style URLs)."""
import pytest

from app.database import normalize_database_url


@pytest.mark.parametrize(
    "raw, expected",
    [
        (
            "postgresql://u:p@h.neon.tech/db?sslmode=require",
            "postgresql+psycopg2://u:p@h.neon.tech/db?sslmode=require",
        ),
        ("postgres://u:p@h/db", "postgresql+psycopg2://u:p@h/db"),
        ("postgresql+psycopg2://u:p@h/db", "postgresql+psycopg2://u:p@h/db"),
        ("sqlite:///./scanner.db", "sqlite:///./scanner.db"),
    ],
)
def test_normalize_database_url(raw, expected):
    assert normalize_database_url(raw) == expected


def test_engine_checks_connections_before_use(tmp_path):
    """Pooled connections are pinged before use.

    Neon closes idle connections after its compute suspends (about 5 min on
    the free tier). Without a pre-ping, the first request after that reused a
    dead connection and returned HTTP 500 (reproduced on prod 2026-10-17).
    """
    from app import database

    engine = database.configure(f"sqlite:///{tmp_path / 'p.db'}")
    assert engine.pool._pre_ping is True
