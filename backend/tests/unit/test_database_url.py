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
