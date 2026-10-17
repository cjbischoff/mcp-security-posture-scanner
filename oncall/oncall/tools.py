"""Configuration, webhook parsing, and the fixed tool allowlist.

Data boundary (brief Section 2, item 1): every tool here returns a small,
typed summary built from the scanner's own operational data: alert labels and
values, metric numbers, fault flag names, and health status. Raw responses are
never passed through, so scan target data (tool descriptions, commands, URLs,
finding text) cannot reach the LLM even if a backend response contained it.
"""

import math
import os
import re
import time
from dataclasses import dataclass, fields

import httpx

# Fixed PromQL. The model picks a name; it can never send its own query.
NAMED_QUERIES = {
    "scan_failure_ratio": (
        'sum(rate(scanner_scans_total{status="failed"}[5m]))'
        " / sum(rate(scanner_scans_total[5m]))"
    ),
    "scan_rate": "sum(rate(scanner_scans_total[5m]))",
    "scan_duration_p95": (
        "histogram_quantile(0.95,"
        " sum(rate(scanner_scan_duration_seconds_bucket[5m])) by (le))"
    ),
}

# Fault flags the agent may clear.
CLEARABLE_FAULTS = {"scan-failure"}

# The scan the agent runs to prove recovery: the bundled stdio fixture.
VERIFY_SCAN = {"target": {"name": "oncall-verify", "transport": "stdio",
                          "command": "vulnerable-demo"}}


class ToolError(Exception):
    """Raised when a tool call is not on the allowlist or has bad arguments."""


@dataclass
class Config:
    """Runtime settings, read from the environment by :meth:`from_env`.

    Attributes:
        scanner_url: Backend base URL (``SCANNER_URL``).
        prometheus_url: Prometheus base URL (``PROMETHEUS_URL``).
        admin_token: Bearer token for the backend admin API (``ADMIN_TOKEN``).
        incidents_dir: Where incident reports go (``INCIDENTS_DIR``).
        verify_wait_seconds: Wait before re-checking after a fix.
        max_steps: Cap on LLM round trips per incident.
        llm_base_url: OpenAI-compatible API base, e.g. ``https://api.openai.com/v1``.
        llm_api_key: API key for the LLM provider.
        llm_model: Model name passed to the provider.
        render_deploy_hook: Render deploy hook URL; enables ``redeploy``.
        github_token: GitHub token; enables ``rollback`` and ``open_issue``.
        github_repository: ``owner/repo`` for GitHub calls.
        rollback_tag: Known-good image tag (commit SHA) for ``rollback``.
        rollback_environment: ``deploy.yml`` environment input.
        oncall_webhook_token: Shared secret Grafana sends as
            ``Authorization: Bearer <token>`` (``ONCALL_WEBHOOK_TOKEN``).
            Empty means every ``/alert`` request is rejected.
        verify_scan_timeout: Seconds to wait for the verification scan.
    """

    scanner_url: str = "http://backend:8000"
    prometheus_url: str = "http://lgtm:9090"
    admin_token: str = ""
    incidents_dir: str = "ops/incidents"
    verify_wait_seconds: float = 15
    max_steps: int = 6
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    render_deploy_hook: str = ""
    github_token: str = ""
    github_repository: str = ""
    rollback_tag: str = ""
    rollback_environment: str = "prod"
    oncall_webhook_token: str = ""
    verify_scan_timeout: float = 60.0

    @classmethod
    def from_env(cls) -> "Config":
        """Build a Config from upper-case environment variables.

        Returns:
            Config with every field overridable by its upper-case env name,
            e.g. ``SCANNER_URL`` or ``VERIFY_WAIT_SECONDS``.

        Example:
            >>> os.environ["MAX_STEPS"] = "4"
            >>> Config.from_env().max_steps
            4
        """
        values = {}
        for f in fields(cls):
            raw = os.environ.get(f.name.upper())
            if raw is not None:
                values[f.name] = type(f.default)(raw)
        return cls(**values)

    @property
    def llm_enabled(self) -> bool:
        """True when base URL, key, and model are all set."""
        return bool(self.llm_base_url and self.llm_api_key and self.llm_model)


def parse_alert(payload) -> dict:
    """Reduce a Grafana webhook body to the fields the agent may see.

    Args:
        payload: Decoded Grafana unified-alerting webhook JSON.

    Returns:
        Dict with status, alertname, service, severity, starts_at, numeric
        values, and a summary truncated to 200 characters. URLs,
        fingerprints, and other labels are dropped.

    Raises:
        ValueError: If the payload has no alerts list.

    Example:
        >>> parse_alert({"status": "firing", "alerts": [{"labels": {}}]})["status"]
        'firing'
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("alerts"), list):
        raise ValueError("not a Grafana webhook payload")
    alerts = [a for a in payload["alerts"] if isinstance(a, dict)]
    if not alerts:
        raise ValueError("webhook has no alerts")
    # ponytail: handles the first firing alert; Grafana groups by alertname,
    # loop over alerts if one webhook ever carries several rules.
    alert = next((a for a in alerts if a.get("status") == "firing"), alerts[0])
    labels = alert.get("labels") or {}
    values = alert.get("values") or {}
    return {
        "status": str(alert.get("status") or payload.get("status", "")),
        "alertname": str(labels.get("alertname", "")),
        "service": str(labels.get("service", "")),
        "severity": str(labels.get("severity", "")),
        "starts_at": str(alert.get("startsAt", "")),
        "values": {str(k): float(v) for k, v in values.items()
                   if isinstance(v, (int, float))},
        "summary": str((alert.get("annotations") or {}).get("summary", ""))[:200],
    }


def _active_faults(data) -> list[str]:
    """Return active fault names from ``GET /api/admin/faults``.

    The backend returns ``{"scan_failure": bool}``. Only keys whose value is
    exactly ``True`` count; names are normalized to the URL form
    (``scan-failure``). Any other content is dropped.
    """
    if not isinstance(data, dict):
        return []
    names = (str(k).replace("_", "-") for k, v in data.items() if v is True)
    return sorted(n for n in names if re.fullmatch(r"[a-z0-9-]{1,40}", n))


class Tools:
    """The agent's only way to touch the world: a fixed allowlist.

    Args:
        config: Runtime settings.
        alert: Output of :func:`parse_alert` for the current incident.
        client: httpx client used for every outbound call.
    """

    # name -> {arg: allowed values}. Exact keys required; nothing else passes.
    ALLOWLIST = {
        "get_alert": {},
        "query_metrics": {"name": set(NAMED_QUERIES)},
        "get_faults": {},
        "check_health": {},
        "clear_fault": {"name": CLEARABLE_FAULTS},
        "redeploy": {},
        "rollback": {},
    }

    def __init__(self, config: Config, alert: dict, client: httpx.Client):
        self.config = config
        self.alert = alert
        self.client = client

    def call(self, name: str, args) -> dict:
        """Validate a tool call against the allowlist, then run it.

        Args:
            name: Tool name.
            args: Argument dict.

        Returns:
            The tool's result dict.

        Raises:
            ToolError: Unknown tool, wrong argument names, or a value outside
                the allowed set.
        """
        spec = self.ALLOWLIST.get(name)
        if spec is None:
            raise ToolError(f"tool not allowed: {name!r}")
        if not isinstance(args, dict) or set(args) != set(spec):
            raise ToolError(f"bad arguments for {name}: {args!r}")
        for key, allowed in spec.items():
            if not isinstance(args[key], str) or args[key] not in allowed:
                raise ToolError(f"{name}.{key} must be one of {sorted(allowed)}")
        return getattr(self, name)(**args)

    def _admin_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.config.admin_token}"}

    def get_alert(self) -> dict:
        """Return the parsed alert (boundary fields only)."""
        return self.alert

    def query_metrics(self, name: str) -> dict:
        """Run one named PromQL query and return its sample values.

        Args:
            name: Key of :data:`NAMED_QUERIES`.

        Returns:
            ``{"name", "values"}`` with floats (``None`` for NaN/Inf), or
            ``{"name", "error"}`` if Prometheus is unreachable.
        """
        try:
            r = self.client.get(f"{self.config.prometheus_url}/api/v1/query",
                                params={"query": NAMED_QUERIES[name]}, timeout=10)
            result = r.json()["data"]["result"]
            values = []
            for sample in result:
                v = float(sample["value"][1])
                values.append(v if math.isfinite(v) else None)
        except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError) as e:
            return {"name": name, "error": type(e).__name__}
        return {"name": name, "values": values}

    def get_faults(self) -> dict:
        """Return the names of active injected faults."""
        try:
            r = self.client.get(f"{self.config.scanner_url}/api/admin/faults",
                                headers=self._admin_headers(), timeout=10)
            r.raise_for_status()
            return {"active": _active_faults(r.json())}
        except (httpx.HTTPError, ValueError) as e:
            return {"error": type(e).__name__}

    def check_health(self) -> dict:
        """Return backend health: ok flag, HTTP status, status, version."""
        try:
            r = self.client.get(f"{self.config.scanner_url}/api/health", timeout=10)
            body = r.json() if r.content else {}
        except (httpx.HTTPError, ValueError) as e:
            return {"ok": False, "error": type(e).__name__}
        status = str(body.get("status", ""))[:20]
        return {"ok": r.status_code == 200 and status == "ok",
                "http_status": r.status_code, "status": status,
                "version": str(body.get("version", ""))[:64]}

    def clear_fault(self, name: str) -> dict:
        """Disable an injected fault via ``DELETE /api/admin/faults/{name}``.

        Refuses unless ``get_faults`` lists the fault as active right now, so
        neither the model nor the runbook can claim a fix for a fault that
        was never on.

        Args:
            name: Fault name from :data:`CLEARABLE_FAULTS`.

        Returns:
            ``{"cleared": name, "http_status"}`` on success, or
            ``{"cleared": None, ...}`` with ``rejected`` or ``error``.
        """
        if name not in (self.get_faults().get("active") or []):
            return {"cleared": None, "rejected": f"fault {name} is not active"}
        try:
            r = self.client.delete(f"{self.config.scanner_url}/api/admin/faults/{name}",
                                   headers=self._admin_headers(), timeout=10)
        except httpx.HTTPError as e:
            return {"cleared": None, "error": type(e).__name__}
        return {"cleared": name if r.is_success else None, "http_status": r.status_code}

    def verify_scan(self, sleep=time.sleep, interval: float = 2) -> dict:
        """Run one fixture scan through the public API and wait for it.

        Not on the model allowlist: the agent calls it during verification.
        Only the scan id and status are kept (never ``error`` text).

        Args:
            sleep: Sleep function (injected in tests).
            interval: Seconds between status polls.

        Returns:
            ``{"id", "status"}`` where status is ``completed``, ``failed``,
            ``timeout``, or ``error`` (transport or HTTP failure).
        """
        base = f"{self.config.scanner_url}/api/scans"
        sid = None
        try:
            r = self.client.post(base, json=VERIFY_SCAN, timeout=10)
            r.raise_for_status()
            sid = int(r.json()["id"])
            for _ in range(max(1, int(self.config.verify_scan_timeout / interval))):
                r = self.client.get(f"{base}/{sid}", timeout=10)
                r.raise_for_status()
                status = r.json().get("status")
                if status in ("completed", "failed"):
                    return {"id": sid, "status": status}
                sleep(interval)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:
            return {"id": sid, "status": "error", "error": type(e).__name__}
        return {"id": sid, "status": "timeout"}

    def redeploy(self) -> dict:
        """Restart the service via the Render deploy hook (same image)."""
        if not self.config.render_deploy_hook:
            return {"skipped": "RENDER_DEPLOY_HOOK not set"}
        try:
            r = self.client.post(self.config.render_deploy_hook, timeout=15)
        except httpx.HTTPError as e:
            return {"error": type(e).__name__}
        return {"http_status": r.status_code}

    def _github(self, path: str, body: dict) -> httpx.Response:
        return self.client.post(
            f"https://api.github.com/repos/{self.config.github_repository}{path}",
            json=body, timeout=15, headers={
                "Authorization": f"Bearer {self.config.github_token}",
                "Accept": "application/vnd.github+json"})

    def rollback(self) -> dict:
        """Dispatch ``deploy.yml`` with the known-good ``ROLLBACK_TAG``."""
        c = self.config
        if not (c.github_token and c.github_repository and c.rollback_tag):
            return {"skipped": "GITHUB_TOKEN, GITHUB_REPOSITORY or ROLLBACK_TAG not set"}
        try:
            r = self._github("/actions/workflows/deploy.yml/dispatches", {
                "ref": "main",
                "inputs": {"environment": c.rollback_environment, "tag": c.rollback_tag}})
        except httpx.HTTPError as e:
            return {"error": type(e).__name__}
        return {"http_status": r.status_code, "tag": c.rollback_tag}

    def open_issue(self, title: str, body: str) -> dict:
        """Open a GitHub issue with the incident report.

        Not on the model allowlist: the agent calls it after verification.

        Args:
            title: Issue title.
            body: Markdown incident report.

        Returns:
            ``{"url"}`` on success, ``{"skipped"}`` if unconfigured, or
            ``{"error"}``.
        """
        c = self.config
        if not (c.github_token and c.github_repository):
            return {"skipped": "GITHUB_TOKEN or GITHUB_REPOSITORY not set"}
        try:
            r = self._github("/issues", {"title": title, "body": body})
            r.raise_for_status()
            return {"url": r.json().get("html_url", "")}
        except (httpx.HTTPError, ValueError) as e:
            return {"error": type(e).__name__}
