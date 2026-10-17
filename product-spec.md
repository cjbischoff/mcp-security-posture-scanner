# Product Spec: MCP Security Posture Scanner

## Problem

Teams wire third-party MCP (Model Context Protocol) servers into AI agents with
little to no security review. Known risk classes include prompt injection in
tool descriptions, overly broad input schemas, missing safety annotations,
confused-deputy capability pairings, unauthenticated transport, and
descriptions that change after a client has trusted them ("rug pull").

There is no lightweight, self-hostable tool that lets a developer point at an
MCP server and get a posture report before wiring it into an agent. This
project builds one.

## What it does

A security scanner that:

1. Connects to an MCP server as a client (stdio command or HTTP URL).
2. Enumerates its tools, resources, and prompts (`list_tools`,
   `list_resources`, `list_prompts`). **It never invokes a target's tools.**
3. Runs a deterministic, human-written rule set against the enumerated
   metadata.
4. Produces a scored findings report (Critical/High/Medium/Low).
5. Diffs two scans of the same target over time to catch description drift.
6. *(Phase 5, operator-requested)* Returns a verdict for each scan:
   `allow`/`review`/`block`, a 0-100 score, and the rule IDs that caused it.
   The operator's hosted decision model produces it from the scanner's own
   findings only. A deterministic policy is the fallback. See brief Section 13.

## Hard constraints

- **Deterministic rule engine.** Target-server descriptions and schemas are
  never fed to an LLM for judgment — that would reintroduce the exact
  prompt-injection risk the tool detects. Rules are pattern/heuristic/schema-shape
  based.
- **Localhost/fixture targets by default.** Non-localhost HTTP targets require
  an explicit `allow_external` consent flag, which is logged.
- **Enumerate only.** The scanner never calls a target server's tools.
- **Capped rule set.** v1 ships 10 checks. Additional rules go to a
  future-work list, not into scope creep.

## Users and flows

Developer evaluating an MCP server before adoption:

1. **Submit scan** — enter target (stdio command or URL) in the web UI, submit.
2. **Watch status** — scan runs asynchronously; UI polls status.
3. **Read report** — findings grouped by severity with rule ID, description,
   remediation.
4. **Diff scans** — pick two scans of the same target, see added/removed
   findings and drift signals.
5. **Get verdict** *(Phase 5)* — see allow/review/block, the score, and the
   reasons. A CI job or agent harness can call the same endpoint before it
   connects to a new MCP server.

## Decision model (Phase 5, operator-requested)

- **Input (allowlist):** finding count per severity, triggered rule IDs,
  transport type, `allow_external` flag. Enum and integer fields only.
- **Never sent:** names, descriptions, schemas, finding text, subject, URL,
  command, args. The model never sees target-server text, so the
  deterministic-engine constraint holds.
- **Output:** `decision`, `score`, `reasons`, `source` (`model` or `policy`).
- **Fallback and floor:** deterministic policy. Score = 100 − (40·Critical +
  20·High + 5·Medium + 1·Low), minimum 0. Any Critical → `block`. Score
  below 70 → `review`. The model can make a verdict stricter, never less
  strict.
- **Config:** `DECISION_MODEL_URL`, `DECISION_MODEL_API_KEY`. Unset → policy
  only.
- Not a rule. It does not count against the 10-rule cap.

## v1 rule set (capped)

| ID | Check | Default severity |
|---|---|---|
| MCP-001 | Injection patterns in tool descriptions (hidden unicode, "ignore previous instructions" strings) | Critical |
| MCP-002 | Unconstrained input schema on sensitive-looking parameters (shell/path/URL, no pattern/format/enum) | High |
| MCP-003 | Missing `readOnlyHint`/`destructiveHint` annotations | Medium |
| MCP-004 | Read capability + network/write capability pairing (confused-deputy signal) | High |
| MCP-005 | Unauthenticated HTTP transport (inactive: not registered until the HTTP transport exists, #21) | High |
| MCP-006 | Overly broad resource URI patterns (wildcards, root paths) | Medium |
| MCP-007 | Tool description length/entropy anomaly (potential hidden payload) | Medium |
| MCP-008 | Missing or malformed schema on required parameters | Medium |
| MCP-009 | Prompt-injection patterns in resource/prompt content descriptions | Critical |
| MCP-010 | (Diff-only) finding changed severity or disappeared without description change — drift | High |

## Data model

- `ScanTarget` — name, transport (stdio/http), command+args or url,
  `allow_external` consent flag.
- `Scan` — target ref, status (pending/running/completed/failed), timestamps,
  error, raw enumeration snapshot (for diffing).
- `Finding` — scan ref, rule ID, severity, title, description, remediation,
  subject (tool/resource/prompt name).
- Diff is computed on demand from two scans' findings + snapshots (rule
  MCP-010); not persisted.

## API

See `openapi.yaml` (contract-first). Summary:

- `POST /api/scans` — submit target, start scan
- `GET /api/scans` — list scans
- `GET /api/scans/{id}` — status
- `GET /api/scans/{id}/report` — findings report
- `GET /api/scans/{id}/diff/{other_id}` — diff/drift between two scans
- `GET /api/scans/{id}/verdict` — allow/review/block verdict *(Phase 5, in
  the contract only, not implemented; issue #12)*
- `GET /api/health` — liveness, build version (not traced; `trace_id` is null)
- `GET /api/metrics` — in-process JSON snapshot (scan, finding, and rule
  totals, request counts, scan durations)
- `GET /api/admin/faults`, `POST`/`DELETE /api/admin/faults/scan-failure` —
  fault injection to trigger the alert; needs `Authorization: Bearer
  $ADMIN_TOKEN`, returns 404 when `ADMIN_TOKEN` is unset

## Acceptance criteria

Added 2026-10-17, after the code was written. This spec and `openapi.yaml`
date from 2026-07-23 (commit `fe2731a`) and predate the code; the criteria
below were written later to make the core flows testable. Per-task criteria
and their status live in
[GitHub Issues](https://github.com/cjbischoff/mcp-security-posture-scanner/issues).
"Open" means a known gap, with the tracking issue.

| # | Flow | Criterion | Status (2026-10-17) |
|---|---|---|---|
| AC-1 | Submit scan | `POST /api/scans` with a valid target returns 201 with a scan `id` and status `pending`; the scan runs in the background and reaches `completed` or `failed` | Met |
| AC-2 | Submit scan | An invalid body (for example `transport: http` with no `url`, an empty or very long `name`, a NUL byte) returns 422, never 201 or 500 | Met (#23) |
| AC-3 | Enumerate only | The MCP client sends only `initialize`, `notifications/initialized`, `tools/list`, `resources/list`, `prompts/list`; no code path sends `tools/call` | Met |
| AC-4 | Rules | Each of the 9 active rules is one module with a unit test that fails if the rule stops firing on a known-bad input; MCP-005 is not registered until the HTTP transport exists | Met (#21) |
| AC-5 | Report | `GET /api/scans/{id}/report` for a completed scan of `vulnerable-demo` returns findings with rule ID, severity, title, description, remediation, and subject; 404 for an unknown scan | Met |
| AC-6 | Report | The report returns 409 only while a scan is `pending`/`running`; the UI shows a failed scan's error and polls until the scan finishes | Met (PR #27, #18) |
| AC-7 | Diff/drift | `GET /api/scans/{a}/diff/{b}` for two completed scans of the same target returns added, removed, and unchanged findings plus drift findings (MCP-010); scans of different targets return 409 | Met; UI "Compare with" links added in PR #27 |
| AC-8 | Consent | A non-localhost HTTP target without `allow_external: true` returns 422; with it, the flag is stored on the target record | Met |
| AC-9 | Public mode | Without `ALLOW_ARBITRARY_STDIO=true`, a stdio `command` other than a bundled fixture name (`vulnerable-demo`), or any `args`, returns 422 | Met |
| AC-10 | Persistence | Targets, scans, findings, and the enumeration snapshot survive a backend restart, a database restart, and `docker compose down`/`up` | Met |
| AC-11 | Persistence | The first request after the database drops idle connections returns 2xx | Fixed in PR #16; prod check open, #19 |
| AC-12 | Observability | One scan has one trace with `scan.execute`, `mcp.connect`, `mcp.enumerate`, `rules.run`; the same `trace_id` is in the JSON logs (Loki); scan metrics are in Prometheus; locally in the LGTM container, deployed in Grafana Cloud | Met |
| AC-13 | Observability | No target name, command, args, URL, tool text, or raw error text in logs, spans, or metrics (unit test) | Met (#22: span URLs drop the query string, health checks are not traced) |
| AC-14 | Alert | `ScanFailureRateHigh` fires when more than 50% of scans fail over 5 minutes (at least 3 scans) and posts to the on-call webhook; `scripts/trigger-alert.sh` fires it in about 2 minutes | Met |
| AC-15 | On-call | On the alert, the on-call agent diagnoses with its fixed tool allowlist, clears only an active known fault, verifies recovery, and writes an incident report; with no known fault it reports `needs_human`; it never receives scan target data | Met (#25: clears only an active fault, verifies with a fixture scan, `needs_human` otherwise) |
| AC-16 | On-call | `/alert` rejects requests without a shared secret | Met (#25: Bearer `ONCALL_WEBHOOK_TOKEN`, 401 otherwise) |

## Tech stack

- Frontend: React + TypeScript (Vite), Vitest + React Testing Library
- Backend: FastAPI, SQLAlchemy + Alembic, official `mcp` Python SDK (client only)
- DB: SQLite (local) / Postgres (prod) via `DATABASE_URL`
- Docker Compose; GitHub Actions CI/CD; cloud deploy (Render/Fly.io/Railway)

## Non-goals

- Not a general-purpose vulnerability scanner — MCP posture only.
- Not a live internet-scanning tool — local/fixture targets by default.
- The rule engine is not, and will not become, an LLM-judgment system on
  untrusted input. Permanent constraint. The Phase 5 decision model does not
  change this: it receives scanner-derived counts and rule IDs only.

## Future work (explicitly out of v1 scope)

- Additional rules beyond the capped set (rug-pull hash pinning, OAuth scope
  analysis, sampling-request abuse detection)
- Scheduled re-scans and alerting
- SBOM-style export of a server's tool inventory
