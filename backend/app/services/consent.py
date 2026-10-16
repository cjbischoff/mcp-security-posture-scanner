"""
Consent validation for external scan targets.
"""
from urllib.parse import urlparse

LOCALHOST_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


class ConsentError(ValueError):
    """Raised when an external target is submitted without consent."""


def validate_target(transport: str, url: str | None, allow_external: bool = False) -> None:
    """Validate that the target is allowed.

    For HTTP transport, non-localhost URLs require allow_external=True.
    For stdio transport, no URL validation is needed.
    """
    if transport != "http":
        return

    if not url:
        return

    parsed = urlparse(url)
    host = parsed.hostname or ""

    if host in LOCALHOST_HOSTS:
        return

    if not allow_external:
        raise ConsentError(
            f"External target '{url}' requires allow_external=true"
        )
