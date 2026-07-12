---
name: frontend-backlog
description: Maintain the frontend finding ledger and exactly one active GitHub improvement issue. Use after frontend audits to verify GitHub prerequisites, deduplicate open findings, select the highest-leverage unblocked root cause, publish or update the single `frontend-quality` issue, record explicit resolution/rejection/defer decisions, and clean up large evidence.
---

# Frontend Backlog

Keep every validated observation locally, but expose only one actionable improvement in GitHub.

Read [references/github-workflow.md](references/github-workflow.md) and the shared [finding contract](../frontend-audit/references/contracts.md).

## Prerequisites

Run `scripts/check-github-prereqs.mjs` before expensive inspection. Stop if:

- `gh` is missing or unauthenticated;
- the current Git repository cannot be resolved through GitHub;
- more than one open issue has the `frontend-quality` label.

GitHub Issues is the only version-one work-tracker backend. Do not create a local active-backlog file.

## Workflow

1. Ensure `.ui-quality/POLICY.md` exists. Append validated finding records to `.ui-quality/findings.jsonl`.
2. Deduplicate only against open findings. Resolved findings do not participate in recurrence tracking.
3. Query open GitHub issues labeled `frontend-quality`.
4. If one exists, inspect and re-audit that issue only. Do not promote another finding.
5. Close the active issue only after one of these outcomes:
   - verified fix;
   - not reproduced (`reason: not-reproduced`);
   - explicit human rejection;
   - explicit human defer.
6. When no active issue exists, run `scripts/select-frontier.mjs .ui-quality/findings.jsonl` and choose exactly one unblocked root cause.
7. Ensure labels `frontend-quality` and `ui-policy-approved` exist, then create one issue using the required template.
8. Write the issue number/URL back to the selected finding.
9. Delete large local evidence when the issue closes; retain concise measurements, locations, dates, and reason in the ledger.

## Policy proposals

A proposal is eligible only after three independent examples and explicit human approval. Approval may be the `ui-policy-approved` label or a direct approval instruction. Update `POLICY.md` only after approval, cite evidence and issue URL, then close the issue.

## Boundaries

- Never create a second active issue, including a second blocker.
- Never auto-defer. Require an explicit defer decision.
- Do not use `unverified` or recurrence tracking.
- Do not upload secrets or private payloads as evidence.
- Do not create labels or issues in a different repository from the current Git remote.
