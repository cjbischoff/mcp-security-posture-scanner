"""Unit tests for webhook parsing and the fixed tool allowlist."""

import json

import httpx
import pytest

from conftest import TARGET_MARKERS, grafana_payload
from oncall.tools import ToolError, Tools, parse_alert


def make_tools(config, client):
    return Tools(config, parse_alert(grafana_payload()), client)


def test_parse_alert_keeps_only_boundary_fields():
    alert = parse_alert(grafana_payload())
    assert alert == {
        "status": "firing",
        "alertname": "ScanFailureRateHigh",
        "service": "scanner-backend",
        "severity": "page",
        "starts_at": "2026-10-16T12:00:00Z",
        "values": {"A": 0.83, "C": 1.0},
        "summary": "Scan failure ratio above 50% for 1m",
    }


def test_parse_alert_resolved():
    assert parse_alert(grafana_payload(status="resolved"))["status"] == "resolved"


@pytest.mark.parametrize("bad", [{}, {"alerts": []}, {"alerts": "x"}, [], "x"])
def test_parse_alert_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_alert(bad)


@pytest.mark.parametrize("name,args", [
    ("delete_database", {}),
    ("query_metrics", {"name": "up{job=~'.*'}"}),
    ("query_metrics", {"query": "up"}),
    ("clear_fault", {"name": "../../users"}),
    ("check_health", {"url": "http://evil-target.example"}),
    ("clear_fault", {}),
])
def test_allowlist_rejects_unknown_tools_and_bad_args(config, client, world, name, args):
    with pytest.raises(ToolError):
        make_tools(config, client).call(name, args)
    assert not any(m == "DELETE" for m, _ in world.requests)


def test_open_issue_is_not_callable_by_name(config, client):
    # open_issue is run by the agent after verification, never by the model.
    with pytest.raises(ToolError):
        make_tools(config, client).call("open_issue", {"title": "x"})


def test_get_faults_returns_only_active_names(config, client, world):
    world.faults["other"] = False
    out = make_tools(config, client).call("get_faults", {})
    assert out == {"active": ["scan-failure"]}


def test_check_health_drops_extra_fields(config, client):
    out = make_tools(config, client).call("check_health", {})
    assert out == {"ok": True, "http_status": 200, "status": "ok", "version": "abc123"}


def test_query_metrics_returns_numbers_only(config, client):
    out = make_tools(config, client).call("query_metrics", {"name": "scan_failure_ratio"})
    assert out == {"name": "scan_failure_ratio", "values": [0.83]}
    assert not any(m in json.dumps(out) for m in TARGET_MARKERS)


def test_clear_fault_deletes_with_admin_token(config, client, world):
    out = make_tools(config, client).call("clear_fault", {"name": "scan-failure"})
    assert out == {"cleared": "scan-failure", "http_status": 204}
    assert world.faults["scan-failure"] is False


def test_optional_actions_skip_when_unconfigured(config, client, world):
    tools = make_tools(config, client)
    assert "skipped" in tools.call("redeploy", {})
    assert "skipped" in tools.call("rollback", {})
    assert "skipped" in tools.open_issue("t", "b")
    assert world.requests == []


def test_redeploy_and_rollback_and_issue_when_configured(config):
    seen = []

    def handler(request):
        seen.append((request.method, str(request.url), request.content))
        return httpx.Response(201, json={"html_url": "https://github.com/o/r/issues/1"})

    config.render_deploy_hook = "https://api.render.com/deploy/srv-x?key=y"
    config.github_token = "gh"
    config.github_repository = "o/r"
    config.rollback_tag = "abc1234"
    tools = Tools(config, parse_alert(grafana_payload()),
                  httpx.Client(transport=httpx.MockTransport(handler)))
    assert tools.call("redeploy", {})["http_status"] == 201
    assert tools.call("rollback", {})["tag"] == "abc1234"
    assert tools.open_issue("t", "b")["url"] == "https://github.com/o/r/issues/1"
    dispatch = json.loads(seen[1][2])
    assert seen[1][1].endswith("/repos/o/r/actions/workflows/deploy.yml/dispatches")
    assert dispatch == {"ref": "main", "inputs": {"environment": "prod", "tag": "abc1234"}}
    assert seen[2][1].endswith("/repos/o/r/issues")
