"""
Consent validation for scan targets.

HTTP targets: non-localhost URLs need explicit consent.
stdio targets: public mode accepts only bundled fixture names, so the API
cannot run an arbitrary command. Local mode (ALLOW_ARBITRARY_STDIO=true)
passes any command through.
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

LOCALHOST_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures"

FIXTURES: dict[str, tuple[str, list[str]]] = {
    "vulnerable-demo": (sys.executable, [str(_FIXTURE_DIR / "stub_mcp_server.py")]),
}


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


def arbitrary_stdio_allowed() -> bool:
    """Return True when local mode allows any stdio command.

    Returns:
        True if the ALLOW_ARBITRARY_STDIO env var is "true", "1" or "yes".
    """
    return os.environ.get("ALLOW_ARBITRARY_STDIO", "").lower() in {"true", "1", "yes"}


def resolve_stdio(command: str | None, args: list[str] | None) -> tuple[str, list[str]]:
    """Resolve a stdio target to the command and args to execute.

    A bundled fixture name always resolves to its server. Any other command
    is accepted only in local mode.

    Args:
        command: Fixture name, or an executable in local mode.
        args: Extra arguments. Must be empty for fixture names in public mode.

    Returns:
        The (command, args) tuple to pass to the subprocess.

    Raises:
        ConsentError: If the command is missing, or is not allowed in public mode.

    Example:
        >>> resolve_stdio("vulnerable-demo", [])[1][0].endswith("stub_mcp_server.py")
        True
    """
    args = args or []
    if not command:
        raise ConsentError("stdio target requires a command")
    if command in FIXTURES and not args:
        return FIXTURES[command]
    if arbitrary_stdio_allowed():
        return command, args
    raise ConsentError(
        f"Public mode accepts only bundled fixture names: {sorted(FIXTURES)}"
    )
