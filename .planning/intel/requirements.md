# Requirements

Extracted from all ingested documents, deduplicated, and ordered by precedence.

---

## Functional Requirements

### FR-1: Submit and run a scan
- Source: PRD (Section 6), SPEC
- User provides a scan target (stdio command or HTTP URL).
- POST /api/scans starts an async scan.
- API returns scan ID immediately; frontend polls status.

### FR-2: Enumerate MCP server metadata
- Source: PRD (Section 2, item 3), SPEC, permissions.md
- Connects as MCP client, calls `list_tools`, `list_resources`, `list_prompts`.
- Reads schemas/descriptions/annotations only.
- Never calls `call_tool`, `read_resource`, or executes prompts.
- Raw enumeration snapshot stored for diffing (PRD Section 6).

### FR-3: Run deterministic rule engine
- Source: PRD (Section 2, item 1; Section 6), SPEC
- 10 rules (MCP-001 through MCP-010), one module per rule.
- Rules are pattern/heuristic/schema-shape based — no LLM judgment on target data.
- Rule set capped at ~10–12; additional rules go to future-work list.

### FR-4: Produce scored findings report
- Source: PRD (Section 6), SPEC
- Each Finding has: scan reference, severity (Critical/High/Medium/Low), rule ID, description, remediation text, subject (tool/resource/prompt name).
- Report available via GET /api/scans/{id}/report.
- Findings grouped by severity in UI.

### FR-5: Diff two scans for drift detection
- Source: PRD (Section 6), SPEC
- GET /api/scans/{id}/diff/{other_id} compares two completed scans of same target.
- Findings keyed by (rule_id, subject) → added/removed/unchanged sets.
- Rule MCP-010 flags findings that changed severity or disappeared without description change.
- Diff computed on demand; not persisted.

### FR-6: Produce verdict (Phase 5)
- Source: ADR (LOCKED), PRD Section 13, SPEC
- GET /api/scans/{id}/verdict returns allow/review/block, score (0–100), reasons, source.
- Hosted decision model produces verdict from scanner-derived counts/rule IDs only.
- Deterministic policy is fallback if model unconfigured/unavailable.
- Any Critical finding → always block (policy floor).
- Not a rule — does not count against the 10-rule cap.

### FR-7: Target consent for external scans
- Source: PRD (Section 2, item 2), SPEC, permissions.md
- Non-localhost targets require explicit `allow_external` consent flag.
- Flag is logged in both API and UI.
- Default targets are localhost or self-hosted fixture servers only.

---

## Non-Functional Requirements

### NFR-1: Deterministic engine constraint
- Source: PRD (Section 2, item 1), SPEC, permissions.md, ADR
- Core rule engine never feeds target-server descriptions or schemas to an LLM.
- Permanent constraint — not a v1 limitation to be lifted later.
- Phase 5 decision model does not change this (receives only counts and rule IDs).

### NFR-2: Enumerate-only safety boundary
- Source: PRD (Section 2, item 3), docs/permissions.md
- Scanner never invokes a target server's tools.
- Must be stated explicitly in docs/permissions.md.

### NFR-3: Localhost/fixture default
- Source: PRD (Section 2, item 2)
- Default scan targets are localhost or self-hosted fixture servers only.
- External targets require explicit consent.

### NFR-4: Clean-room implementation
- Source: PRD (Section 2, item 4)
- Ruleset derived from public sources only (OWASP MCP Top 10, published research, appsec principles).
- No employer-internal architecture, logic, or threat models.

### NFR-5: Capped rule set
- Source: PRD (Section 2, item 5), SPEC
- v1 ships exactly 10 rules (MCP-001 through MCP-010).
- Additional rules go to future-work list, not scope creep.

### NFR-6: Spec-first development
- Source: PRD (Section 5, Phase 0), AGENTS.md, CLAUDE.md
- openapi.yaml written before backend code.
- Used as contract by both frontend and backend.

### NFR-7: Containerized deployment
- Source: PRD (Sections 5, 10), architecture.md
- Docker Compose: frontend, backend, Postgres.
- SQLite locally, Postgres in prod (via DATABASE_URL).
- docker compose up —build runs full stack with no manual steps.

### NFR-8: Phase ordering
- Source: PRD (Section 5)
- Phase 1 must be functionally complete before Phase 2 starts.
- Phase 5 must not delay Phases 3–4 (graded).

---

## v1 Rule Set (Requirements)

| ID | Check | Severity | FR |
|---|---|---|---|
| MCP-001 | Injection patterns in tool descriptions (hidden unicode, "ignore previous instructions") | Critical | FR-3 |
| MCP-002 | Unconstrained input schema on sensitive params (shell/path/URL, no pattern/format/enum) | High | FR-3 |
| MCP-003 | Missing `readOnlyHint`/`destructiveHint` annotations | Medium | FR-3 |
| MCP-004 | Read + network/write capability pairing (confused-deputy signal) | High | FR-3 |
| MCP-005 | Unauthenticated HTTP transport | High | FR-3 |
| MCP-006 | Overly broad resource URI patterns (wildcards, root paths) | Medium | FR-3 |
| MCP-007 | Tool description length/entropy anomaly (potential hidden payload) | Medium | FR-3 |
| MCP-008 | Missing or malformed schema on required parameters | Medium | FR-3 |
| MCP-009 | Prompt-injection patterns in resource/prompt content descriptions | Critical | FR-3 |
| MCP-010 | (Diff-only) finding changed severity or disappeared without description change — drift | High | FR-5 |

---

## Rubric Requirements (Grading Gate)

| Category | Max | Satisfaction Criteria | Source |
|---|---|---|---|
| Problem Description | 2 | Clear README with problem, functionality, expected behavior | PRD Section 9 |
| AI-Assisted Dev Workflow | 2 | Documents prompts/task delegation, context files, manual review, verification in AGENTS.md | PRD Section 9 |
| Tech & Architecture | 2 | Frontend, backend, DB, containerization, CI/CD roles explained in docs/architecture.md | PRD Section 9 |
| Frontend | 3 | Functional, centralized API client, tests with run instructions | PRD Section 9 |
| API Contract | 2 | OpenAPI spec written first, used as contract | PRD Section 9 |
| Backend | 3 | Well structured, follows spec, tests on core functionality | PRD Section 9 |
| Database | 2 | Properly integrated, multi-environment support, documented | PRD Section 9 |
| Containerization | 2 | Full system via Docker Compose, no manual steps | PRD Section 9 |
| Integration Testing | 2 | Clearly separated, covers key workflows, documented | PRD Section 9 |
| Deployment | 2 | Deployed to cloud, working URL | PRD Section 9 |
| CI/CD | 2 | Runs tests and deploys on pass | PRD Section 9 |
| Agent Extension Pack | 2 | Conditional on Module 3: instructions, workflow, subagent, MCP tools, hook, permissions | PRD Section 9 |
| Security/Audit/DevOps | 2 | All 5 artifact types present (PR audit, Semgrep, agent/extension notes, ops output, AI data policy) | PRD Sections 8, 9 |
| Reproducibility | 2 | Clear end-to-end setup/run/test/deploy instructions in README | PRD Section 9 |
| Peer Review | pass/fail+bonus | Minimum 3 peer evaluations completed (course platform) | PRD Section 3 |
