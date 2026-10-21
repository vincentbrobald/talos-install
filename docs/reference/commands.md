# Commands

> Reference · [Documentation](../../README.md#documentation)

```
deploy-talos.py template [--preset P] [--name NAME] [--lan-bridge B] [--lan-range R] [--domain D]
                         [--ca-file F] [--secrets-dir DIR] [-o FILE] [--force]
deploy-talos.py plan     -f FILE [--no-checks]
deploy-talos.py create   -f FILE
deploy-talos.py argocd   -f FILE
deploy-talos.py scale    -f FILE [--dry-run] [--drain-timeout D] [-y]
deploy-talos.py upgrade  -f FILE [--dry-run] [--drain-timeout D] [--health-timeout D]
                         [--on-failure rollback-all|rollback-node] [--simulate-failure NODE] [-y]
deploy-talos.py upgrade-k8s -f FILE [--dry-run] [--health-timeout D] [--force] [-y]
deploy-talos.py oidc     -f FILE [-y]
deploy-talos.py headlamp -f FILE [-y]
deploy-talos.py longhorn -f FILE [--drain-timeout D] [--health-timeout D] [-y]
deploy-talos.py node-config -f FILE
deploy-talos.py omni -f FILE [--dry-run | --abort]
deploy-talos.py dns-records -f FILE --domain DOMAIN [--format json|text]
deploy-talos.py destroy  -f FILE [-y]
```

`deploy-talos.py --help` and `deploy-talos.py <command> --help` show the same
information on the command line.

## Everyday commands

| Command | Does |
|---|---|
| `kubectl get nodes; talosctl -n <cp-ip> health` | is all well? |
| `virsh shutdown <name>-cp-1 …`, `virsh start <name>-cp-1 …` | stop or start the nodes; the cluster resumes on boot |
| `deploy-talos.py destroy -f FILE` | remove the VMs and the network; the cluster directory stays |

## template

Writes a fully commented cluster file. It goes to stdout, or to `-o FILE`. An
existing file is only overwritten with `--force`.

| Option | Description |
|---|---|
| `--preset` | Starting point, default `minimal` (see below) |
| `--secrets-dir` | Set `paths.secretsDir` in the file (directory with credential files, kept out of git) |
| `--lan-bridge` | Host bridge for LAN mode (default placeholder `br0`) |
| `--lan-range` | Unused LAN addresses for LAN mode, e.g. `192.0.2.200-229` (default placeholder `192.0.2.200-229`, a documentation range) |
| `--domain` | DNS domain for the example host names and OIDC issuer (default placeholder `example.com`) |
| `--ca-file` | CA certificate for the `oidc.caFile` example |
| `--name` | Cluster name to put in the file. Defaults to the preset's name: `dev`, `ha`, `lan` or `lan-ha` |
| `-o`, `--output` | Write to this file instead of stdout |
| `--force` | Overwrite `--output` if it exists |

| Preset | Layout |
|---|---|
| `minimal` | 1 control plane + 2 workers, internal NAT network only (flannel) |
| `ha` | 3 control planes behind an internal API VIP + 2 workers, internal only |
| `lan` | 1 control plane + 2 workers, exposed on a host bridge (Cilium, Gateway API) |
| `lan-ha` | 3 control planes + 2 workers, API VIP and Gateways on a host bridge (Cilium) |

The presets differ only in `controlPlanes.count` and whether the `lan` section is
active. Any preset can be edited into any other layout.

The template contains placeholders for site values (bridge `br0`, LAN range
`192.0.2.200-229`, domain `example.com`). `plan` refuses them until they're
replaced, or pass your values directly:

```sh
./deploy-talos.py template --preset lan-ha --name lab --lan-bridge bridge0 \
    --lan-range 192.0.2.200-229 --domain example.org --secrets-dir ~/secrets -o lab.yaml
```

## plan

Validates the file and prints the resolved settings, resource totals and the
per-node address plan. It then runs the same read-only host checks `create`
starts with:
- the required tools are present and `/dev/kvm` exists;
- no domain or disk with the cluster's names already exists;
- private network, when the script creates it: the libvirt network name and
  `network.bridgeName` are free, and `network.prefix` isn't already routed on
  the host;
- private network on an existing bridge: `network.existingBridge` is a bridge,
  the host has a route to the prefix through it, and no node address answers ping;
- in LAN mode, the bridge exists, `lan.range` lies inside the bridge's subnet,
  and **no address in `lan.range` answers ping**;
- with an `argocd` section: the credential files exist and aren't empty, and an SSH key has no passphrase. Then `git ls-remote` runs from the
  host with exactly those credentials, and the revision must exist. Wrong
  credentials therefore fail here, before any VM is built.

`--no-checks` only validates and prints. `plan` never changes anything.

## create

Builds the cluster and waits until it is healthy:
1. Runs the host checks.
2. Downloads `talosctl`, the Talos image, `kubectl`, and `helm` (LAN mode or Argo CD).
3. Generates secrets and per-node machine configs.
4. Creates the libvirt network (unless `network.existingBridge` is set) and the VMs,
   both set to autostart, so the cluster comes back up when the host reboots.
5. Bootstraps etcd. In LAN mode it then installs Cilium and the LoadBalancer pool.
6. Runs `talosctl health` and checks that nodes are Ready and CoreDNS is up.
7. With an `argocd` section, installs Argo CD, connects the repository, creates
   the root Application and waits until it is Synced and Healthy (see
   [GitOps with Argo CD](../explanation/gitops.md)).
8. Prints the nodes and the commands to use the cluster (and Argo CD).

`create` refuses to run if any of the cluster's VMs, disks or network already
exist. Secrets in an existing cluster directory are reused, so destroying and
re-creating a cluster keeps its PKI.

## argocd

Installs or updates Argo CD on a cluster that `create` built from the same file,
using its `argocd` section. It runs the repository check, upgrades the Helm
release, replaces the repository credentials, re-applies the root Application
and waits for it to sync. Use it to:
- add GitOps to a cluster created without an `argocd` section;
- rotate a password, token or deploy key;
- switch auth method, repository, revision or path.

Credentials from a previous method are removed from the cluster. A failed host
check stops before anything in the cluster changes.

With `argocd.addons.enabled`, it also renders the add-on definitions, pushes
them, and syncs them through Argo CD (see [Add-ons in Git](../explanation/gitops.md#add-ons-in-git)).
On a cluster whose add-ons were installed with Helm, this is the migration:
Argo CD takes over the existing releases.

## scale

Adds or removes workers so the cluster matches `workers.count` in the file. Edit
the count, run `scale --dry-run` to see and check the changes, then `scale`.
Details in [Scaling workers](../how-to/scale-workers.md).

| Option | Description |
|---|---|
| `--dry-run` | Show the workers to add/remove and the pool change, run the checks, change nothing |
| `--drain-timeout` | How long each worker may take to drain, e.g. `90s`, `15m` (default `10m`) |
| `-y`, `--yes` | Don't ask before removing workers; required without a terminal |

## upgrade

Upgrades Talos on every node to `talos.version`, one node at a time, with a
health gate after each node and rollback on failure. Details in
[Upgrading Talos](../how-to/upgrade-talos.md).

| Option | Description |
|---|---|
| `--dry-run` | Show the per-node plan and check cluster health, change nothing |
| `--drain-timeout` | How long each node may take to drain (default `10m`) |
| `--health-timeout` | How long the cluster may take to be healthy after each node (default `10m`) |
| `--on-failure` | `rollback-all` (default): roll back the failed node and every node upgraded in this run. `rollback-node`: only the failed node |
| `--simulate-failure NODE` | Treat NODE's post-upgrade check as failed, to rehearse the rollback |
| `-y`, `--yes` | Don't ask for confirmation; required without a terminal |

## upgrade-k8s

Upgrades Kubernetes to `talos.kubernetesVersion` (`null`: the default of the
Talos release) behind pre- and post-upgrade gates. Details in
[Upgrading Kubernetes](../how-to/upgrade-kubernetes.md).

| Option | Description |
|---|---|
| `--dry-run` | Run the pre-upgrade gates and show Talos' upgrade plan, change nothing |
| `--health-timeout` | How long the post-upgrade gates may take (default `10m`) |
| `--force` | Proceed despite removed-API or add-on findings; health gates still apply |
| `-y`, `--yes` | Don't ask for confirmation; required without a terminal |

## oidc

Adds or updates OIDC authentication on an existing cluster from the file's
`oidc` section. See
[Authentication with Keycloak (OIDC)](../explanation/authentication.md).
1. Sets up Keycloak, when the script manages it.
2. Updates the API servers one control plane at a time. Each update waits until
   the API server has really restarted with the new configuration, then runs the
   health gate.
3. Binds the admin groups to `cluster-admin` and writes `kubeconfig-oidc`.
4. With an `argocd` section, re-applies Argo CD with single sign-on.

Running it again only changes API servers whose configuration differs from the
file. `-y` skips the confirmation.

## headlamp

Adds or updates the Headlamp web console on an existing cluster from the
file's `headlamp` section. See
[HTTPS and the Headlamp web console](../explanation/https-and-headlamp.md).
1. With an `oidc` section: brings the API servers' accepted token audiences in
   line with the file (adds Headlamp's client), one control plane at a time
   like `oidc`, after confirmation (`-y` skips it).
2. With a `certManager` section: installs cert-manager and the ACME issuer.
3. Installs Headlamp, its Keycloak client and, with `headlamp.hostname`, the
   certificate, the HTTPS listener on the gateway and the routes.

Running it again only changes what differs from the file.

## longhorn

Adds or updates Longhorn storage on an existing cluster from the file's
`longhorn` section. See [Longhorn storage](../explanation/storage.md).
1. Refuses if a node doesn't run `talos.version` (run `upgrade` first), or if
   the cluster has more storage nodes than `longhorn.nodes.count` (storage
   nodes are never removed).
2. Nodes lacking the `iscsi-tools` / `util-linux-tools` extensions are
   reinstalled with them: same Talos version, new installer image, using the
   [`upgrade`](../how-to/upgrade-talos.md) procedure (one node at a time, drain, health
   gate, rollback of the failed node). It asks first; `-y` skips the question.
   `--drain-timeout` and `--health-timeout` are as for `upgrade`.
3. In LAN mode, excludes storage nodes from the ARP announcements.
4. Creates the missing storage nodes `<name>-st-N` and waits until they are Ready.
5. Installs or updates the Longhorn chart and waits for the CSI driver and the
   storage nodes' disks.

Running it again only changes what differs from the file.

## node-config

Applies the settings that take effect without a reboot to the running nodes
of a cluster created from FILE:
- the `registry` mirrors and CA;
- the Talos API access and firewall rules that tuppr and talos-backup need;
- with `omni.caFile`, Omni's CA (`TrustedRootsConfig` `omni-ca`).

Only nodes whose documents differ are patched, each first in try mode (Talos
reverts the change by itself after two minutes if this host loses the node's
Talos API), then for good. A document that differs is replaced, not merged.
`argocd` runs the same step.

## omni

Imports a cluster created from FILE into [Omni](https://docs.siderolabs.com/omni)
(Sidero Labs' console and API for Talos clusters), using its `omni` section:
1. With `omni.caFile`, the nodes first trust Omni's CA (as `node-config` does):
   they join Omni's SideroLink API over HTTPS.
2. Downloads `omnictl` of `omni.omnictlVersion` (checksum-verified) and runs
   `omnictl cluster import --dry-run` on every node, then the import: Omni saves
   a backup of the nodes' configs (`<name>-backup-<time>.zip` in the cluster
   directory: it holds the cluster's secrets), connects each node over
   SideroLink (no reboot), keeps the current configs as patches, and marks the
   cluster **locked**.

Locked: Omni changes nothing until `omnictl cluster unlock <name>`; this script,
the GitOps repository and tuppr keep managing the cluster. Unlocking hands the
machine configs and the Kubernetes endpoint to Omni. A cluster already in Omni
is only reported. `--dry-run` only checks; `--abort` aborts an import still
locked (the nodes keep Omni's documents until their backed-up configs are
applied again with `talosctl apply-config`).

## destroy

Removes the cluster's VMs, disks, config ISOs and libvirt network. A network is
only removed if this script created it for this cluster: networks are tagged
with libvirt metadata when created. An existing bridge is never touched. It asks for
confirmation unless `-y`/`--yes` is given; without a terminal, `--yes` is
required. VMs are matched by name (`<name>-cp-N`, `<name>-w-N`, `<name>-st-N`;
storage nodes' data disks go too). The cluster
directory is **kept**, because it holds the secrets. When the script manages
Keycloak, the cluster's Keycloak clients (Kubernetes, Argo CD, Headlamp,
Grafana: those it has) are removed too; the realm and
groups stay. With `argocd.addons`, the cluster's generated files are removed
from the repository. Delete it yourself when it
is no longer needed. Running `destroy` on a cluster that's already gone is
harmless.

## Exit status

`0` on success, `1` on any error (printed as `ERROR: ...`), `130` when interrupted.
