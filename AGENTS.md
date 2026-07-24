# AGENTS.md — AI-Assisted Development Workflow

This file documents how AI tooling is used to build this project (rubric
category 2). It is a running log, updated per phase.

## Ground rules given to every agent

- `mcp-scanner-project-brief.md` is the single source of truth; Section 2
  constraints are non-negotiable (deterministic rules, enumerate-only,
  localhost defaults, clean-room, capped rule set).
- Spec-first: `openapi.yaml` is written before backend code and used as the
  contract by both frontend and backend work.
- No target-server data ever flows to an LLM in the application itself; the
  AI assistance documented here is development-time only.

## Workflow pattern

1. **Context files:** agents are pointed at `CLAUDE.md` (constraints +
   commands), `product-spec.md`, and `openapi.yaml` before any code task.
2. **Task delegation:** backend and frontend are built by separate agent
   sessions against the shared OpenAPI contract; root-level artifacts
   (compose, CI, docs) are handled in the orchestrating session.
3. **Manual review:** every agent-produced diff is reviewed by the human
   operator before commit; commits are conventional-format and GPG-signed.
4. **Verification:** work is accepted only when the real commands pass —
   `uv run pytest`, `npm test`, `npx tsc --noEmit`, `docker compose up`.

## Session log

| Date | Phase | What AI did | Human review/verification |
|---|---|---|---|
| 2026-07-23 | 0 | Verified brief against live course rubric; scaffolded repo per brief Section 4; drafted `product-spec.md`, `openapi.yaml`, compose + CI skeletons, docs | Operator reviewed scope, corrected an over-eager start on Phase 1 implementation (reverted; Phase 1 not yet authorized) |

## Prompts and delegation records

Representative prompts, delegation boundaries, and review notes are appended
here as each phase executes. (Phase 1 not started.)
