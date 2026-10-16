from app.config import Settings


class TestSettings:
    def test_default_database_url(self):
        """Defaults to SQLite when DATABASE_URL is not set."""
        s = Settings()
        assert s.database_url == "sqlite:///./scanner.db"

    def test_env_variable_override(self, monkeypatch):
        """Reads DATABASE_URL from environment."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h/db")
        s = Settings()
        assert s.database_url == "postgresql+psycopg://u:p@h/db"

    def test_debug_default(self):
        """debug defaults to False."""
        s = Settings()
        assert s.debug is False
