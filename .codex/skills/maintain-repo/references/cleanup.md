# Verify temporary-resource cleanup

Build an inventory for the selected repository from its workflows, deployment
manifests, preview controller, resource labels/owners, and live state. Record the
cluster context, namespaces, resource identities, lifecycle owner, and why each
temporary resource should remain or disappear. Keep the inventory in the current
run's context; do not create a persistent per-repo profile unless asked.

Check both resources created by this run and pre-existing obsolete resources owned
by the target repository. An open PR's preview is normally intentional. Low CPU,
old age, or lack of traffic alone does not establish that a resource is unused.

## Kubernetes previews

1. Query all currently open PRs, with pagination, and map them to preview
   Applications/namespaces using the repository's actual naming convention or
   labels. Do not assume all repositories use the same numeric namespace suffix.
2. After a PR merges or closes, allow its controller's documented reconciliation
   interval. Confirm the preview Application and workload controllers are gone,
   pods have disappeared, and preview Services/Ingresses are removed. Check the
   preview namespace too if its lifecycle is owned by the preview deployment.
3. Re-read current PR and desired deployment state immediately before removing
   anything. Check owner references, labels, and desired Git state; a reopened PR
   or another active run can make a formerly obsolete resource legitimate again.

For an identified preview namespace, useful read-only checks are:

```sh
kubectl --context "$context" -n "$preview_namespace" get pods,services,deployments,statefulsets,daemonsets,replicasets,jobs,cronjobs,ingresses
kubectl --context "$context" get namespace "$preview_namespace"
```

Inspect the relevant controller's Application/resource record separately. A
Service is a routing object, not a process: obsolete Services must be deleted, and
zero pods alone does not prove cleanup. Check for remaining controllers that can
recreate pods, including CronJobs and stuck deletion/finalizer states. Namespace
deletion must finish when namespace removal is expected.

With Argo CD ApplicationSets, inspect the preview generator, its open-PR filter,
requeue interval, Application finalizer, `preserveResourcesOnDeletion`, and relevant
pruning policy. Closing a PR is only the trigger; observe the actual deletion.
An empty list is proof only after a successful, correctly scoped API call. An API
timeout, forbidden response, wrong context, or failed pipeline is not evidence
that resources are gone. Use structured reads or individually checked commands
instead of hiding errors behind `grep` or `|| true`.

If cleanup is stuck, diagnose controller conditions, events, and finalizers.
Prefer fixing the repository's lifecycle configuration through GitOps. Delete an
individual obsolete ephemeral object only when repository ownership, absence of
an active consumer, and the intended lifecycle are established. Do not force
finalizers, delete PVCs/databases, or delete a namespace containing unclassified
resources. Record such cases as blockers needing the appropriate decision.

## CI workers and local test services

Check the repository's active/queued workflow runs before expecting runners to
disappear. Ephemeral runner pods should terminate after their jobs complete and
settle to the scale set's configured minimum. Listener/controller pods and
deliberately retained warm or persistent runners are legitimate resources.
Inspect runner ownership and configured capacity rather than deleting any pod
whose name contains "runner". If another run is active, identify it and report
runner shutdown verification as deferred, not passed.

Stop only temporary services/processes/containers created by this run. Use captured
process/container identities or explicit project labels; avoid process-name kills
and global prune/down commands. Verify their exit/removal and release of any
temporary listeners. Preserve user browser profiles and unrelated local services.

## Other platforms and completion

For Docker Compose, hosted previews, serverless revisions, or other environments,
use the platform's equivalent ownership and lifecycle records. Verify that obsolete
instances and routing resources are removed; mark Kubernetes-specific checks not
applicable when the repository does not use Kubernetes.

Bound observation using the platform's reconciliation/termination deadlines. When
none are documented, allow up to ten minutes and then report exact remaining
resources and conditions. Do not start an unsolicited recurring watcher or keep
retrying a broken controller indefinitely. Always perform cleanup inspection even
if an earlier verification or deployment fails, while preserving active previews
and the previous working production release.
