---
name: frontend-heuristic-audit
description: Evaluate concrete frontend browser evidence against human-authored UI policy and conservative usability/consistency baselines. Use when judging spacing, grouping, hierarchy, density, interaction feedback, responsive adaptation, or repeated UI patterns that deterministic source rules cannot fully prove. Produces evidence-backed findings only and never enforces aesthetic taste.
---

# Frontend Heuristic Audit

Turn runtime facts into cautious, traceable judgments.

Read [references/baseline-principles.md](references/baseline-principles.md), the browser [evidence protocol](../frontend-browser-inspect/references/evidence-protocol.md), and the shared [finding contract](../frontend-audit/references/contracts.md).

## Workflow

1. Read `.ui-quality/POLICY.md` and its canonical source references.
2. Separate three classes:
   - explicit project rule;
   - conservative baseline principle;
   - unsupported aesthetic preference.
3. Evaluate only the scoped browser observations. Do not reread the whole application unless requested.
4. Require concrete evidence before creating a finding:
   - relevant snapshot or screenshot;
   - measured geometry/computed styles when available;
   - violated project rule or named baseline principle;
   - clear user or maintenance impact.
5. Emit no finding for “feels weak,” “looks dated,” or similar unsupported taste.
6. Correlate repeated evidence to a root cause. Prefer one systemic finding over many DOM-instance findings.
7. Assign confidence and severity using the shared contract. Persist only validated findings.
8. Create a `policy-proposal` candidate only when the same intentional pattern appears in at least three independent places.
9. Never edit policy until a human explicitly approves the active GitHub proposal. Then add the narrow rule under `Established Rules` with evidence and issue link.

## Policy behavior

- Sparse or missing policy does not block baseline checks.
- Do not invent colors, spacing scales, component APIs, or aesthetic direction.
- Discover canonical token values from referenced code rather than copying them into policy.
- A project rule overrides a general heuristic unless it creates a standards or security failure; report that conflict explicitly.

## Boundaries

- Do not modify application code.
- Do not enforce fashionable fonts, layouts, card styles, color taste, animation taste, or “anti-AI” aesthetics.
- Do not convert low-confidence opinion into a ledger record.
- Do not create GitHub issues directly; hand validated findings to `frontend-backlog`.
