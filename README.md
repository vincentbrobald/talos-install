# deploy-talos.py

Deploy Talos Linux Kubernetes clusters on the local qemu/kvm host via libvirt,
from a YAML description.

- One command builds a cluster: network, VMs, bootstrap, health check, kubeconfig.
- Clusters are described by a small YAML file. `template` generates a fully
  commented one from a preset.
- Optional **LAN mode** puts the Kubernetes API and Gateways/LoadBalancer services
  on an existing host bridge, using Cilium.
- **Workers can be scaled** out or in later. Removed workers are drained first,
  so workloads move without downtime.
- **Rolling Talos upgrades**: one node at a time, with health gates between
  nodes and automatic rollback on failure.
- **Kubernetes upgrades** behind pre- and post-upgrade gates: version path,
  health, removed APIs, add-on compatibility.
- Optional **OIDC login** (e.g. Keycloak) for `kubectl` and Argo CD, with group
  based admin rights. The script can set up the Keycloak realm, groups and
  clients itself.
- Optional **GitOps**: Argo CD syncs a Git repository from the first minute,
  and the add-ons themselves can live in that repository.
- `talosctl`, `kubectl` and `helm` are downloaded with checksum verification
  into a cache directory. Nothing is installed system-wide.

```sh
./deploy-talos.py template --preset minimal -o dev.yaml
./deploy-talos.py create -f dev.yaml
```

New here? Start with the tutorial [Getting started](docs/tutorials/getting-started.md).

## Documentation

The documentation follows [Diátaxis](https://diataxis.fr/): tutorials to
learn, how-to guides for tasks, reference to look things up, explanation to
understand.

**Tutorials**
- [Getting started](docs/tutorials/getting-started.md): a first cluster, then one on the LAN with GitOps and Keycloak login
- [Change a running cluster](docs/tutorials/change-a-running-cluster.md): add and remove a worker, rehearse a failed upgrade, upgrade, on a throwaway cluster

**How-to guides**

| Task | Guide |
|---|---|
| Make clusters survive a host reboot | [Prepare the host](docs/how-to/prepare-the-host.md) |
| More or fewer workers, bigger disks | [Scale workers](docs/how-to/scale-workers.md) |
| New Talos release | [Upgrade Talos](docs/how-to/upgrade-talos.md) |
| New Kubernetes release | [Upgrade Kubernetes](docs/how-to/upgrade-kubernetes.md) |
| Let the cluster upgrade itself from Git | [Hand upgrades to tuppr](docs/how-to/hand-upgrades-to-tuppr.md) |
| Deploy from a Git repository, rotate its credentials | [Set up GitOps](docs/how-to/set-up-gitops.md) |
| Keep the add-ons in Git | [Manage the add-ons in Git](docs/how-to/manage-addons-in-git.md) |
| Keep Secrets in Git (SOPS) | [Keep Secrets in Git](docs/how-to/keep-secrets-in-git.md) |
| Log in with Keycloak | [Add Keycloak login](docs/how-to/add-keycloak-login.md) |
| HTTPS certificates and the web console | [Serve HTTPS and Headlamp](docs/how-to/serve-https-and-headlamp.md) |
| Publish an application | [Expose an application](docs/how-to/expose-an-application.md) |
| Persistent volumes | [Add Longhorn storage](docs/how-to/add-longhorn-storage.md) |
| `kubectl top`, Prometheus, Grafana | [Add monitoring](docs/how-to/add-monitoring.md) |
| etcd backups and restore | [Back up and restore etcd](docs/how-to/back-up-and-restore-etcd.md) |
| Pull images through a mirror | [Use a registry mirror](docs/how-to/use-a-registry-mirror.md) |
| Names in the LAN's DNS | [Register DNS records](docs/how-to/register-dns-records.md) |
| Show the cluster in Omni | [Import into Omni](docs/how-to/import-into-omni.md) |
| Something failed | [Troubleshoot](docs/how-to/troubleshoot.md) |

**Reference**
- [Commands](docs/reference/commands.md): every command, its options and steps, and everyday ones
- [Cluster file](docs/reference/cluster-file.md): every key, its default and constraints
- [Address plan](docs/reference/address-plan.md): node, VIP and pool addresses
- [Ingress gateway](docs/reference/ingress-gateway.md): its listeners
- [Repository files](docs/reference/repository-files.md): what is written to the Git repository
- [Files and credentials](docs/reference/files-and-credentials.md): what is read and written on the host and in the cluster
- [Requirements](docs/reference/requirements.md): host, tools, network access

**Explanation**
- [Design decisions](docs/explanation/design-decisions.md): the choices, the alternatives considered, when to revisit them
- [Architecture](docs/explanation/architecture.md): from cluster file to cluster, the address plan, the health gate
- [LAN mode](docs/explanation/lan-mode.md): two networks, Cilium, the firewall, the ingress gateway
- [GitOps and add-ons](docs/explanation/gitops.md): Argo CD, the add-ons in Git, SOPS
- [Upgrades](docs/explanation/upgrades.md): rollouts, gates, rollback, VIP handover, tuppr
- [Authentication](docs/explanation/authentication.md): OIDC, audiences, rights
- [HTTPS and Headlamp](docs/explanation/https-and-headlamp.md): ACME on the gateway, the user's own rights
- [Storage](docs/explanation/storage.md): Longhorn on dedicated nodes
- [Metrics and monitoring](docs/explanation/monitoring.md): what is collected and why
- [Security](docs/explanation/security.md): what is protected, and the limits

`deploy-talos.py --help` and `deploy-talos.py <command> --help` show the
commands on the command line.

## License

MIT (LICENSE), © 2026 Vincent Brobald.
