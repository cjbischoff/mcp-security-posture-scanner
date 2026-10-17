"""Tests for the user-facing scan error text."""
from app.services.scan_service import user_error


def test_timeout_gets_a_readable_message():
    """str(TimeoutError()) is empty; the API must still say what happened."""
    assert user_error(TimeoutError()) == "TimeoutError: the target did not respond in time"


def test_other_errors_keep_their_message():
    """Errors with text are passed through unchanged."""
    assert user_error(ValueError("Command not found: npx")) == "Command not found: npx"
