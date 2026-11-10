---
name: maintain-repo
description: "Manually maintain a selected repository: fix dependency updates, verify them, merge, deploy, and check that obsolete temporary resources are removed."
---

# Maintain a repository

Carry dependency updates through working code, verified merges, deployment, and
temporary-resource cleanup. Start only when explicitly invoked; create no schedule
or background maintenance service.

Accept a local path, repository URL, or `owner/repo`, optionally restricted to PRs
or packages. With no target, use the current Git repository; ask if the target is
ambiguous. Examples:

```text
$maintain-repo https://github.com/echoja/tanstack-demo
$maintain-repo ~/works/another-app, only PRs 12 and 18
$maintain-repo owner/repo, check only
```

An ordinary maintenance invocation covers necessary code fixes, commits, pushes,
update PRs, merges after verification, and the repository's existing release or
deployment process. A narrower request such as "check only" or "leave PRs open"
takes precedence. Honor existing user and repository restrictions; use permissions
already granted without asking again for routine steps. Pause only dependent work
when a product decision, destructive data change, new spending, or missing access
requires the user. Do not invent a deployment for a repository that has none.

## Discover the repository's operating contract

Read applicable `AGENTS.md` files and inspect the actual repository, not assumptions
from a previous run. Resolve its remote, default branch, local changes, package
manager and lockfiles, update bot configuration, supported runtimes, verification
commands, CI, merge rules, and release/deployment mechanism. Follow linked infra
configuration when deployment is owned by another repository. Prefer existing
connected tools or authenticated CLIs; never copy credentials into the skill.

Preserve unfinished work. Fetch before choosing a base; use a clean, isolated
checkout when needed, following the environment's worktree tooling. Do not reset
the user's branch or mix unrelated edits into maintenance commits.

Briefly state the discovered checks and release path. Snapshot the eligible update
PRs at the start of the run, applying the user's filter. Reuse existing PRs rather
than duplicating them. When no bot manages updates, inspect the manifest and
registry/release sources and propose coherent update batches using the project's
package manager. Identify baseline failures before attributing them to an update.

## Fix and verify updates

Process updates sequentially, grouping coupled packages when compatibility requires
it. Patch, minor, and major dependency updates are eligible when they preserve the
project's intended behavior. Read upstream release/migration guidance for material
changes and implement necessary compatibility fixes. Preserve repository policies
such as release-age limits, supported platforms, and lockfile consistency.

Run the checks appropriate to the affected behavior: build/type/lint checks,
existing relevant tests, and an application-level smoke test where applicable.
Use disposable databases or services for tests that write data. Establish whether
previews share production data before exercising mutations. A successful build or
health endpoint alone does not establish authentication or database correctness.
If necessary verification is absent, add a focused regression or integration check
that exercises the behavior the update could break.

Push only the maintenance changes. Wait for the intended CI workflows on the exact
current PR head, including preview verification where used. A green check from an
older head or an older deployed image does not qualify. Discover which jobs are
mandatory and which are conditional; absent mandatory checks, skipped mandatory
jobs, cancellations, and pending runs are not successes. If bot-token pushes do
not trigger CI, use the repository's supported dispatch or credential mechanism
and verify the resulting run; do not infer success from the push.

Repair recoverable failures and rerun the affected checks. After two unsuccessful
repair cycles for the same cause, defer that update with evidence and continue
independent candidates. Use bounded waits based on the repository's workflow
timeouts; do not repeatedly rerun unchanged failures or bypass checks to finish.

## Merge and finish the release

Immediately before merging, re-read the PR head and check results. Merge only the
verified head, using the repository's permitted merge method and a head-SHA
precondition where supported. If another change advances the head, reverify it.
Do not weaken branch rules or self-approve to bypass a required review.

After each merge, follow [the release verification procedure](references/release.md).
Finish any related image/version PR in the deployment repository only after
checking that it changes the intended application's verified version. Confirm the
running version and application behavior before processing the next update that
depends on it. If the repository only publishes a library or artifact, verify that
publication instead. If it has no release process, report deployment as not
applicable.

A failed production rollout stops further merges for that target. Diagnose it,
restore the previous application version when compatible with the data/schema,
and verify recovery. Never automatically reverse data migrations or destroy data.
Run the cleanup checks even when repair or deployment fails.

## Verify cleanup and report

Follow [the resource cleanup procedure](references/cleanup.md) for the discovered
platform. This includes checking whether obsolete pods and Services have actually
been removed, not just whether the corresponding PR is closed. Verify temporary
test processes, containers, and CI workers created by the run are finished too.

Report merged and deployed versions with PR/run links, what verification passed,
deferred updates and reasons, and cleanup results. Separate verified cleanup from
resources still terminating, active resources retained for a reason, and checks
blocked by missing access. Do not call the run complete while a required deployment
or cleanup check is unresolved; identify the remaining work explicitly. Do not
save run notes, repo profiles, or new persistent instructions unless requested.
