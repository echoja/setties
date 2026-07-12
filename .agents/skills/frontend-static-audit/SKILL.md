---
name: frontend-static-audit
description: Run non-mutating frontend source analysis using the project's configured linters first, then trusted established rules, then small independent custom checks. Use when checking design-token usage, React component instrumentation, maintainability, semantics, or other frontend rules that source analysis can prove without a browser.
---

# Frontend Static Audit

Find source-backed problems without editing code or configuration.

Read [references/rule-discovery.md](references/rule-discovery.md) before recommending or creating a rule. Read the shared [finding contract](../frontend-audit/references/contracts.md) before emitting findings.

## Workflow

1. Scope to explicitly named files/components or current frontend changes. Include changed shared primitives.
2. Inventory package manifests, lint configuration, framework configuration, canonical token/theme sources, and existing scripts.
3. Detect React and TypeScript versions with `scripts/detect-react-compat.mjs` when React-specific checks apply.
   - Acceptance target: React 19.2 and TypeScript 7.
   - Require explicit confirmation for other versions.
4. Run the project's configured checks first. Preserve their native rule IDs and file locations.
5. Search for a trusted established rule before proposing custom analysis.
6. If a high-value established rule is absent or disabled, strongly recommend installing/enabling it. This tooling prerequisite may outrank individual defects.
7. Use an independent custom check only when established rules cannot express the requirement accurately.
   - Prefer one ast-grep YAML rule.
   - Use one small executable detector only when structural matching is insufficient.
8. Normalize only validated results into the shared finding schema. Do not persist weak suspicions.

## React state instrumentation

Version one supports the reference contract only on the stated acceptance target. A component opts in with:

```tsx
/** @ui-inspectable */
export function CheckoutForm() {
  return (
    <form
      {...uiStateProps("checkout-form", {
        submission: "idle",
        validation: "invalid",
      })}
    />
  );
}
```

Use [assets/ui-state-props.ts](assets/ui-state-props.ts) as a reference implementation, not as a file to copy automatically. Run the independent `checks/require-ui-state-props` check only after compatibility confirmation.

The check's own fixtures declare the acceptance versions in their local `package.json`; run their `tests/run.mjs` self-test directly.

The check proves that marked components attach `uiStateProps(...)` structurally. Browser inspection separately proves that `data-ui-component` and `data-ui-state` reached a real DOM element.

## Design-system checks

- Discover canonical tokens from CSS variables, framework themes, Style Dictionary, or project documentation.
- Reference canonical sources from policy; never maintain a duplicate token registry.
- Distinguish token definitions from token consumers.
- Treat internal consistency, arbitrary literals, duplicate component implementations, boolean-prop growth, and unclear primitive/wrapper boundaries as static candidates when source evidence is sufficient.

## Boundaries

- Do not install dependencies, edit lint configuration, add suppressions, or apply fixes.
- Do not create a custom rule merely because an established rule is not installed.
- Keep every custom check independently runnable and tested.
- Do not treat unsupported syntax as passing; report the limitation.
- Do not enforce aesthetic taste.
