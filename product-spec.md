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

## v1 rule set (capped)

| ID | Check | Default severity |
|---|---|---|
| MCP-001 | Injection patterns in tool descriptions (hidden unicode, "ignore previous instructions" strings) | Critical |
| MCP-002 | Unconstrained input schema on sensitive-looking parameters (shell/path/URL, no pattern/format/enum) | High |
| MCP-003 | Missing `readOnlyHint`/`destructiveHint` annotations | Medium |
| MCP-004 | Read capability + network/write capability pairing (confused-deputy signal) | High |
| MCP-005 | Unauthenticated HTTP transport | High |
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
- `GET /api/health` — liveness

## Tech stack

- Frontend: React + TypeScript (Vite), Vitest + React Testing Library
- Backend: FastAPI, SQLAlchemy + Alembic, official `mcp` Python SDK (client only)
- DB: SQLite (local) / Postgres (prod) via `DATABASE_URL`
- Docker Compose; GitHub Actions CI/CD; cloud deploy (Render/Fly.io/Railway)

## Non-goals

- Not a general-purpose vulnerability scanner — MCP posture only.
- Not a live internet-scanning tool — local/fixture targets by default.
- The rule engine is not, and will not become, an LLM-judgment system on
  untrusted input. Permanent constraint.

## Future work (explicitly out of v1 scope)

- Additional rules beyond the capped set (rug-pull hash pinning, OAuth scope
  analysis, sampling-request abuse detection)
- Scheduled re-scans and alerting
- SBOM-style export of a server's tool inventory
