# Task Tracker

The task tracker is **GitHub Issues**, public at
<https://github.com/cjbischoff/mcp-security-posture-scanner/issues>.
This file is a pointer and an evidence index; the acceptance criteria live
in the issues.

## How tasks are written

- One issue per work stream, with an **Acceptance criteria** checklist
  (`- [ ]` items that a command or artifact can prove).
- Commits reference the issue in the body: `Refs #N` while work is in
  progress, `Closes #N` on the commit that completes it. Find them with
  `git log --grep "#"`.
- The agent that did the work comments on the issue with evidence (test
  output, trace IDs, incident reports). See [`agent-team.md`](agent-team.md).

## Labels

| Label | Meaning |
|---|---|
| `area:backend`, `area:frontend`, `area:ci-cd`, `area:observability`, `area:oncall`, `area:docs` | Part of the system |
| `agent:builder` | Built by a builder subagent |
| `agent:orchestrator` | Done by the orchestrator session |
| `backlog` | Not scheduled |

## Issues and evidence

"Closed by commit" means a `Closes #N` commit is on `feature/core-scanner`
(PR [#13](https://github.com/cjbischoff/mcp-security-posture-scanner/pull/13));
GitHub closes the issue when the PR merges to `main`.

| Issue | Title | Status | Evidence commits |
|---|---|---|---|
| [#2](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/2) | Backend: scan API, enumeration-only MCP client, 10 deterministic rules | Closed | `9b844f6` (PR #1) |
| [#3](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/3) | Frontend: scan form, scan list, report and diff pages | Closed | `22fecd4` (PR #1) |
| [#4](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/4) | Security: public mode must not run arbitrary stdio commands | Closed | `a3513bb` |
| [#5](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/5) | CI: green lint and tests on every PR, one test command | Closed | `a9610a6`, `00c9eb9` |
| [#6](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/6) | Persistence: scans, targets, findings stored in Postgres | Closed | `36d3453`, `de6d6d8` |
| [#7](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/7) | Observability: traces, metrics, JSON logs share one trace ID | Closed by commit | `58e4b7c`, `84f7f0a`, `7c86fdc` |
| [#8](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/8) | Alerting: ScanFailureRateHigh alert and a trigger to fire it | Closed by commit | `58e4b7c`, `84f7f0a`, `7c86fdc` |
| [#9](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/9) | On-call agent: wakes on the alert and fixes the incident | Closed by commit | `e53b039`, `aeae48c`, `ce6365f` |
| [#10](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/10) | CD: auto deploy to dev, manual prod, rollback by SHA, public URL | Open (hosting setup pending) | `45923ef`, `668eb91` |
| [#11](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/11) | Docs: agent team spec, tracker evidence, README matches reality | Closed by commit | see `git log --grep "#11"` |
| [#12](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/12) | Phase 5: decision-model verdict endpoint | Backlog | `f802f9b` (spec only) |

Earlier phase plans (before the move to GitHub Issues) are in
[`.planning/`](../.planning/).
