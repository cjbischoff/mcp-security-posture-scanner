# Phase 4: Security/Audit/DevOps Hardening

## Status

Planned (3 plans, not started)

## Requirements mapped

R-10 (Deployment — documented as local-first, no cloud), R-11 (CI/CD), R-13 (Security artifacts: Semgrep, SBOM, PR audit, AI policy, ops), R-15 (Peer review — documented, completed on course platform)

## Plans

| # | Plan | Status | Critical test |
|---|---|---|---|
| 4.1 | Semgrep full scan + SBOM | ○ Pending | SARIF valid JSON; SBOM generates |
| 4.2 | PR audit log + AI tool data policy | ○ Pending | Policy accurately describes data flows |
| 4.3 | Agent/extension notes + final README + full smoke | ○ Pending | Full smoke: pytest (86) + npm test (26) + smoke.py + compose build + semgrep all green |

## Full smoke verification (Plan 4.3)

```bash
cd backend && uv run pytest -v                    # 86 passing
cd frontend && npm test                           # 26 passing
cd backend && uv run python scripts/smoke_test.py  # 6 findings, 5 rules
docker compose build                              # both images build
semgrep --config security/semgrep/rules/ backend/ --error  # 0 findings
```

## Decisions

- No cloud deployment — focus on local reproducibility
- SBOM is conditional on `syft` being available; if not, command is documented
- PR audit log records manual review process (CodeRabbit not installed)
- Final README is the primary deliverable for reproducibility (R-14)
