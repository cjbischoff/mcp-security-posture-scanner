# AI Tool Data Policy

What data is shared with external AI services during development and at runtime.

---

## Development Time

An AI coding assistant (Claude Code via omp) was used during the development of this project. The following data was visible to the AI assistant:

- **Code:** All source files, test files, and configuration files in the repository
- **Documentation:** All docs, planning artifacts (`mcp-scanner-project-brief.md`, `product-spec.md`, `openapi.yaml`, `.planning/`)
- **Git history:** Commit messages and diffs

**Not shared:** No secrets, API keys, credentials, tokens, or personal data were provided to the AI assistant. No employer-internal code, architecture, or threat models were shared (clean-room constraint per brief Section 2, item 4).

All AI-generated code was reviewed by the human operator before commit. See `security/pr-audit/review-log.md`.

---

## Runtime — Core Rule Engine

The core scanner rule engine (MCP-001 through MCP-010) is **fully deterministic**. It never sends any target-server data to an LLM or any external service. The engine runs:

- Regex patterns over tool descriptions (MCP-001, MCP-009)
- Schema shape analysis (MCP-002, MCP-006, MCP-008)
- Heuristic checks on annotations (MCP-003, MCP-004)
- Length/entropy analysis (MCP-007)
- In-memory set operations for drifts (MCP-010)

**Data that never leaves the host:** tool names, tool descriptions, input schemas, resource URIs, prompt descriptions, finding text, scan target URLs, scan commands. All processing is local.

This constraint is enforced by the custom Semgrep rule `no-llm-on-untrusted-mcp-data` at `security/semgrep/rules/no-llm-on-untrusted-mcp-data.yaml`.

---

## Runtime — Decision Model (Phase 5, Optional)

If configured, the Phase 5 decision model (`GET /api/scans/{id}/verdict`) sends only scanner-derived data to an external hosted model:

**Sent:**
- Count of findings per severity (integer: critical, high, medium, low)
- Set of triggered rule IDs (enum from fixed set: MCP-001..MCP-010)
- Transport type (enum: stdio/http)
- `allow_external` flag (boolean)

**Never sent:**
- Tool/resource/prompt names, descriptions, or schemas
- Finding title, description, or remediation text
- Target URL, command, or arguments
- Any free-text field from the scanned MCP server

The input model has typed fields only (integers, enums, booleans). No free-text field exists in the serialized request. This is enforced by:
1. Typed Pydantic request model with no string fields
2. Custom Semgrep rule covering the decision-model client
3. Unit test asserting no target-derived string in serialized request

The decision model is opt-in (`DECISION_MODEL_URL` and `DECISION_MODEL_API_KEY` env vars). If unset, only the deterministic policy runs and no data leaves the host.

---

## Runtime — Telemetry

Traces, metrics, and logs go to the local `lgtm` container (Grafana
`otel-lgtm`) over OTLP/HTTP. It runs on the same host; no telemetry goes to a
hosted service or an AI service. Telemetry carries only scan_id, transport,
status, counts, durations, and a fixed error category. Target command, args,
URL, target name, tool/resource/prompt metadata, and raw error text are kept
out, and `tests/unit/test_telemetry.py` checks this. See
`ops/observability.md`.

---

## Runtime — On-call Agent (optional LLM)

The on-call agent (`oncall/`) can use an LLM provider the operator chooses
(`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`; any OpenAI-compatible API). If
these are unset, nothing is sent and a deterministic runbook runs.

**Sent to the provider:**
- A fixed system prompt
- The alert, reduced to: alert name, status, severity, service label, start
  time, numeric alert values, and the alert summary (our own Grafana rule
  text, cut to 200 characters)
- Tool results: metric numbers (no labels), names of active fault flags,
  backend health status/version/HTTP code, and action results (HTTP codes)

**Never sent:**
- Tool/resource/prompt names, descriptions, or schemas of any scan target
- Scan target names, URLs, commands, or args
- Finding text, scan errors, or log lines (the agent does not read Loki)
- Grafana URLs, fingerprints, or labels other than the ones above
- Secrets (admin token, GitHub token, deploy hook)

The agent has no tool that reads scans, targets, or findings, and every tool
returns a small typed summary instead of a raw response. Enforced by
`oncall/tests/test_agent.py::test_llm_never_sees_target_data` and the Semgrep
rule `oncall-no-scanner-target-data-import` (no backend or MCP SDK imports in
`oncall/`). Details: `docs/oncall-agent.md`.

---

## Third-Party Services

| Service | Purpose | Data shared |
|---|---|---|
| GitHub Actions | CI/CD pipeline | Source code (during build/test) |
| PyPI / npm | Package installation | Package names and versions |
| Docker Hub | Base images (postgres, nginx, python, node, grafana/otel-lgtm) | None — pull only |

---

## Enforcement

The deterministic engine boundary is enforced at multiple layers:

1. **Design constraint** — brief Section 2, item 1 (permanent)
2. **Code-level** — `app/rules/` modules never import HTTP clients or LLM SDK
3. **Static analysis** — custom Semgrep rule flags any HTTP call with snapshot data in body
4. **Tests** — unit tests verify no target text in decision model request
5. **Documentation** — this policy document and `docs/permissions.md`

---

*Last updated: 2026-10-16*
