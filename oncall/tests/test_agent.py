"""Unit tests for the responder loop: runbook, LLM, fallback, verify, report."""

import json
from pathlib import Path

from conftest import TARGET_MARKERS, grafana_payload, tool_call
from oncall.agent import respond


def deletes(world):
    return [u for m, u in world.requests if m == "DELETE"]


def test_runbook_without_llm_clears_fault_and_writes_report(config, client, world):
    report = respond(grafana_payload(), config, client)
    assert report["mode"] == "runbook"
    assert report["outcome"] == "resolved"
    assert world.faults["scan-failure"] is False
    assert [s["tool"] for s in report["steps"]][-1] == "clear_fault"
    md = Path(config.incidents_dir) / f"{report['id']}.md"
    assert md.exists() and "ScanFailureRateHigh" in md.read_text()
    saved = json.loads((Path(config.incidents_dir) / f"{report['id']}.json").read_text())
    assert saved["outcome"] == "resolved"


def test_llm_path_uses_model_tool_calls(llm_config, client, world):
    world.llm_replies = [
        tool_call("get_faults", {}),
        tool_call("clear_fault", {"name": "scan-failure"}),
        {"role": "assistant", "content": "Cleared the scan-failure fault."},
    ]
    report = respond(grafana_payload(), llm_config, client)
    assert report["mode"] == "llm"
    assert report["outcome"] == "resolved"
    assert [s["tool"] for s in report["steps"]] == ["get_faults", "clear_fault"]
    assert report["summary"] == "Cleared the scan-failure fault."
    # The tool result was fed back with the matching tool_call_id.
    assert world.llm_bodies[1]["messages"][-1]["tool_call_id"] == "c1"


def test_unknown_tool_falls_back_to_runbook(llm_config, client, world):
    world.llm_replies = [tool_call("run_shell", {"cmd": "rm -rf /"})]
    report = respond(grafana_payload(), llm_config, client)
    assert report["mode"] == "runbook"
    assert "run_shell" in report["fallback_reason"]
    assert world.faults["scan-failure"] is False


def test_bad_args_fall_back_to_runbook(llm_config, client, world):
    world.llm_replies = [tool_call("query_metrics", {"name": "sum(up)"})]
    report = respond(grafana_payload(), llm_config, client)
    assert report["mode"] == "runbook"
    assert report["outcome"] == "resolved"


def test_llm_error_falls_back_to_runbook(llm_config, client, world):
    world.llm_status = 500
    report = respond(grafana_payload(), llm_config, client)
    assert report["mode"] == "runbook"
    assert report["outcome"] == "resolved"


def test_llm_that_never_acts_is_capped_then_falls_back(llm_config, client, world):
    world.llm_replies = [tool_call("check_health", {}, f"c{i}") for i in range(20)]
    report = respond(grafana_payload(), llm_config, client)
    assert len(world.llm_bodies) == llm_config.max_steps
    assert report["mode"] == "runbook"
    assert world.faults["scan-failure"] is False


def test_llm_never_sees_target_data(llm_config, client, world):
    world.llm_replies = [
        tool_call("get_alert", {}, "a"),
        tool_call("query_metrics", {"name": "scan_failure_ratio"}, "b"),
        tool_call("get_faults", {}, "c"),
        tool_call("check_health", {}, "d"),
        tool_call("clear_fault", {"name": "scan-failure"}, "e"),
    ]
    respond(grafana_payload(), llm_config, client)
    sent = json.dumps(world.llm_bodies)
    assert len(world.llm_bodies) == 6
    for marker in TARGET_MARKERS + ["generatorURL", "lgtm:3000", "fingerprint"]:
        assert marker not in sent


def test_verify_reports_unresolved_when_fault_stays(config, client, world):
    world.sticky_faults = True
    report = respond(grafana_payload(), config, client)
    assert report["outcome"] == "unresolved"
    assert report["verification"]["active_faults"] == ["scan-failure"]


def test_verify_reports_unresolved_when_unhealthy(config, client, world):
    world.healthy = False
    report = respond(grafana_payload(), config, client)
    assert report["outcome"] == "unresolved"
    # Unresolved after the runbook -> it tried the (unconfigured) redeploy.
    assert report["steps"][-1]["tool"] == "redeploy"


def test_resolved_alert_takes_no_action(config, client, world):
    report = respond(grafana_payload(status="resolved"), config, client)
    assert report["outcome"] == "alert_resolved"
    assert deletes(world) == []


def test_unknown_alert_runs_diagnostics_only(config, client, world):
    report = respond(grafana_payload(alertname="DiskFull"), config, client)
    assert report["outcome"] == "needs_human"
    assert deletes(world) == []
