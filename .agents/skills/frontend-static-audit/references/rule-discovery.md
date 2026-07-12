# Rule discovery

## Selection order

1. Built-in rule from the configured project linter.
2. Official language or framework plugin.
3. Widely adopted, actively maintained ecosystem plugin.
4. Independent rule with verifiable source, tests, compatibility, and license.
5. Independent custom check.

Do not use popularity alone. Verify primary documentation, maintenance, supported versions, tests, license, false-positive risk, and exact coverage.

## Missing rules

When a trusted rule exists but is absent:

- name the package and exact rule;
- cite its primary documentation;
- explain what findings it replaces;
- provide installation, configuration, and verification commands;
- emit a tooling-prerequisite candidate when adopting it unlocks substantial coverage;
- do not install or configure it.

## Custom checks

Use ast-grep when local syntax and structural relationships are sufficient. Each rule owns one directory:

```text
checks/<rule-id>/
├── check.yml
├── rule.yml
└── tests/
```

Run independently:

```bash
ast-grep scan -r checks/<rule-id>/rule.yml <paths>
```

If a check requires cross-file resolution or genuine data flow, use a small executable detector with its own fixtures. Do not enlarge an ast-grep rule until it becomes opaque or unreliable.

## Output discipline

Preserve upstream rule IDs. For custom rules, use stable dotted or kebab-case IDs. Report source location, impact, recommendation, confidence, and whether the result is deterministic or heuristic.
