"""
Tests for the consent validation service.
"""
import sys

import pytest
from app.services.consent import validate_target, resolve_stdio, ConsentError


class TestConsent:
    def test_localhost_allowed_without_flag(self):
        """localhost URL is allowed without allow_external flag."""
        # Should not raise
        validate_target("http", "http://localhost:8080", allow_external=False)

    def test_localhost_ip_allowed_without_flag(self):
        """127.0.0.1 URL is allowed without allow_external flag."""
        validate_target("http", "http://127.0.0.1:8080", allow_external=False)

    def test_external_rejected_without_flag(self):
        """External URL without allow_external raises."""
        with pytest.raises(ConsentError, match="external"):
            validate_target("http", "http://example.com:8080", allow_external=False)

    def test_external_allowed_with_flag(self):
        """External URL with allow_external=True is allowed."""
        validate_target("http", "http://example.com:8080", allow_external=True)

    def test_stdio_ignores_url_field(self):
        """stdio transport ignores the URL field."""
        validate_target("stdio", "http://evil.com", allow_external=False)


class TestResolveStdio:
    def test_fixture_name_resolves_without_flag(self, monkeypatch):
        """A bundled fixture name resolves to its server command in public mode."""
        monkeypatch.delenv("ALLOW_ARBITRARY_STDIO", raising=False)
        command, args = resolve_stdio("vulnerable-demo", [])
        assert command == sys.executable
        assert args[0].endswith("stub_mcp_server.py")

    def test_arbitrary_command_rejected_without_flag(self, monkeypatch):
        """Public mode rejects any command that is not a bundled fixture."""
        monkeypatch.delenv("ALLOW_ARBITRARY_STDIO", raising=False)
        with pytest.raises(ConsentError, match="fixture"):
            resolve_stdio("touch", ["/tmp/x"])

    def test_fixture_with_args_rejected_without_flag(self, monkeypatch):
        """Public mode rejects extra args, even with a fixture name."""
        monkeypatch.delenv("ALLOW_ARBITRARY_STDIO", raising=False)
        with pytest.raises(ConsentError):
            resolve_stdio("vulnerable-demo", ["--evil"])

    def test_arbitrary_command_allowed_with_flag(self, monkeypatch):
        """Local mode (ALLOW_ARBITRARY_STDIO=true) passes the command through."""
        monkeypatch.setenv("ALLOW_ARBITRARY_STDIO", "true")
        assert resolve_stdio("python", ["server.py"]) == ("python", ["server.py"])

    def test_missing_command_rejected(self, monkeypatch):
        """stdio without a command is rejected."""
        monkeypatch.setenv("ALLOW_ARBITRARY_STDIO", "true")
        with pytest.raises(ConsentError):
            resolve_stdio(None, [])
