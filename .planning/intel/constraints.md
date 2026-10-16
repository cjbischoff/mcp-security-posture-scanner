# Constraints

Hard boundaries extracted from all ingested documents, ordered by precedence (ADR > SPEC > PRD > DOC).

---

## ADR-Level Constraints

### C-ADR-001: Decision model input is typed and bounded
- Source: ADR (LOCKED), PRD Section 13
- The hosted model receives only: finding counts per severity, triggered rule IDs (enum), transport type (enum), `allow_external` flag (bool).
- No free-text fields. Names, descriptions, schemas, finding text, URLs, commands, and args are never sent.
- Enforcement via typed input model, custom Semgrep rule, and unit test.

### C-ADR-002: Policy floor — model can only make verdict stricter
- Source: ADR (LOCKED)
- Any Critical finding → always `block`.
- Model cannot downgrade a stricter policy verdict.

### C-ADR-003: Decision model is opt-in
- Source: ADR (LOCKED), PRD Section 13
- `DECISION_MODEL_URL` and `DECISION_MODEL_API_KEY` env vars.
- If unset → deterministic policy only.
- A fresh clone works with no model.

---

## SPEC-Level Constraints

### C-SPEC-001: API prefix
- Source: SPEC
- All scan/verdict/health endpoints use `/api` prefix (e.g., `/api/scans`, not `/scans`).

### C-SPEC-002: Data model entities
- Source: SPEC, PRD Section 6
- `ScanTarget`: name, transport (stdio/http), command+args or URL, `allow_external` flag.
- `Scan`: target ref, status (pending/running/completed/failed), timestamps, error, raw enumeration snapshot.
- `Finding`: scan ref, rule ID, severity, title, description, remediation, subject.
- `ScanDiff`: computed on demand — findings keyed by (rule_id, subject) → added/removed/unchanged sets.

---

## PRD-Level Constraints

### C-PRD-001: Deterministic rule engine (permanent)
- Source: PRD Section 2, item 1
- Core rule engine is deterministic — never feeds target data to an LLM for judgment.
- This is a permanent constraint, not a v1 limitation to lift later.

### C-PRD-002: Localhost/fixture default
- Source: PRD Section 2, item 2
- Default scan targets are localhost or self-hosted fixture servers only.
- External targets require explicit `allow_external` consent flag in API, UI, and README.

### C-PRD-003: Enumerate-only (permanent)
- Source: PRD Section 2, item 3
- Scanner calls `list_tools`, `list_resources`, `list_prompts` only.
- Never invokes a target server's tools (`call_tool`), reads resources, or executes prompts.

### C-PRD-004: Clean-room implementation
- Source: PRD Section 2, item 4
- Ruleset from public sources: OWASP MCP Top 10, published MCP security research, general appsec principles.
- No employer-internal architecture, logic, or threat models.

### C-PRD-005: Capped rule set
- Source: PRD Section 2, item 5
- v1 rule count capped at ~10–12. Exactly 10 defined (MCP-001 through MCP-010).
- Additional rules go to future-work list, not scope creep.

### C-PRD-006: Phase ordering dependency
- Source: PRD Section 5
- Phase 1 must be functionally complete and tested before Phase 2, 3, 4, or 5 work.
- Phase 5 (decision model) must not delay Phases 3–4 (graded).
- Phase 2 (Agent Extension Pack) is conditional on Module 3 completion (unconfirmed).

### C-PRD-007: Spec-first contract
- Source: PRD Sections 0, 5 (Phase 0)
- `openapi.yaml` written before backend implementation.
- Used as shared contract by frontend and backend.

### C-PRD-008: Repository structure
- Source: PRD Section 4
- Strict directory layout enforced: `backend/`, `frontend/`, `docs/`, `security/`, `ops/`, `.github/workflows/`.
- Phase 2 directories (`agent-capabilities/`, `agent-hooks/`, `mcp-server/`, `custom-agent/`) only if Module 3 confirmed.

### C-PRD-009: Decision model Phase 5 placement
- Source: PRD Section 13
- Decision model is operator-requested, Phase 5 only.
- Not traceable to a rubric line.
- Must record what is sent to the model in `security/ai-tool-data-policy.md`.

---

## DOC-Level Constraints (Informational)

### C-DOC-001: Safety boundary documentation
- Source: permissions.md
- `docs/permissions.md` must state the enumerate-only boundary in plain language.
- Agent Extension Pack (Phase 2) components inherit the same boundary.

### C-DOC-002: Target metadata is hostile input
- Source: architecture.md
- Target-server metadata treated as hostile: parsed by deterministic rules, rendered inertly in UI, never forwarded to LLM API.

### C-DOC-003: Repository scaffolding complete (Phase 0)
- Source: AGENTS.md session log
- Phase 0 complete as of 2026-07-23. Repo scaffolded per PRD Section 4.
- Phase 1 not started. Do not start Phase 1 work without human operator authorization.
