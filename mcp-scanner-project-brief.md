# MCP Security Posture Scanner: Project Brief and Build Instructions

Course: AI Dev Tools Zoomcamp (DataTalksClub), 2026 cohort, Final Project (draft requirements as of this writing).

---

## 0. How to use this document (read this first)

This file is the single source of truth for the project. If you are an LLM or coding agent being handed this document:

- Treat every constraint in Section 2 as non-negotiable. Do not propose work-arounds for them.
- Use Section 4 as the target repository structure. If the current repo state diverges from it, report the diff before making changes, do not silently restructure.
- Use Section 9 (rubric mapping table) as the definition of "done" for each area. A feature that isn't traceable to a rubric line in that table is out of scope unless the human operator explicitly asks for it.
- Section 5 gives the build order. Do not start Phase 2 or 3 work before Phase 1 is functionally complete and passing its own tests. Flag it if asked to jump ahead.
- Section 11 lists unresolved unknowns. Do not assume answers to these, ask the human operator.
- If any instruction here conflicts with something the human operator says in a live session, the live instruction wins, but flag the conflict rather than silently overriding this document.

---

## 1. Purpose and Problem Statement

Teams increasingly wire third-party MCP (Model Context Protocol) servers into AI agents with little to no security review. Known risk classes include:

- Prompt injection embedded in tool descriptions or schemas (the agent reads the description, not just the human)
- Overly broad input schemas (unconstrained shell/path/URL parameters)
- Missing or absent `readOnly`/`destructive` annotations on tools
- Tools that pair a broad read capability with a broad network/write capability (confused-deputy / exfiltration risk)
- Unauthenticated or weakly authenticated transport
- Tool descriptions that change after a client has already connected and trusted them ("rug pull")

There is no lightweight, self-hostable tool that lets a developer point at an MCP server and get a posture report before wiring it into an agent. This project builds one.

**One-line description:** a security scanner that connects to an MCP server as a client, enumerates its tools/resources/prompts, runs a deterministic rule set against them, and produces a scored findings report, with support for diffing two scans of the same server over time to catch description drift.

---

## 2. Scope Boundaries (hard constraints, do not violate)

1. **The core rule engine is deterministic, not LLM-based.** Do not feed a target server's tool descriptions or schemas into an LLM for judgment. That would reintroduce the exact prompt-injection risk the tool exists to detect. Rules are pattern/heuristic/schema-shape based, written and reviewed by a human.
2. **Default scan targets are localhost or self-hosted fixture servers only.** Do not build default support for scanning arbitrary third-party MCP servers over the network. If external targets are supported at all, they require an explicit, logged consent flag in both the API and the UI, and a README disclaimer.
3. **The scanner only enumerates.** It calls `list_tools`, `list_resources`, `list_prompts`, and reads schemas/descriptions. It never invokes a target server's tools. This boundary must be stated explicitly in `docs/permissions.md`.
4. **Clean-room implementation.** The ruleset is derived from public sources (OWASP MCP Top 10, published MCP security research, general appsec principles). Do not adapt any internal, proprietary, or employer-specific architecture, logic, or threat models into this codebase. This is a public repository for peer review.
5. **Scope is capped at a fixed v1 rule count (~10-12 checks).** Do not let the rule engine grow indefinitely during development. Additional rules go in a "future work" list in the README, not into scope creep.

---

## 3. Course Context

Source rubric is explicitly marked draft for the 2026 cohort; scoring, deadlines, and peer-review mechanics may change before the cohort starts. Re-verify against the live course repository (`DataTalksClub/ai-dev-tools-zoomcamp`) before final submission. Do not assume the rubric in Section 9 is frozen.

Two graded categories are conditional or newly added relative to earlier course material:

- **Agent Extension Pack** (rubric category 12) only applies if the operator has completed Module 3 of the course. Confirm this before scoping that work (see Section 11).
- **Security, Audit, and DevOps Hardening** (rubric category 13) applies regardless of module completion and requires five distinct artifact types, not a single scan.

Peer review is mandatory to receive any project points at all: minimum 3 peer evaluations required, independent of build quality. This is a submission-process requirement, not a code requirement, but failure to do it fails the project.

---

## 4. Required Repository Structure

```
.
├── README.md
├── product-spec.md
├── AGENTS.md
├── openapi.yaml
├── docker-compose.yml
├── frontend/
│   ├── src/
│   │   ├── api/              # single centralized backend client, no scattered fetches
│   │   ├── components/
│   │   ├── pages/
│   │   └── tests/            # Vitest + React Testing Library
│   ├── Dockerfile
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── models/            # SQLAlchemy models
│   │   ├── mcp_client/        # MCP client used to connect to scan targets
│   │   └── rules/             # deterministic check engine, one module per rule
│   ├── alembic/                # migrations
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/        # runs against stub MCP fixture servers
│   ├── Dockerfile
│   └── pyproject.toml
├── .github/
│   └── workflows/
│       ├── ci.yml               # lint, unit tests, integration tests
│       ├── security-scan.yml    # semgrep, syft/grype if in scope
│       └── deploy.yml           # deploy on merge to main after tests pass
├── docs/
│   ├── architecture.md
│   ├── agent-extension-pack.md   # only if Module 3 complete
│   └── permissions.md            # only if Module 3 complete; states enumerate-only boundary
├── security/
│   ├── pr-audit/                 # captured CodeRabbit review artifacts
│   ├── semgrep/
│   │   ├── results.sarif
│   │   └── rules/
│   │       └── no-llm-on-untrusted-mcp-data.yaml
│   ├── sbom/                     # Syft output, if in scope
│   ├── grype/                    # Grype findings, if in scope
│   └── ai-tool-data-policy.md
├── ops/
│   ├── health-sample-output.md   # captured /health, /metrics output
│   └── operational-notes.md
├── agent-capabilities/            # only if Module 3 complete
├── agent-hooks/                   # only if Module 3 complete
├── mcp-server/                    # only if Module 3 complete: exposes scanner as MCP tools
└── custom-agent/                  # or plugins/, only if Module 3 complete
```

---

## 5. Build Plan (phased, in order)

### Phase 0: Setup
- Scaffold repo structure per Section 4.
- Write `product-spec.md` and initial `openapi.yaml` (spec-first, before backend implementation).
- Set up Docker Compose skeleton (frontend, backend, Postgres) even before features exist.

### Phase 1: Core Application (covers rubric categories 1, 3-11, 14)
- Backend: MCP client module, rule engine (deterministic, capped rule set per Section 2), scan/report data model, API endpoints matching `openapi.yaml`.
- Build stub/fixture MCP servers under `backend/tests/fixtures/` representing known-vulnerable patterns (injected description, unconstrained schema, missing annotations, etc.). These serve as integration test targets, not live scan targets.
- Frontend: submit-scan form, scan status view, findings report view, scan diff view.
- Tests: pytest unit tests on the rule engine, integration tests running full scans against fixture servers, Vitest/RTL tests on frontend report rendering and form validation.
- Containerize, verify `docker-compose up` runs the full stack with no manual steps.
- Write `README.md`, `docs/architecture.md`.
- Do not proceed to Phase 2 until this phase's tests pass and the app runs end to end locally.

### Phase 2: Agent Extension Pack (covers rubric category 12, only if Module 3 confirmed complete)
- `mcp-server/`: expose the scanner's own functions (`scan_server`, `get_report`, `diff_scans`) as MCP tools, callable by any MCP-compatible agent.
- `agent-hooks/`: a real guardrail, e.g. a pre-commit or pre-deploy hook blocking the addition of a new MCP server config if its last scan has open Critical findings.
- `agent-capabilities/`: reusable prompt templates / instructions for "audit this MCP server before wiring it in."
- `custom-agent/` or `plugins/`: a subagent specialized in interpreting scan output and recommending remediation.
- `docs/agent-extension-pack.md`: document all of the above together.
- `docs/permissions.md`: explicitly state the enumerate-only boundary from Section 2, item 3.

### Phase 3: Security, Audit, and DevOps Hardening (covers rubric category 13)
- Install CodeRabbit as a GitHub App; capture representative PR review output into `security/pr-audit/`.
- Semgrep: run `p/security-audit` and `p/owasp-top-ten` against `backend/` and `frontend/`, commit SARIF to `security/semgrep/`, wire into CI. Write the custom rule `no-llm-on-untrusted-mcp-data.yaml` that fails CI if data returned from the MCP client's enumeration calls flows into any LLM API call in the codebase, this directly enforces the Section 2 constraint.
- If time permits (see Section 11): Syft to generate SBOMs (CycloneDX) for backend deps, frontend deps, and built images, committed to `security/sbom/`. Grype to consume those SBOMs and produce CVE findings in `security/grype/`, gating CI on Critical/High. If Syft/Grype are cut for time, Semgrep alone satisfies the rubric minimum for this category's scan-artifact requirement.
- `ops/`: add `/health` and `/metrics` endpoints, capture a sample run's output into `ops/health-sample-output.md`.
- `security/ai-tool-data-policy.md`: state what was shared with the AI coding assistant during development (code only, no secrets), and what data (if any) the running application sends to a third-party LLM. Given the Section 2 constraint, the honest statement is that the core rule engine sends nothing to an LLM. If Phase 5 ships, also state exactly which scanner-derived fields go to the hosted decision model (Section 13).

### Phase 4: Deploy and Polish
- Deploy to Render, Fly.io, or Railway as a working URL.
- Finalize `.github/workflows/deploy.yml` to deploy on merge to `main` after tests pass.
- Final pass on `README.md`, `AGENTS.md` (documenting actual AI-assisted development workflow used: prompts, task delegation, context files, manual review steps taken).
- Verify full reproducibility: a fresh clone should be runnable end to end following only the README.

### Phase 5: Decision Model (operator-requested extension, see Section 13)
- Not traceable to a rubric line. The human operator requested it explicitly (2026-10-15), per Section 0.
- Start only after Phase 1 is complete. Do not let it delay Phases 3-4, which are graded.
- Deliver the deterministic policy fallback first, then the hosted-model client.

---

## 6. Functional Spec: Core Scanner

**Data model (minimum):**
- `ScanTarget`: connection info (stdio command or URL), consent flag if external.
- `Scan`: target reference, status, timestamps.
- `Finding`: scan reference, severity (Critical/High/Medium/Low), rule ID, description, remediation text.
- `ScanDiff`: reference to two scans, list of changed/added/removed findings (drift detection).

**API endpoints (draft, finalize in `openapi.yaml` before backend build):**
- `POST /scans` — submit a target, start a scan
- `GET /scans/{id}` — status
- `GET /scans/{id}/report` — findings report
- `GET /scans/{id}/diff/{other_id}` — diff between two scans of the same target

**v1 rule set (capped at ~10-12, do not exceed without explicit sign-off):**
1. Injection patterns in tool descriptions (hidden unicode, "ignore previous instructions" style strings)
2. Unconstrained input schema on sensitive-looking parameters (shell/path/URL with no format/pattern constraint)
3. Missing `readOnly`/`destructive` annotation hints
4. Read-capability + network/write-capability pairing on the same tool or tool set (confused-deputy signal)
5. Unauthenticated transport
6. Overly broad resource URI patterns (wildcard access)
7. Tool description length/entropy anomalies (potential hidden payload)
8. Missing or malformed schema validation on required parameters
9. Prompt-injection patterns in resource content, not just tool descriptions
10. (Diff-only) any finding present in a prior scan of the same target that has since changed severity or been removed without a corresponding description change, flag as drift

---

## 7. Agent Extension Pack Spec

See Phase 2 above for component breakdown. Key requirement: `docs/permissions.md` must state, in plain language, that the MCP server component of this project only reads target-server metadata (tool lists, schemas, descriptions, resource lists) and never calls a target server's tools. This is both a rubric requirement and the actual safety boundary of the whole project.

---

## 8. Security, Audit, and DevOps Hardening Spec

See Phase 3 above. The five required artifact types, restated for clarity:

1. PR audit output (CodeRabbit, captured as files, not left only in the GitHub UI)
2. Deterministic security scan findings (Semgrep, standard + custom rule)
3. Agent/extension security notes (the deterministic-engine design decision, stated explicitly, tied to the custom Semgrep rule)
4. Operational diagnosis output (`/health`, `/metrics`, captured sample)
5. AI tool/data policy document

---

## 9. Rubric to Deliverable Mapping

| # | Category | Max pts | What satisfies max | Where it lives |
|---|---|---|---|---|
| 1 | Problem Description | 2 | Clear README with problem, functionality, expected behavior | `README.md` |
| 2 | AI-Assisted Dev Workflow | 2 | Documents prompts/task delegation, context files, manual review, verification | `AGENTS.md` |
| 3 | Tech & Architecture | 2 | Frontend, backend, DB, containerization, CI/CD roles explained together | `docs/architecture.md` |
| 4 | Frontend | 3 | Functional, centralized API client, tests on core logic with run instructions | `frontend/` |
| 5 | API Contract | 2 | OpenAPI spec written first, used as contract | `openapi.yaml` |
| 6 | Backend | 3 | Well structured, follows spec, tests on core functionality | `backend/` |
| 7 | Database | 2 | Properly integrated, supports multiple environments, documented | `backend/app/models/`, `alembic/` |
| 8 | Containerization | 2 | Full system via Docker Compose, no manual steps | `docker-compose.yml` |
| 9 | Integration Testing | 2 | Clearly separated, covers key workflows, documented | `backend/tests/integration/` |
| 10 | Deployment | 2 | Deployed to cloud, working URL | deploy target + README link |
| 11 | CI/CD | 2 | Runs tests and deploys on pass | `.github/workflows/` |
| 12 | Agent Extension Pack | 2 (conditional on Module 3) | Instructions, workflow, subagent, MCP tool/server, hook/guardrail, permissions notes, all documented | `agent-capabilities/`, `agent-hooks/`, `mcp-server/`, `custom-agent/`, `docs/` |
| 13 | Security/Audit/DevOps Hardening | 2 | All five artifact types present | `security/`, `ops/` |
| 14 | Reproducibility | 2 | Clear end-to-end setup/run/test/deploy instructions | `README.md` |
| — | Peer Review | pass/fail gate + bonus | Minimum 3 peer evaluations completed | course platform, not repo |

---

## 10. Tech Stack Summary

- Frontend: React + TypeScript, Vitest + React Testing Library
- Backend: FastAPI, SQLAlchemy + Alembic
- Database: SQLite (local) / Postgres (prod), switched via environment variable
- Containerization: Docker + Docker Compose
- CI/CD: GitHub Actions
- Deployment: Render, Fly.io, or Railway (single container or compose-based, per course's own reference pattern)
- Security tooling: CodeRabbit, Semgrep (+ custom rule), Syft + Grype (conditional on time budget)

---

## 11. Open Items to Confirm Before Starting

- **Deadline / time budget for this cohort:** unconfirmed. Determines whether Phase 3's Syft/Grype work and the diff-based drift detection feature both fit, or whether either gets cut to "future work" in the README.
- **Module 3 completion status:** unconfirmed. Determines whether Phase 2 (Agent Extension Pack, rubric category 12) is in scope at all.
- **External scan target support:** decide explicitly whether the shipped product supports scanning non-localhost targets with consent flags, or is restricted to fixture/self-hosted servers only. Default to restricted per Section 2 unless there's a specific reason to expand it.

- **Decision model (Section 13):** confirm the hosted model's endpoint, request/response format, auth, data retention terms, and that it is the operator's own model (not employer-owned, per Section 2 item 4).

Do not proceed past Phase 1 without resolving the first two items with the human operator.

---

## 12. Explicit Non-Goals

- Not a general-purpose vulnerability scanner. Scope is MCP server posture specifically.
- Not a live internet-scanning tool. Default targets are local/fixture only.
- Not a reimplementation of any employer-internal architecture or proprietary logic. Ruleset and design are clean-room from public sources.
- The core rule engine is not, and will not become, an LLM-judgment system on untrusted input. This is a permanent constraint, not a v1 limitation to be lifted later.

---

## 13. Decision Model (operator-requested extension)

**Purpose:** answer one question per scan: "Is it safe to connect an agent to this MCP server?" The output is structured data, not prose: a decision (`allow`/`review`/`block`), a score (0-100), and the rule IDs that caused the decision. The operator's own hosted "System 1" decision model (a classifier that returns structured output, not text) produces the verdict. A deterministic policy is the fallback.

**Why this does not violate Section 2 item 1:** the model never sees target-server text. It receives only data that the scanner itself produced. The rule engine stays deterministic and unchanged. The verdict is a separate layer that runs after the rule engine.

**Model input (allowlist, nothing else):**
- Count of findings per severity
- The set of triggered rule IDs (from the fixed v1 list)
- Transport type (`stdio`/`http`) and the `allow_external` flag

**Never sent to the model:** tool/resource/prompt names, descriptions, schemas, finding `subject`/`description`/`title`, target URL, command, or args. All of these are target-derived or can contain target text.

**Enforcement:**
1. A typed input model with enum and integer fields only, and extra fields forbidden. No free-text field exists, so target text cannot be sent.
2. The custom Semgrep rule `no-llm-on-untrusted-mcp-data` also covers the decision-model client.
3. A unit test asserts that the serialized request contains no target-derived string from a fixture scan.

**Safety rules for the output:**
- Validate the model response against the `Verdict` schema. If it is invalid, times out, or the model is not configured, use the deterministic policy.
- Policy floor: the model can make a decision stricter, never less strict. Any Critical finding is always `block`.
- Each verdict records its `source` (`model` or `policy`).

**Deterministic policy (fallback and floor):**
- Score = 100 − (40 × Critical + 20 × High + 5 × Medium + 1 × Low), minimum 0.
- Any Critical → `block`. Score below 70 → `review`. Otherwise `allow`.

**Configuration:** `DECISION_MODEL_URL` and `DECISION_MODEL_API_KEY`. If unset, only the policy runs, so a fresh clone works with no model.

**API:** `GET /api/scans/{id}/verdict` (see `openapi.yaml`).

**Scope:** not a rule. It does not count against the Section 2 item 5 rule cap. Record what is sent to the model in `security/ai-tool-data-policy.md`. Decision record: `docs/decisions/2026-10-15-decision-model.md`.
