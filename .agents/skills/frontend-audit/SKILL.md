---
name: frontend-audit
description: Orchestrate a change-focused frontend quality audit across source checks, Playwright browser evidence, policy-aware heuristics, and a single GitHub improvement issue. Use when auditing current frontend work, reviewing UI quality, checking design-system adherence, or choosing the next frontend improvement. Requires authenticated GitHub CLI and delegates to the four atomic frontend audit skills.
---

# Frontend Audit

Coordinate the audit. Own no lint rules, browser judgments, or backlog logic.

Read [references/contracts.md](references/contracts.md) before doing any work. Use these sibling skills in order when their lane applies:

1. `frontend-static-audit`
2. `frontend-browser-inspect`
3. `frontend-heuristic-audit`
4. `frontend-backlog`

## Workflow

1. Verify the current directory is a Git repository with a GitHub remote.
2. Run the `frontend-backlog` GitHub prerequisite check. Stop before expensive inspection if `gh` is missing, unauthenticated, or cannot view the repository.
3. Create `.ui-quality/POLICY.md` from the minimal template in the contracts reference when absent. Create `findings.jsonl` only after validating the first finding.
4. Set scope:
   - Use an explicitly named file, component, route, or flow.
   - Otherwise inspect current frontend changes and their affected routes/shared primitives.
   - Audit the whole application only when explicitly requested.
5. Detect React and TypeScript versions before React-specific checks.
   - Acceptance target: React 19.2 and TypeScript 7.
   - If either differs, warn that other versions may not work and require explicit confirmation before React-specific static checks.
   - Framework-neutral browser inspection may continue.
6. Run `frontend-static-audit`. Prefer installed and trusted lint rules; do not install, configure, or fix anything.
7. Run `frontend-browser-inspect` when rendered evidence is relevant and the app can run safely.
8. Run `frontend-heuristic-audit` only on concrete evidence. Never convert unsupported aesthetic opinion into a finding.
9. Normalize validated findings using the shared contract and append them to the ledger.
10. Run `frontend-backlog` to preserve exactly zero or one open `frontend-quality` GitHub issue.
11. Stop any development server and Playwright session started by this audit. Retain large evidence only for the active finding.

## Boundaries

- Do not modify application code, dependencies, lint configuration, or canonical design-token sources.
- Audit-owned files and an explicitly approved policy update are the only writes.
- Do not invent project principles. Baseline checks still run when policy is sparse.
- Do not create a second GitHub issue while one `frontend-quality` issue is open.
- Do not auto-defer an active issue. Human input is required.
- When human browser input is required, let the user interact through the existing Playwright session; never request secrets in chat.
- CI behavior is outside version-one scope.

## Human-input checkpoint

Ask one concrete question with a recommended answer. Preserve collected evidence and keep the active issue unchanged. Continue independent read-only inspection only when safe; promote nothing else until the human answers or explicitly defers the issue.
