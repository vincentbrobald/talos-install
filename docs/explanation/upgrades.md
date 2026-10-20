# Upgrades

> Explanation · [Documentation](../../README.md#documentation)

How Talos and Kubernetes upgrades are rolled out, what protects the cluster,
and what was measured. To run one: [Upgrade Talos](../how-to/upgrade-talos.md),
[Upgrade Kubernetes](../how-to/upgrade-kubernetes.md),
[Hand upgrades to tuppr](../how-to/hand-upgrades-to-tuppr.md).

## Two separate upgrades

Talos is the operating system; Kubernetes runs on it. `upgrade` replaces the
OS on each node (reboot included). `upgrade-k8s` changes the Kubernetes
components (API server, controller-manager, scheduler, kubelet, kube-proxy,
and the bootstrap manifests Talos manages: CoreDNS, flannel, RBAC) without
rebooting or draining. Keeping them apart keeps each one small and
reversible where it can be.

## Talos: one node at a time

Order: control planes first, then workers, strictly one node at a time, so
never more than one control plane and one worker are down. For each node:

1. **Drain,** respecting PodDisruptionBudgets. A blocked drain stops the
   rollout *before* the node changes.
2. **Upgrade** with the Image Factory installer of the cluster's extensions.
   Talos installs the new release next to the current one (A/B) and reboots
   into it.
3. **Verify:** the node reports the new version and is Ready, then is
   uncordoned.
4. **Health gate** ([what it checks](architecture.md#the-health-gate)) within
   `--health-timeout` before the next node.

**Rollback.** Because Talos keeps the previous installation, a failure is
recoverable: the failed node is rolled back (`talosctl rollback`) if it
already runs the new release, or only uncordoned if it never changed. With
`--on-failure rollback-all` (default) the nodes upgraded earlier in the run
are rolled back too, in reverse order, each followed by the gate, so the
cluster returns to one version. With `rollback-node` they stay on the new
release, a mixed state Talos supports during upgrades. If the cluster isn't
healthy after a rollback, the remaining rollbacks are skipped rather than take
more nodes down. Running `upgrade` again continues with the nodes not yet on
`talos.version`.

**Rules.** Talos supports one minor release at a time (1.13.x to 1.14.y), so
larger jumps and downgrades are refused. With a single control plane the API
is down while it reboots: three control planes keep it available.

**The install image in the config.** `talosctl upgrade --image` installs the
new image but leaves the running config naming the old one; anything
upgrading from the config (`talosctl upgrade` without `--image`, tuppr) would
reinstall the old schematic without newer extensions. The script therefore
also updates the running configs and the stored ones (used for new workers).

**Measured** on a 3+2 cluster, 1.14.1 to 1.14.2, with a workload of 4
replicas (PodDisruptionBudget minimum 3), sampled every 2 s: about 4 minutes
in total, at most one control plane and one worker unavailable at any time,
the API reachable and 4 replicas ready in every sample.

## Kubernetes: gated, phased, no rollback

**Gates before.**
1. Version path: every node on `talos.version`; the target within the Talos
   release's window (the six minor releases up to its default, e.g. 1.32–1.37
   for Talos 1.14), at most one minor ahead, no minor downgrade.
2. Cluster health: the health gate.
3. Removed APIs: versions the target removes that clients requested since the
   API server started (`apiserver_requested_deprecated_apis`).
4. Add-on compatibility: the `kubeVersion` range of the charts the script
   installed (Cilium, Argo CD) includes the target.

Gates 3 and 4 can be overridden with `--force`; 1 and 2 can't.

**Phases,** one node at a time, each step followed by the health gate:
1. Control plane, component by component: kube-apiserver everywhere, then
   kube-controller-manager, then kube-scheduler. Kubernetes' version-skew
   policy demands it: a controller-manager or scheduler may not be newer than
   an API server it talks to (a 1.37 scheduler next to 1.36 API servers never
   becomes ready).
2. Kubelets, control planes first.
3. kube-proxy and the bootstrap manifests, via `talosctl upgrade-k8s`.

Each step patches only that node's config, and nodes already at the target are
skipped, so an interrupted run continues where it stopped.

**VIP handover.** Talos's API VIP isn't tied to the local API server's health.
Restarting the API server (or the kubelet, which recreates the static pods)
on the VIP holder would take the address down with it. So before such a step
the script removes that node's VIP config, another control plane takes the
address (about 1 s, no failed requests), the config is restored afterwards,
and the holder is always done last. With one control plane there is nowhere
to move it.

**Measured** on 3 control planes, 1.36.5 to 1.37.1, an authenticated API
request through the VIP every 0.5 s:

| Rollout | Outages |
|---|---|
| stock `talosctl upgrade-k8s` | 40 s and 13 s |
| phased, without handover | 38.8 s and 10.6 s |
| the script's, with handover | none (1004/1004 over 8.5 minutes, 2 VIP moves) |

In-cluster clients (kubelets, Cilium) use KubePrism, Talos' local load
balancer over all API servers, and were never affected; workloads kept running.

**Gates after.** Component versions match the target; the health gate; with
Argo CD, the root Application Synced and Healthy, which catches applications
broken by the new version. The stored configs then get the new images, so
workers added later join with the new kubelet.

**No rollback.** Kubernetes doesn't support minor downgrades and Talos keeps
no A/B copy of it. A failure stops the run with each component's version;
fixing the cause and running again continues.

**Limits.** Add-ons aren't upgraded: Cilium, the Gateway API CRDs and Argo CD
must support the target first, and chart `kubeVersion` ranges are often broad
(Cilium declares `>= 1.21`), so check the projects' own matrices. The
removed-API metric only covers requests since each API server started:
manifests in Git using removed APIs show up after the upgrade, in the Argo CD
gate.

## tuppr: upgrades from inside the cluster

With a `tuppr` section, the [tuppr](https://github.com/home-operations/tuppr)
controller runs both rollouts from resources in Git (`TalosUpgrade talos`,
`KubernetesUpgrade kubernetes` in `generated/tuppr/`). The cluster then
upgrades itself from a commit, like every other change, and the host only
has to push.

The script keeps its gates in front: `upgrade` and `upgrade-k8s` check
versions, health and compatibility as above, then push the new version and
follow tuppr until it completes. Before each node, tuppr itself checks that
all nodes are Ready and, with Longhorn, that every attached volume is fully
replicated. tuppr upgrades from the install image in each node's running
config with the version swapped, which is why the script sets that image to
the cluster's current schematic first.

tuppr talks to the Talos API from a pod: the control planes grant `os:admin`
to namespace `system-upgrade` (`KubeTalosAPIAccessConfig`) and the firewall
admits the pod network ([LAN mode](lan-mode.md#firewalled-node-services)).
On a running cluster both are applied without a reboot, first in try mode
(Talos reverts by itself after two minutes if this host loses the node), then
for good.

Editing the version in Git directly also starts a rollout, but the next run of
the script resets it to the cluster file's version: the file stays the source.
