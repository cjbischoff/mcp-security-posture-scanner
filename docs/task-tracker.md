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

Status from `gh issue list --state all` on 2026-10-17. Numbers 13, 15,
16, 17, and 27 are pull requests. Issues #2-#11 were opened after most of
their work was done; see the timestamps in
[`agent-team.md`](agent-team.md#how-the-tracker-was-used-timestamps).

| Issue | Title | Status | Evidence commits |
|---|---|---|---|
| [#2](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/2) | Backend: scan API, enumeration-only MCP client, 10 deterministic rules | Closed; one criterion not met (MCP-005, see #21) | `9b844f6` (PR #1) |
| [#3](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/3) | Frontend: scan form, scan list, report and diff pages | Closed | `22fecd4` (PR #1) |
| [#4](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/4) | Security: public mode must not run arbitrary stdio commands | Closed | `a3513bb` |
| [#5](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/5) | CI: green lint and tests on every PR, one test command | Closed | `a9610a6`, `00c9eb9` |
| [#6](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/6) | Persistence: scans, targets, findings stored in Postgres | Closed | `36d3453`, `de6d6d8` |
| [#7](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/7) | Observability: traces, metrics, JSON logs share one trace ID | Closed (PR #13) | `58e4b7c`, `84f7f0a`, `7c86fdc` |
| [#8](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/8) | Alerting: ScanFailureRateHigh alert and a trigger to fire it | Closed (PR #13) | `58e4b7c`, `84f7f0a`, `0959018` |
| [#9](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/9) | On-call agent: wakes on the alert and fixes the incident | Closed (PR #13); defect found later, see #25 | `e53b039`, `aeae48c`, `ce6365f` |
| [#10](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/10) | CD: auto deploy to dev, manual prod, rollback by SHA, public URL | Closed; rollback tested on dev only, see #26 | `45923ef`, `668eb91`, `5f8a9a8` |
| [#11](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/11) | Docs: agent team spec, tracker evidence, README matches reality | Closed (PR #13) | `4da9a04`, `94ec19e`, `ae2e2e8`, `d91154f` |
| [#12](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/12) | Phase 5: decision-model verdict endpoint | Open, backlog (not graded) | `f802f9b` (spec only) |
| [#14](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/14) | Observability: send deployed telemetry to Grafana Cloud, keep local LGTM | Closed (PR #15) | `b62af72`, `bbb5122`, `510193c`, `9e7d158`, `a48d5b9` |
| [#18](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/18) | UI: failed scan error, report polling, diff link | Closed; PR #27, verified on prod `82e6f42` | `b6f2d2f`, `8fbcfc4` (PR #27) |
| [#19](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/19) | Backend: reconnect after idle DB (pool_pre_ping) | Closed; PR #16, verified on prod (201 after 7 idle min) | `be1ca1b`, `47cacb7` (PR #16) |
| [#20](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/20) | CI/CD: block fork workflow_run deploys, SHA-pin actions, protect main | Closed; PR #17 + branch protection; prod self-review accepted (sole maintainer) | `56800c6` (PR #17) |
| [#21](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/21) | Rule MCP-005 is dead code: implement it or drop it from the rule count | Closed; PR #29 (MCP-005 unregistered, 9 active rules) | — |
| [#22](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/22) | Observability: strip query strings from span URLs, drop health-check traces | Closed; PR #29 | — |
| [#23](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/23) | Backend: validate scan input (http without url, name length, NUL byte returns 500) | Closed; PR #29 | — |
| [#24](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/24) | Tests: tighten weak assertions, fail polling loops on timeout, no public-host URLs | Closed; PR #29 | — |
| [#25](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/25) | On-call: clear a fault only if it is active, and authenticate /alert | Closed; PR #30 | — |
| [#26](https://github.com/cjbischoff/mcp-security-posture-scanner/issues/26) | CD: run a prod rollback drill | Closed; prod rollback run 39047623170 → `ae229fc`, roll-forward run 39063223640 → `d59093c` | — |

Earlier phase plans (before the move to GitHub Issues) are in
[`.planning/`](../.planning/).
