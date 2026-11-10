# Verify the released version

Use the existing platform's source of truth: GitHub Actions, a package registry,
Argo CD, Kubernetes, a hosting provider, or a documented release command. Discover
names and identifiers from the selected repository; examples below are templates,
not defaults for every project.

## Tie checks to the version being released

Track the verified PR head, its merge commit on the default branch, the successful
build/release run for that commit, and the resulting artifact or image tag/digest.
Capture the previous deployed version before changing deployment state.

On GitHub, inspect the PR and runs with explicit repository arguments:

```sh
gh pr view "$pr" --repo "$repo" --json headRefOid,baseRefName,statusCheckRollup,mergeStateStatus
gh run list --repo "$repo" --commit "$commit" --json databaseId,workflowName,status,conclusion,headSha
```

Use `gh pr merge --match-head-commit` or an equivalent API precondition for the
verified head. Choose squash, merge, or rebase according to the repository's
configuration. A successful PR build does not replace the default-branch build
when deployment depends on that later build.

If CI opens a deployment-repository PR, verify its source commit, image/version,
changed paths, and required checks. Merge only the intended application's change.
If concurrent deployments supersede the run, determine what is now desired and
running; never deploy an older image just to match the maintenance run's state.

## Confirm the rollout, then the application

For Kubernetes, use the discovered context and namespace on every command:

```sh
kubectl --context "$context" -n "$namespace" rollout status "deployment/$deployment" --timeout=300s
kubectl --context "$context" -n "$namespace" get deployment "$deployment" -o json
kubectl --context "$context" -n "$namespace" get pods -l "$app_selector" -o json
```

Compare the desired image with the expected artifact, observed deployment
generation, ready/updated replicas, and running pod image IDs. A rollout reporting
success while still serving an older image is not sufficient. If GitOps is used,
also verify the owning Application's desired revision, sync result, and health.
Keep normal configuration changes in Git; live edits that the controller will
revert are not a deployment fix. Inspect selected fields instead of dumping
rendered values, Secrets, or credential-bearing manifests into output.

Use a version endpoint, build identifier, response header, or platform release
record to verify the public endpoint serves the intended version. Check the key
user paths affected by the update, plus relevant authentication and database
behavior. On shared or production databases, prefer read-only checks; use a
documented test tenant/account only when those writes are already authorized.

For libraries or other non-service repositories, check that the expected version
and artifacts were published successfully. Do not manufacture an HTTP deployment
step or treat publication and runtime deployment as the same event.

## Recovery and stopping conditions

Respect existing CI and rollout deadlines. If no documented deadline exists, use
a bounded observation window and report it. Poll in short intervals and keep the
user informed rather than blocking silently through long waits.

On failure, stop further merges for that target and inspect the failing version.
Revert the application release through its usual ownership mechanism when the
previous version remains schema-compatible. Confirm recovery and perform cleanup.
If recovery needs destructive migration, missing credentials, or a product
decision, report the exact blocker and retain the evidence needed to resume.
