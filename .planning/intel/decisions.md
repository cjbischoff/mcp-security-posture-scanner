# Decisions

## ADR-001: Hosted Decision Model (LOCKED)

**Source:** `docs/decisions/2026-10-15-decision-model.md`
**Precedence:** ADR (highest)
**Status:** LOCKED — operator-requested, Phase 5

### Decision

Add a hosted "System 1" decision model that produces a per-scan verdict (`allow`/`review`/`block`), a score (0–100), and the rule IDs that caused the decision. The model receives only scanner-derived data — never target-server text.

### Input allowlist

- Count of findings per severity (integer fields)
- Set of triggered rule IDs (enum fields from the fixed v1 list: MCP-001..MCP-010)
- Transport type (`stdio`/`http`, enum)
- `allow_external` flag (boolean)

Never sent: tool/resource/prompt names, descriptions, schemas, finding `subject`/`description`/`title`, target URL, command, or args.

### Enforcement

1. Typed input model with enum + integer fields only, extra fields forbidden (no free-text field exists).
2. Custom Semgrep rule `no-llm-on-untrusted-mcp-data` covers the decision-model client.
3. Unit test asserts no target-derived string in serialized request from a fixture scan.

### Output safety

- Validate model response against `Verdict` schema. Invalid/timeout/unconfigured → fallback to deterministic policy.
- Policy floor: model can make a verdict stricter, never less strict. Any Critical finding → always `block`.
- Each verdict records its `source` (`model` or `policy`).

### Deterministic policy (fallback and floor)

- Score = 100 − (40 × Critical + 20 × High + 5 × Medium + 1 × Low), minimum 0.
- Any Critical → `block`. Score below 70 → `review`. Otherwise `allow`.

### Configuration

`DECISION_MODEL_URL` and `DECISION_MODEL_API_KEY`. If unset, only the policy runs.

### Rationale

Model never sees target text, so the Section 2 item 1 constraint (deterministic rule engine, no LLM on untrusted input) holds. The rule engine stays deterministic and unchanged. The typed input model makes it impossible to send target text. Policy floor means model error can only make verdict stricter.

### Trade-offs accepted

- Input has limited information (counts and rule IDs only). The model cannot find risks that the rules miss.
- Not traceable to a rubric line. Added as Phase 5 so it does not delay graded work (Phases 3–4).
- Adds an external network dependency. Scan metadata (counts, rule IDs) leaves the host — must be stated in `security/ai-tool-data-policy.md`.
- Open: endpoint, request/response format, auth, and data retention of the hosted model are not confirmed yet.

### Alternatives rejected

- Model classifies target descriptions (injection probability) — breaks Section 2 item 1.
- Model as offline evaluation tool only — does not give users a decision.
- Deterministic verdict only, no model — kept as fallback and floor (chosen approach includes both).

### Supersedes

None.

---

## Derived Decisions

### Phase ordering

**Source:** PRD (Section 5), AGENTS.md session log
**Precedence:** PRD

- Phase 0 (Setup): complete as of AGENTS.md session log (2026-07-23).
- Phase 1 (Core Application): not started. Must complete before Phases 2–5.
- Phase 2 (Agent Extension Pack): conditional on Module 3 completion (unconfirmed).
- Phase 3 (Security/Audit/DevOps Hardening): applies regardless of Module 3.
- Phase 4 (Deploy and Polish): after Phase 1 + optional/graded phases.
- Phase 5 (Decision Model): operator-requested, starts only after Phase 1, must not delay Phases 3–4.

### API endpoint paths

**Source:** PRD vs SPEC
**Precedence:** SPEC > PRD → SPEC wins

- SPEC: `/api/scans`, `/api/scans/{id}`, `/api/scans/{id}/report`, `/api/scans/{id}/diff/{other_id}`, `/api/scans/{id}/verdict`, `/api/health`
- PRD draft: `/scans` (no `/api` prefix)
- Resolution: Use `/api/scans` per SPEC. The PRD marks its endpoints as draft and defers to `openapi.yaml`.

### Spec-first approach

**Source:** PRD (Section 0), AGENTS.md, CLAUDE.md
**Precedence:** PRD

- `openapi.yaml` is written before backend code and used as the contract by both frontend and backend.
- Enforced across all phases.
