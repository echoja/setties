---
name: frontend-browser-inspect
description: Collect factual frontend runtime evidence with one reusable Playwright CLI session. Use when an audit needs rendered DOM structure, data-ui semantic states, accessibility snapshots, geometry, computed styles, interaction states, responsive behavior, console/network signals, or targeted screenshots without making design judgments.
---

# Frontend Browser Inspect

Collect facts. Do not decide whether the UI is good or bad.

Read [references/evidence-protocol.md](references/evidence-protocol.md) and the shared [finding contract](../frontend-audit/references/contracts.md). Use the installed `playwright-cli` skill for commands and session semantics.

## Session lifecycle

1. Prefer an explicit URL, then an existing local server, then the project's existing `dev`/`start` command.
2. Start a server only when unambiguous. Record its process and stop only what this inspection started.
3. Open one semantic session such as `<repo>-frontend-audit`.
4. Load configured storage state when authentication is needed.
5. Reuse the same session for every route, state, viewport, and atomic audit step.
6. Close the session at audit end. Do not leave a browser process running across audits.
7. Save/load storage state across runs when configured; use a persistent profile only when storage state is insufficient.

## Evidence escalation

Use the cheapest evidence that can prove the observation:

1. accessibility snapshot;
2. targeted DOM attributes and `data-ui-state`;
3. bounding boxes and computed styles;
4. console and network evidence;
5. targeted component screenshot;
6. full-page or multi-viewport screenshots only when necessary.

Do not capture a responsive screenshot matrix by default.

## Inspection workflow

1. Navigate to the scoped route through the application's normal setup.
2. Take a shallow snapshot, then inspect only suspicious subtrees.
3. Inventory `[data-ui-component][data-ui-state]` elements. Record component, semantic state dimensions, role/name, and bounding box.
4. Confirm `@ui-inspectable` components identified by static analysis actually expose attributes when rendered.
5. Exercise relevant keyboard, focus, hover, active, disabled, loading, empty, error, success, modal, menu, and return-focus states.
6. Resize only when responsive evidence is relevant. Check overflow, reflow, long labels, density, and layout reorganization.
7. Capture console/request evidence only when it explains a visible or structural failure.
8. Save large artifacts under `.ui-quality/evidence/<fingerprint>/` only for the active finding.
9. Return factual evidence in the protocol format. Leave severity and recommendations to `frontend-heuristic-audit` or deterministic source rules.

## Human input

When MFA, CAPTCHA, consent, or account selection is required, keep the existing session and use `playwright-cli show --annotate`. Let the user interact directly. Never request passwords or one-time codes in chat. Do not auto-defer blocked work.

## Boundaries

- Do not modify application code or data intentionally.
- Do not perform destructive workflows.
- Do not call an unsupported component “passing.”
- Do not infer aesthetic quality from a screenshot.
- Do not retain large evidence after the active finding closes.
