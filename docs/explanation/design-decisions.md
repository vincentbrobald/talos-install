# Design decisions

> Explanation · [Documentation](../../README.md#documentation)

The choices deploy-talos.py is built on, what else was considered, and when
to look at them again. A platform built on the clusters (its GitOps layout,
teams, Crossplane) records its own decisions in its own repository.

## The cluster

### Talos Linux

**Decision.** Nodes run Talos Linux.
**Why.** An immutable OS managed only through an API: no SSH, no package
drift, A/B installs with rollback, upgrades as one operation per node.
**Alternatives.** A general-purpose distribution with kubeadm or k3s: more to
patch and harden, upgrades are OS plus Kubernetes plus tooling.

### VMs on one libvirt host

**Decision.** Every node is a KVM VM on this host, created through libvirt.
**Why.** Real Talos nodes (real kernel, disks, NICs, reboots) on one machine,
rebuilt in minutes; the same code makes throwaway test clusters.
**Alternatives.** Containers (kind, Talos in Docker): no real upgrades,
reboots or block storage; a hypervisor platform (Proxmox, ...): another
system to run for one host.
**Revisit if** the lab spans several hosts.

### One Python script, not a provisioning stack

**Decision.** A single script (Python standard library, PyYAML, Jinja2)
drives libvirt, talosctl, kubectl and helm, from one YAML file.
**Why.** No toolchain to install, and the orchestration the lab needs (health
gates between nodes, rollback, VIP handover, adoption of Helm releases by
Argo CD) lives in one readable place.
**Alternatives.** Terraform with the Talos and libvirt providers: state to
keep, no gates between nodes. Cluster API: needs a management cluster. Omni:
Business Source License, and it would own the machine configs (it is used
read-only instead, below).
**Revisit if** the script's size outgrows one file's readability.

### The cluster file as the source of truth

**Decision.** Every command makes the cluster match one YAML file; unknown
keys are rejected; the file holds no credential, only file names.
**Why.** One place to read a cluster's shape, safe to commit, and typos fail
instead of being ignored. See [Architecture](architecture.md).

### Configs delivered as cloud-init ISOs

**Decision.** Each node boots with its machine config on a small ISO
(nocloud user-data).
**Why.** Nodes come up fully configured: no maintenance-mode
`apply-config` step to race against.
**Alternatives.** Booting into maintenance mode and pushing configs over the
network: an extra, timing-sensitive step per node.

### Image Factory images per extension set

**Decision.** The node image and installer come from the Image Factory for the
configured extensions; a different list is a different, cached image.
**Why.** Extensions (guest agent, iSCSI tools) are part of the OS image, and
upgrades keep them because configs name the matching installer.

### Tools downloaded and verified, not installed

**Decision.** `talosctl`, `kubectl`, `helm`, `kubelogin`, `omnictl` are
downloaded with checksum verification into a per-Talos-version cache.
**Why.** Versions match the cluster exactly, several clusters can coexist,
nothing is installed system-wide.

## Networks

### Private by default, LAN mode as an option

**Decision.** A cluster gets its own libvirt NAT network; with a `lan`
section, nodes get a second NIC on a host bridge for the API VIP and
LoadBalancer addresses, while cluster traffic stays internal.
**Why.** Test clusters need nothing from the LAN; LAN clusters expose only
what is meant to be reached, and node services stay firewalled to the
internal network. See [LAN mode](lan-mode.md).

### Cilium in LAN mode, flannel otherwise

**Decision.** LAN mode replaces flannel and kube-proxy with Cilium: Gateway
API, LoadBalancer IP pools and L2 announcements in one component.
**Alternatives.** MetalLB plus an ingress controller: two more components.
Cilium everywhere: unnecessary for private test clusters.

### One shared ingress gateway

**Decision.** One Gateway, `ingress/ingress`, takes one LoadBalancer address;
host names are listeners on it, and labelled namespaces may add their own
through ListenerSets.
**Why.** One DNS wildcard and one forward from an outside load balancer serve
every application; teams get host names without a change to the Gateway.
**Cost.** Cilium can't mix TLS passthrough and termination on one port: with
`certManager`, only termination.

### A fixed address plan

**Decision.** Addresses follow role and index; in LAN mode workers count down
from the end of the range.
**Why.** Rebuilt clusters get the same addresses, and scaling workers only
moves the pool's upper bound, so service addresses never change.
See [Address plan](../reference/address-plan.md).

## Day 2

### Our own upgrade rollouts

**Decision.** `upgrade` and `upgrade-k8s` roll out one node at a time with a
health gate after each, Talos with automatic rollback, Kubernetes phased
component by component with the API VIP moved away first.
**Why.** Stock `talosctl upgrade-k8s` took the API down for 40 s and 13 s
through the VIP; the script's rollout lost no request. See [Upgrades](upgrades.md).
**Alternatives.** `talosctl` directly: no gates, no rollback across nodes, the
outages above. tuppr alone: optional instead (next entry).

### tuppr as an option, behind the script's gates

**Decision.** With a `tuppr` section, the cluster runs the rollouts itself
from resources in Git, but `upgrade` and `upgrade-k8s` still check versions,
health and compatibility before pushing the new version.
**Why.** Upgrades become commits like everything else without losing the
pre-upgrade gates.

### Add-ons in Git, rendered by the script

**Decision.** With `argocd.addons`, the script renders the add-ons into the
repository and Argo CD syncs them; the script owns `addons/generated/` and
`generated/`, and writes `generated/CHECKSUMS`.
**Why.** The repository holds the cluster's whole Argo CD view, while the
cluster file stays the single source for what the script knows.
**Alternatives.** Helm releases installed by the script (the default without
`addons`): no review, no drift correction. `addons.content: reuse` makes Git
the source instead. See [GitOps and add-ons](gitops.md).

### Secrets in Git with SOPS, Git wins

**Decision.** In SOPS mode the add-ons' Secrets are encrypted for the
cluster's age key and yours; a credential already in Git is used, never
replaced.
**Why.** A rebuilt cluster or Keycloak gets the same secrets back.
**Cost.** Argo CD's repo server runs KSOPS, a plugin named in the repository.

### Credentials only from files

**Decision.** The cluster file names credential files; values reach the
cluster through stdin, never in Helm values or files on disk.
See [Security](security.md#credentials).

### Keycloak: bootstrap clients by the script, the rest optionally by Crossplane

**Decision.** The script creates the realm, groups and the Kubernetes and Argo
CD clients through Keycloak's API; with `oidc.crossplane`, it writes the
Headlamp and Grafana clients as Crossplane objects instead.
**Why.** The first two are needed before Crossplane exists in the cluster;
the others can be reconciled like the rest of the platform.

### Headlamp with the user's own token

**Decision.** Headlamp's service account gets no rights; it passes the user's
OIDC token to the API server.
**Why.** Each person sees exactly what RBAC grants them.

### Longhorn on dedicated storage nodes

**Decision.** Longhorn's replicas live on storage nodes with a data disk and
no LAN NIC, tainted for Longhorn only.
**Why.** Rebuilds and workloads don't compete; replication stays on the
internal network. See [Storage](storage.md).

### etcd backups, write-only and encrypted

**Decision.** talos-backup uploads age-encrypted snapshots with a credential
that can only write.
**Why.** A stolen cluster credential can't read or destroy backups.
**Note.** The image is a build of talos-backup's main branch: the last
release predates compression, several recipients and a path-style fix.

### Images through a mirror

**Decision.** With a `registry` section, every node pulls through a mirror
that keeps each upstream under its own namespace (`overridePath`), falling
back to the upstream.

### Omni, imported locked

**Decision.** `omni` imports a cluster into Omni locked: Omni shows it but
changes nothing.
**Why.** The console without handing the machine configs to Omni, which
would compete with this script and the GitOps repository.

## Known limits accepted

- metrics-server and Prometheus don't verify the kubelets' self-signed
  serving certificates (fix: serving certificates from the cluster CA).
- Single-host lab: the host is a single point of failure for every cluster.
- x86_64 only.
