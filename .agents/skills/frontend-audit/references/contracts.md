# Frontend audit contracts

## Compatibility

React-specific instrumentation is validated only with:

- React 19.2
- TypeScript 7

Other versions may not work. Detect and report versions, then obtain explicit confirmation before running React-specific checks. Runtime DOM inspection is framework-neutral. React Native is outside the HTML `data-*` protocol.

## Project artifacts

Create only:

```text
.ui-quality/
├── POLICY.md
└── findings.jsonl
```

Minimal `POLICY.md`:

```markdown
# UI Policy

## Foundational Principles

<!-- Human-owned. Agents may propose changes but cannot edit automatically. -->

## Established Rules

<!-- Human-authored or explicitly approved. -->

## Canonical Sources

<!-- Reference token, theme, component-library, and design documentation paths. -->
```

Do not copy canonical design-token values into `.ui-quality`. Discover them from code or reference their paths.

## Finding record

Store one JSON object per line. Preserve concise evidence after large files are removed.

```json
{
  "fingerprint": "rule-id:scope:component:state",
  "rule_id": "spacing.proximity.too-tight",
  "status": "open",
  "reason": null,
  "severity": "P1",
  "confidence": "high",
  "scope": "src/checkout",
  "component": "checkout-form",
  "state": "submission:error",
  "source": ["src/checkout/CheckoutForm.tsx:42"],
  "evidence": ["gap=4px; canonical peer-control token=8px"],
  "impact": "Adjacent actions are difficult to distinguish and operate.",
  "recommendation": "Use the peer-control spacing token.",
  "blocked_by": [],
  "prerequisite_depth": 0,
  "downstream_count": 0,
  "user_impact": "high",
  "estimated_effort": "small",
  "github_issue": null,
  "observed_at": "2026-07-12T00:00:00Z"
}
```

Allowed status values:

- `open`
- `resolved`
- `rejected`
- `deferred`

Use `reason: "fixed"` or `reason: "not-reproduced"` for resolved findings. Do not create an `unverified` state or recurrence relationships. Deduplicate only against open findings.

## Severity

- `P0`: blocks a core user task or creates immediate severe risk.
- `P1`: substantial user or maintenance impact that should precede other work.
- `P2`: meaningful but non-blocking problem.
- `P3`: low-impact polish or cleanup.

## Single frontier

The ledger may contain many findings. GitHub contains exactly zero or one open issue labeled `frontend-quality`.

Select the highest-leverage unblocked root cause by:

1. prerequisite depth and downstream count;
2. user impact;
3. severity;
4. confidence;
5. smaller safe change when otherwise tied.

Never promote a dependent finding while its root cause remains open. Never promote another issue until the active issue is resolved, rejected, or explicitly deferred.

## Policy proposals

Do not edit policy unless both conditions hold:

1. the same intentional pattern appears in at least three independent places; and
2. a human explicitly approves the proposal.

Use the GitHub label `ui-policy-approved` or a direct approval instruction. Add the approved rule under `Established Rules` with approval date, evidence, and issue link, then close the issue.

## Production diagnostics

Allow bounded semantic diagnostics that explain behavior already delivered to the browser. Forbid secrets and private payloads.

Allowed examples:

```text
submission:error
error-code:payment-timeout
experiment:new-checkout
```

Forbidden examples:

```text
access-token:...
card-number:...
user-email:...
cross-tenant-id:...
```

Never use client metadata as an authorization input.
