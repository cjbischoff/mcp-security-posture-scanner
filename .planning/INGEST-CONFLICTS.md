# Conflict Detection Report

## BLOCKERS (0)

No blockers found.

## WARNINGS (0)

No warnings found.

## INFO (3)

[INFO] API endpoint path variant — auto-resolved by precedence
  Found: PRD (Section 6) drafts endpoints as `POST /scans`, `GET /scans/{id}/report`, etc. (no `/api` prefix). SPEC defines endpoints as `POST /api/scans`, `GET /api/scans/{id}/report`, etc. Architecture.md and permissions.md consistently use `/api/scans`.
  Note: The PRD explicitly marks its endpoints as "(draft, finalize in `openapi.yaml` before backend build)", delegating to the spec-first process. SPEC (higher precedence) wins. The `/api` prefix is the resolved path.
  → No action needed. SPEC takes precedence per rules: SPEC > PRD.

[INFO] docs/permissions.md exists ahead of its formal phase
  Found: PRD Phase 2 scopes `docs/permissions.md` to the Agent Extension Pack ("only if Module 3 complete"). However, the file already exists and contains critical safety boundary information that applies to the entire project regardless of Module 3 status.
  Note: The PRD also states (Section 2, item 3) that the enumerate-only boundary "must be stated explicitly in docs/permissions.md" — this is a project-wide requirement, not scoped to Phase 2. The file's existence is correct and consistent with the constraint documentation need.
  → No action needed. The file's content is accurate and its existence pre-dates its formal phase assignment.

[INFO] Decision model PRD/ADR cross-reference is not a contradiction
  Found: PRD Section 13 proposes the decision model as an operator-requested extension. ADR (2026-10-15-decision-model.md, LOCKED) formalizes the same concept with identical constraints (typed input, policy floor, no target text). The two documents reference each other cyclically (PRD → ADR, ADR → PRD Section 13).
  Note: This is a healthy cross-reference pattern, not a contradiction. The ADR formalizes (and LOCKs) what the PRD proposes. Both agree on every constraint. ADR takes precedence for implementation details of the decision model; PRD takes precedence for its placement in Phase 5 and the scope boundaries it must satisfy.
  → No action needed. Documents are consistent.

---

GSD > No conflicts detected.
