# GitHub workflow

## Invariant

Exactly zero or one open issue may carry the `frontend-quality` label.

Create labels when absent:

```bash
gh label create frontend-quality --color B60205 --description "Single active frontend quality improvement" --force
gh label create ui-policy-approved --color 0E8A16 --description "Human-approved UI policy proposal" --force
```

## Issue template

```markdown
<!-- frontend-quality:fingerprint=<fingerprint> -->

## Problem

<one root cause, not a list of unrelated findings>

## Why this is first

- Prerequisite/dependency impact:
- User impact:
- Downstream findings suppressed:

## Evidence

- Source:
- Runtime:
- Policy or baseline:

## Required change

<smallest coherent improvement; audit does not implement it>

## Verification

- [ ] Original static or runtime check passes
- [ ] Affected browser state is reproduced and passes
- [ ] No equal-or-higher-severity regression appears in scope
```

## Transitions

Fixed:

```bash
gh issue comment <number> --body "Verified: <concise evidence>"
gh issue close <number> --reason completed
```

Not reproduced:

```bash
gh issue comment <number> --body "Resolved: not reproduced during <scope/date>."
gh issue close <number> --reason completed
```

Rejected or explicitly deferred: record the human decision in a comment, then close. Do not preserve a GitHub queue.

## Active issue first

When an active issue exists, verification of that issue precedes new finding promotion. The ledger may continue receiving validated observations, but no other issue is created.
