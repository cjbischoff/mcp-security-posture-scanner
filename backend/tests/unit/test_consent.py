"""
Tests for the consent validation service.
"""
import pytest
from app.services.consent import validate_target, ConsentError
from app.mcp_client.models import MCPTool, MCPSnapshot


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

    def test_stdio_always_allowed(self):
        """stdio transport is always allowed (no URL validation)."""
        validate_target("stdio", None, allow_external=False)

    def test_stdio_with_url_still_allowed(self):
        """stdio transport ignores URL field."""
        validate_target("stdio", "http://evil.com", allow_external=False)
