# Agent Team Specification

## Roles

| Agent | Role | Responsibilities |
|---|---|---|
| **Orchestrator** (Claude) | Project lead, planner, reviewer | Decomposes phases into plans, delegates work, reviews all output before commit, runs verification gates |
| **Classifier** (gsd-doc-classifier) | Document analyst | Classifies planning documents as ADR/PRD/SPEC/DOC, extracts title/summary/scope |
| **Synthesizer** (gsd-doc-synthesizer) | Document integrator | Merges classified docs into intel files, detects cross-doc conflicts, applies precedence rules |
| **Roadmapper** (gsd-roadmapper) | Phase planner | Creates ROADMAP.md from requirements with goal-backward success criteria, validates 100% coverage |
| **Researcher** | Technical investigator | Researches technical approaches, SDK APIs, best practices before implementation |
| **Planner** | Plan decomposer | Breaks phases into executable plans with RED/GREEN/REFACTOR steps |
| **Checker** (plan-checker) | Quality gate | Reviews plan quality, coverage, and testability before execution starts |
| **Builder** (Claude) | Implementer | Writes code following TDD: RED (failing test) → GREEN (implementation) → REFACTOR (improve) |

## Process

### Phase lifecycle

```
Research → Plan → Approve → Execute → Verify → Review
```

Each phase follows this cycle:

1. **Research** — Researcher investigates technical approaches
2. **Plan** — Planner decomposes into executable plans with tests
3. **Approve** — Human operator reviews plan and approves or revises
4. **Execute** — Builder implements RED → GREEN → REFACTOR per plan
5. **Verify** — All tests pass; full smoke test passes; operator confirms
6. **Review** — Checker validates plan coverage; operator signs off

### How agents work together

- **Orchestrator** owns the conversation and context. It loads planning docs, runs `/gsd-ingest-docs`, delegates to sub-agents, and writes final output.
- **Sub-agents** (Classifier, Synthesizer, Roadmapper, Planner, Checker) run in isolated contexts. They read context files, produce structured output, and return results to the orchestrator.
- **Builder** follows TDD strictly: never writes production code before a failing test exists.
- **Verification gate:** Every plan must pass `uv run pytest -v` before the orchestrator accepts it as complete.

### Communication pattern

```
Orchestrator → spawns parallel Classifiers (one per doc)
  → Synthesizer (reads all classifications, merges)
  → Roadmapper (creates PLAN.md from requirements)
  → Planner (decomposes phase into plans)
  → Checker (reviews plans)
  → Builder (implements plan with TDD)
  → Operator (reviews diff, approves/rejects)
```

### Tools used by agents

| Tool | Purpose |
|---|---|
| `Read`, `Write`, `Edit` | File operations |
| `Grep`, `Glob` | Code search and navigation |
| `Bash` | Running tests, build commands, Docker |
| `Task` / subagents | Parallel classification, research, planning |
| `Ask` / user prompts | Approval gates at phase boundaries |

## Context management

All agents receive these context files before any code task:
- `CLAUDE.md` — constraints and commands
- `mcp-scanner-project-brief.md` — single source of truth
- `product-spec.md` — functional spec
- `openapi.yaml` — API contract (spec-first)

Output is structured into `.planning/` for traceability. Each phase has its own `CONTEXT.md` under `.planning/phases/NN-phase-name/`.
