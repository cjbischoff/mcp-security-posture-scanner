## Decision: Add a hosted decision model that produces a per-scan verdict from scanner-derived data only

## Context
The operator asked to add a "System 1" decision model: a classifier that
returns structured output (decision, score), not prose. The operator has their
own hosted model with this function. Brief Section 2 item 1 forbids feeding
target-server descriptions or schemas to an LLM for judgment.

## Alternatives considered
- Model classifies target descriptions (injection probability) — rejected.
  It breaks Section 2 item 1 and brings back the prompt-injection risk the
  scanner detects.
- Model as an offline evaluation tool for the rules only — rejected as the
  main feature. It does not give users a decision.
- Deterministic verdict only, no model — kept as the fallback and floor.
- **Chosen:** hosted model produces the verdict from scanner-derived counts and
  rule IDs only, with a deterministic policy as fallback and floor.

## Reasoning
The model never sees target text, so Section 2 item 1 holds. The rule engine
stays deterministic and unchanged. The typed input (enum and integer fields
only) makes it impossible to send target text. The policy floor means a model
error can only make a verdict stricter.

## Trade-offs accepted
- The input has little information (counts and rule IDs). The model cannot
  find risks that the rules miss.
- Not traceable to a rubric line. Added as Phase 5 so it does not delay
  graded work.
- Adds an external network dependency, and scan metadata (counts, rule IDs)
  leaves the host. This must be stated in `security/ai-tool-data-policy.md`.
- Open: endpoint, request/response format, auth, and data retention of the
  hosted model are not confirmed yet.

## Supersedes
none
