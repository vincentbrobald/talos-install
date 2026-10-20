# Cluster file

> Reference · [Documentation](../../README.md#documentation)

A YAML mapping. Only `name` is required. Every other key has the default shown
in the tables below. **Unknown keys are rejected**, so typos fail instead of
being silently ignored. `null` means "use the default / auto-detect". Relative
paths are resolved against the directory containing the cluster file.

Complete example (the `lan-ha` preset with comments removed):

```yaml
name: lan-ha
talos:
  version: v1.14.2
  kubernetesVersion: null
  extensions:
    - siderolabs/qemu-guest-agent
network:
  prefix: 10.44.0
  name: null
  bridgeName: null
  existingBridge: null
  gateway: null
  nameservers: null
controlPlanes:
  count: 3
  vcpus: 2
  memory: 4096
  diskSize: 20G
workers:
  count: 2
  vcpus: 2
  memory: 4096
  diskSize: 20G
lan:
  bridge: br0
  range: 192.0.2.200-229
  gateway: null
  prefixLength: null
cilium:
  version: 1.20.2
  gatewayApiVersion: v1.6.3
helm:
  version: v4.3.0
paths:
  imagesDir: /var/lib/libvirt/images
  controlPlaneImagesDir: null
  workerImagesDir: null
  storageImagesDir: null
  cacheDir: null
  clusterDir: null
  secretsDir: null
libvirt:
  uri: qemu:///system
```

## `name` (required)

| Key | Type | Description |
|---|---|---|
| `name` | string | 1–20 characters of `[a-z0-9-]`, not starting or ending with `-`. Used for VM names (`<name>-cp-1`, `<name>-w-1`), the default libvirt network name (`talos-<name>`), the Talos cluster name and the default cluster directory. |

## `talos`

| Key | Type | Default | Description |
|---|---|---|---|
| `version` | string | `v1.14.2` | Talos release (`vX.Y.Z`), **v1.14.0 or later** (the machine config documents the script writes need it). Selects the node image and `talosctl` version. Change it later and run `upgrade` for a rolling upgrade. |
| `kubernetesVersion` | string or null | `null` | Kubernetes version (`1.37.1` or `v1.37.1`). `null` uses the version bundled with the Talos release. `kubectl` is downloaded to match. Change it later and run `upgrade-k8s`. |
| `extensions` | list of strings | `[siderolabs/qemu-guest-agent]` | Official Image Factory system extensions baked into the node image. Changing the list produces a different image (cached separately). |

## `network`

The private network carries cluster traffic: etcd, kubelet, the pod network and
the Talos API. It can be provided in two ways:

- **Created network (default):** the script creates a libvirt NAT network for
  the cluster, with the gateway on `.1`, DHCP reservations for the nodes, and
  DNS. `destroy` removes it again.
- **Existing bridge:** set `existingBridge` and the nodes are attached to a
  bridge that already exists on the host, for example one shared with other VMs
  or connected to a dedicated VLAN. No libvirt network is created. Nodes get
  static addresses from the [address plan](address-plan.md). The host needs an
  address in `<prefix>.0/24` on that bridge, because `talosctl` (and `kubectl`
  without LAN mode) reach the nodes from the host.

| Key | Type | Default | Description |
|---|---|---|---|
| `prefix` | string | `10.44.0` | First three octets of the private /24. For a created network it must not be routed on the host yet, and two clusters running at the same time need different prefixes. For an existing bridge it is the subnet already used on that bridge. |
| `name` | string or null | `null` → `talos-<name>` | Created network only: name of the libvirt network to create. 1–50 chars of `[A-Za-z0-9_.-]`; must not exist yet. |
| `bridgeName` | string or null | `null` → chosen by libvirt (`virbrN`) | Created network only: bridge device for the network. 1–15 chars; must not exist yet. |
| `existingBridge` | string or null | `null` | Attach the nodes to this existing host bridge instead of creating a network. Must differ from `lan.bridge`. |
| `gateway` | string or null | `null` | Existing bridge only: router on the private network, the nodes' default route (metric 1024, so a LAN route wins). Must be in the prefix, outside `.10`–`.99`. Without it, a `lan` section is required so nodes can reach registries. |
| `nameservers` | list or null | `null` → Talos defaults (`1.1.1.1`, `8.8.8.8`) | Existing bridge only: DNS servers for the nodes. Public resolvers don't know local names: to reach a Git server or registry by a LAN hostname, use your local DNS server, e.g. the router. |

## `controlPlanes` and `workers`

| Key | Type | Default | Constraints |
|---|---|---|---|
| `count` | integer | control planes `1`, workers `2` | Control planes: odd, 1–9, fixed after creation. Workers: 0–70; change it later with `scale`. |
| `vcpus` | integer | `2` | Control planes ≥ 2, workers ≥ 1 (Talos minimums). For workers, changes apply to workers added later. |
| `memory` | integer (MiB) | `4096` | Control planes ≥ 2048, workers ≥ 1024. |
| `diskSize` | string | `20G` | `qemu-img` size (`<n>[K\|M\|G\|T]`). Thin-provisioned; must not be smaller than the image. The VM disks have `discard=unmap`: what Talos trims (weekly, its default `FilesystemTrimConfig`) is freed in the host file too; without it the file only grows towards `diskSize`. Count on each disk reaching its full size on the host. |

With `workers.count: 0`, ordinary workloads won't schedule, because control
planes keep their `NoSchedule` taint.

## `lan` (optional section)

If the section is present, LAN mode is on. Omit it, comment it out or set it to
`null` for an internal-only cluster.

| Key | Type | Default | Description |
|---|---|---|---|
| `bridge` | string | required | Existing Linux bridge on the host, connected to the LAN. |
| `range` | string | required | Unused LAN addresses as `a.b.c.X-Y`, e.g. `192.0.2.200-229`. Must hold at least *1 + nodes + 1* addresses (see [Address plan](address-plan.md)) and lie inside the bridge's subnet; with `addressing: dhcp` only the API VIP and the LoadBalancer pool, so 2 at least. |
| `gateway` | string or null | `null` | LAN default gateway for the nodes. `null`: the host's default gateway on `bridge`. |
| `prefixLength` | integer or null | `null` | LAN prefix length. `null`: the host's prefix length on `bridge`. |
| `addressing` | string | `static` | How the nodes' LAN NICs get their address. `static`: from `range` (the address plan). `dhcp`: from the LAN's DHCP server, which also learns each node's name (Talos sends it in the request) and, on a router that registers DHCP names (OPNsense, most home routers), makes `<node>.<domain>` resolvable. The API VIP and the LoadBalancer pool still come from `range`, which then holds only them (pool: everything after the VIP). The script reaches the nodes on the internal network either way. Tested with OPNsense: names registered, LAN default route preferred, LoadBalancer IPs answering. |

## `cilium` (LAN mode only)

| Key | Type | Default | Description |
|---|---|---|---|
| `version` | string | `1.20.2` | Cilium Helm chart version. |
| `gatewayApiVersion` | string | `v1.6.3` | Gateway API CRDs to install (standard channel); with `argocd.addons`, also kept in Git (`gateway-api/`, Application `gateway-api`, never pruned), so a new version reaches a running cluster with `argocd`. Keep it at the version your Cilium release documents. |

## `helm` (LAN mode only)

| Key | Type | Default | Description |
|---|---|---|---|
| `version` | string | `v4.3.0` | Helm release used to install Cilium. |

## `argocd` (optional section)

If the section is present, Argo CD is installed. See
[GitOps with Argo CD](../explanation/gitops.md) for how it works.

| Key | Type | Default | Description |
|---|---|---|---|
| `chartVersion` | string | `10.10.5` | argo-cd Helm chart version (10.10.5 ships Argo CD v3.5.5). |
| `hostname` | string or null | `null` | LAN mode only: serve the Argo CD UI at `https://<hostname>` on the cluster's [ingress gateway](ingress-gateway.md): through a TLSRoute (TLS passed through to Argo CD, which uses its own self-signed certificate), or with a `certManager` section through an HTTPS listener with a certificate from the ACME CA. The name must resolve to the gateway's address or to a load balancer in front of it. `null`: no route, use `kubectl port-forward`. Argo CD never gets a LoadBalancer address of its own. |
| `repository.url` | string | required | `ssh://[user@]host[:port]/path`, `user@host:path`, or `http(s)://host[:port]/path`. |
| `repository.revision` | string | `HEAD` | Branch, tag or commit to sync. |
| `repository.path` | string | `.` | Directory in the repository holding the manifests (plain YAML, Kustomize or Helm, detected by Argo CD). |
| `repository.recurse` | bool | `false` | Plain YAML directories: include subdirectories. |
| `repository.checkFromHost` | bool | `true` | Run `git ls-remote` from the host during `plan`/`create`/`argocd`. Disable it if only the cluster can reach the repository. |
| `repository.auth.method` | string | `none` | `none`, `ssh`, `basic` or `token` (see below). |
| `repository.auth.sshKeyFile` | string | – | `ssh`: private key file, without passphrase. Typically a read-only deploy key. |
| `repository.auth.knownHosts` | string | `auto` | `ssh`: `auto` scans the server's host keys from the host when deploying (fingerprints are printed). `insecure` disables host key checking. Any other value is a `known_hosts` file. |
| `repository.auth.username` | string | – | `basic`: required. `token`: optional, default `git` (GitHub, Gitea and Forgejo accept any name with a token; GitLab expects e.g. `oauth2`). |
| `repository.auth.passwordFile` | string | – | `basic`: required. A file whose content is the password. |
| `repository.auth.tokenFile` | string | – | `token`: required. A file whose content is the token. |
| `repository.auth.insecureSkipTLSVerify` | bool | `false` | `https://` only: accept self-signed certificates. |
| `application.enabled` | bool | `true` | `false`: no root Application, only with `addons.enabled` (the add-ons app-of-apps is then the cluster's only root; `repository.path` is unused). |
| `application.name` | string | `root` | Name of the root Application (in namespace `argocd`). |
| `application.namespace` | string | `default` | Destination namespace for manifests that don't set one. Created if missing. |
| `application.prune` | bool | `true` | Delete resources that were removed from the repository. |
| `application.selfHeal` | bool | `true` | Revert manual changes in the cluster to the repository state. |
| `addons.enabled` | bool | `false` | Manage the add-ons (Cilium, Argo CD itself, cert-manager, Headlamp, Longhorn, gateway, issuer, certificates, routes) with Argo CD from this repository instead of Helm. See [Add-ons in Git](../explanation/gitops.md#add-ons-in-git). |
| `addons.path` | string or null | `null` → `clusters/<name>` | Directory in the repository for the generated definitions. |
| `addons.pushSshKeyFile` | string | – | SSH repositories: a private key with **write** access (e.g. a deploy key with write permission), used only from the host to push the definitions. Argo CD keeps its read-only credential. |
| `addons.pushTokenFile` | string | – | http(s) repositories: a token with write access (username from `auth.username`, default `git`). |
| `addons.sopsAgeKeyFile` | string or null | `null` | The cluster's age key (an `age-keygen` file), created if missing. Set: the add-on Secrets go to the repository SOPS-encrypted, and Argo CD decrypts them with KSOPS. See [Secrets in Git](../explanation/gitops.md#secrets-in-git). |
| `addons.sopsRecipients` | list | `[]` | More age public keys (`age1...`) that can decrypt the Secrets in Git, e.g. yours. |
| `addons.projects.infra`, `addons.projects.services` | string | `platform-infra`, `platform-services` | The Argo CD projects of the generated Applications: `services` for those that need nothing cluster-wide but their namespace (`headlamp`, `ingress`, `talos-backup`), `infra` for the others. The repository provides them. |
| `addons.content` | string | `generate` | `generate`: the generated files are rewritten from the cluster file on each run. `reuse`: those already in the repository are kept as they are (Git is the source) and only missing ones are written. See [Add-ons in Git](../explanation/gitops.md#add-ons-in-git). |

Keys that don't belong to the chosen method are rejected, as are credentials
given inline. Secrets only come from files (see [Credentials](files-and-credentials.md)), so
the cluster file can be committed safely. Relative credential file paths resolve
against `paths.secretsDir` when it's set, otherwise against the cluster file's
directory.

## `oidc` (optional section)

If the section is present, the API servers (and Argo CD, if configured) accept
logins from an OIDC provider. See
[Authentication with Keycloak (OIDC)](../explanation/authentication.md).

| Key | Type | Default | Description |
|---|---|---|---|
| `issuer` | string | required | Issuer URL, e.g. `https://oauth.example.com/realms/example`. Must be reachable from the host and the nodes. |
| `caFile` | string or null | `null` | CA certificate (PEM) for the issuer's TLS certificate, e.g. `/path/to/issuer-root-ca.crt`. Needed for a private CA; it's given to the API servers, Argo CD and kubelogin. |
| `keycloakAdminUser` | string | `admin` | Keycloak admin user (master realm), when the script manages Keycloak. |
| `keycloakAdminPasswordFile` | string or null | `null` | When set, the script creates and updates the realm, groups and clients in Keycloak (the issuer must be a Keycloak realm URL). When `null`, the clients must already exist. |
| `kubernetes.clientId` | string or null | `null` → `k8s-<name>` | Client ID, which is also the token audience the API servers accept. One client per cluster, so a token for one cluster isn't accepted by another. |
| `kubernetes.usernamePrefix` | string | `oidc:` | Prefix for OIDC usernames (`preferred_username` claim). |
| `kubernetes.groupsPrefix` | string | `oidc:` | Prefix for OIDC groups (`groups` claim). |
| `kubernetes.adminGroups` | list | `[k8s-admins]` | Groups bound to `cluster-admin`. |
| `argocd.clientId` | string or null | `null` → `argocd-<name>` | Argo CD's client ID. |
| `argocd.clientSecretFile` | string or null | `null` | Argo CD client secret. Required when the script doesn't manage Keycloak; otherwise read from Keycloak. |
| `argocd.adminGroups` | list | `[argocd-admins]` | Groups with Argo CD's `role:admin`. |
| `headlamp.clientId` | string or null | `null` → `headlamp-<name>` | Headlamp's client ID (with a `headlamp` section). Also accepted by the API servers as token audience, since Headlamp passes the user's token on. |
| `headlamp.clientSecretFile` | string or null | `null` | Headlamp client secret. Required when the script doesn't manage Keycloak; otherwise read from Keycloak. |
| `grafana.clientId` | string or null | `null` → `grafana-<name>` | Grafana's client ID (with a `monitoring` section). |
| `grafana.clientSecretFile` | string or null | `null` | Grafana client secret. Required when the script doesn't manage Keycloak; otherwise read from Keycloak. |
| `grafana.adminGroups` | list | `[grafana-admins]` | Groups whose members are Grafana `Admin`s; everyone else who logs in is a `Viewer`. |
| `crossplane.enabled` | bool | `false` | The Headlamp and Grafana clients, their `groups` mappers and Grafana's admin groups become Crossplane objects (provider-keycloak, namespaced) in the repository, next to the add-on (`generated/headlamp/`, `generated/monitoring/`), instead of API calls: Crossplane keeps Keycloak as the file says and undoes console edits, never deletes. The client secret stays the one in Git (`clientSecretSecretRef` on the add-on's Secret; a new random one when Git has none). Needs `argocd.addons` with `sopsAgeKeyFile` and Crossplane with provider-keycloak in the cluster (the repository's job, not the script's). With `keycloakAdminPasswordFile`, existing clients, mappers and groups are looked up once and adopted (external names). The Kubernetes and Argo CD clients stay API calls: they are needed before Crossplane exists. |
| `crossplane.providerConfig` | string | `default` | The provider-keycloak `ClusterProviderConfig` the objects use. |
| `crossplane.observeOnly` | bool | `false` | `managementPolicies: [Observe]`: Crossplane reads and compares, changes nothing. For taking over existing clients: run with it, compare each object's `status.atProvider` with Keycloak, then run without it. |

## `certManager` (optional section, LAN mode)

| Key | Type | Default | Description |
|---|---|---|---|
| `chartVersion` | string | `v1.21.2` | cert-manager Helm chart version. |
| `acmeServer` | string | required | ACME directory URL, e.g. `https://pki.example.com/acme/acme/directory` (step-ca) or Let's Encrypt's. |
| `caFile` | string or null | `null` | CA certificate (PEM) of the ACME server, when it isn't publicly trusted (e.g. step-ca). Relative to the cluster file. |
| `email` | string or null | `null` | Contact address for the ACME account (Let's Encrypt wants one). |
| `extraHosts` | list | `[]` | More host names served over HTTPS on the ingress gateway, for applications deployed from Git: each gets a listener `https-<first label>` and a certificate (Secret `tls-<host>`). The application's `HTTPRoute`s are its own, attached to that listener (`sectionName: https-<first label>`). First labels must be unique and not `argocd`, `headlamp` or `grafana`. |
| `listenersLabel` | string | `deploy-talos/listeners` | The label key of namespaces (value `ingress`) allowed to add HTTPS listeners to the gateway with a `ListenerSet` ([Ingress gateway](ingress-gateway.md#listeners-from-other-namespaces)). |

## `headlamp` (optional section)

| Key | Type | Default | Description |
|---|---|---|---|
| `chartVersion` | string | `0.45.0` | Headlamp Helm chart version. |
| `hostname` | string or null | `null` | Served at `https://<hostname>` on the ingress gateway; needs `certManager`. `null`: port-forward only. |

## `metricsServer` (optional section)

| Key | Type | Default | Description |
|---|---|---|---|
| `chartVersion` | string | `3.14.0` | metrics-server Helm chart version. |

Needs `argocd.addons.enabled`. See [Metrics and monitoring](../explanation/monitoring.md).

## `monitoring` (optional section)

| Key | Type | Default | Description |
|---|---|---|---|
| `chartVersion` | string | `92.8.0` | kube-prometheus-stack Helm chart version. |
| `hostname` | string or null | `null` | Grafana at `https://<hostname>` on the ingress gateway; needs `certManager`. `null`: port-forward only. |
| `retention` | string | `7d` | How long Prometheus keeps samples. |
| `storageSize` | string | `10Gi` | Prometheus' Longhorn volume (with a `longhorn` section; without one, no volume: data lost on restart). Prometheus also deletes old data beyond 80% of it. |
| `grafanaStorageSize` | string | `1Gi` | Grafana's Longhorn volume (users, preferences, dashboards made in the UI). |

Needs `argocd.addons.enabled`. See [Metrics and monitoring](../explanation/monitoring.md).

## `tuppr` (optional section)

| Key | Type | Default | Description |
|---|---|---|---|
| `chartVersion` | string | `0.5.8` | tuppr Helm chart version (OCI, `ghcr.io/home-operations/charts`). |

Needs `argocd.addons.enabled`. See
[Talos and Kubernetes upgrades with tuppr](../how-to/hand-upgrades-to-tuppr.md).

## `talosBackup` (optional section)

| Key | Type | Default | Description |
|---|---|---|---|
| `image` | string | `ghcr.io/siderolabs/talos-backup:v0.1.0-beta.3-10-gb9fd478` | talos-backup image. The default is a build of the main branch: the last release (beta.3) predates compression, multiple age recipients and a fix of `USE_PATH_STYLE`, which it reads inverted. |
| `schedule` | string | `0 */6 * * *` | Cron schedule of the backups. |
| `s3.endpoint` | string | required | S3 endpoint URL, e.g. `https://backup.example.com` (path-style addressing). |
| `s3.bucket` | string | required | Bucket; snapshots go under `<cluster name>/`. |
| `s3.region` | string | `us-east-1` | Region sent to the endpoint. |
| `s3.accessKeyFile`, `s3.secretKeyFile` | string | required | Files holding the S3 key pair; relative to `paths.secretsDir`. Their content goes to the cluster as a Secret, never to the repository. |
| `s3.caFile` | string or null | `null` | CA certificate (PEM) of the endpoint, when not publicly trusted. Relative to the cluster file. |
| `agePublicKeyFile` | string | required | age public key(s), one per line, that snapshots are encrypted for. Keep the private key off the cluster. |
| `compression` | bool | `true` | zstd-compress snapshots before encryption. |

Needs `argocd.addons.enabled`. See [etcd backups](../how-to/back-up-and-restore-etcd.md).

## `registry` (optional section)

| Key | Type | Default | Description |
|---|---|---|---|
| `mirror` | string | required | Mirror registry URL, `https://host[:port]`. It must serve each upstream under its own namespace (`<mirror>/docker.io/library/nginx`), as Harbor's proxy-cache projects named after the upstream (or zot's on-demand sync) do. |
| `caFile` | string or null | `null` | CA certificate (PEM) of the mirror, when not publicly trusted. Relative to the cluster file. |
| `registries` | list | `docker.io`, `ghcr.io`, `quay.io`, `registry.k8s.io`, `gcr.io`, `factory.talos.dev` | Upstreams sent through the mirror. |

See [Registry mirror](../how-to/use-a-registry-mirror.md).

## `omni` (optional section)

| Key | Type | Default | Description |
|---|---|---|---|
| `endpoint` | string | required | Omni's URL, e.g. `https://omni.example.com`. |
| `serviceAccountKeyFile` | string | required | Key of an Omni service account (Operator or Admin), e.g. the initial one an Omni started with `--create-initial-service-account` writes. A credential: relative to `paths.secretsDir`. |
| `caFile` | string or null | `null` | CA of Omni's certificate, when it isn't publicly trusted: the nodes trust it (`TrustedRootsConfig`), `omnictl` too. Relative to the cluster file. |
| `omnictlVersion` | string | `v1.12.2` | `omnictl` to download: the Omni server's version. |

The `omni` command imports the cluster (see [omni](commands.md#omni)).

## `longhorn` (optional section)

| Key | Type | Default | Description |
|---|---|---|---|
| `chartVersion` | string | `1.13.0` | Longhorn Helm chart version. |
| `nodes.count` | integer | `3` | Dedicated storage nodes `<name>-st-1` … (1–9). More can be added later with `longhorn`; they are never removed. |
| `nodes.vcpus` | integer | `2` | vCPUs per storage node. |
| `nodes.memory` | integer (MiB) | `4096` | Memory per storage node, at least 2048. |
| `nodes.diskSize` | string | `20G` | System disk (Talos), thin. |
| `nodes.dataDiskSize` | string | `50G` | Data disk for Longhorn (second disk, thin qcow2 `<name>-st-N-data.qcow2`). Applies to storage nodes created later; existing disks aren't resized. |
| `replicas` | integer or null | `null` → one per storage node, at most 3 | Replicas per volume (default StorageClass and UI default). At most `nodes.count`: replicas of a volume go to different nodes. |
| `defaultStorageClass` | boolean | `true` | Make the `longhorn` StorageClass the cluster's default. |

The section adds `siderolabs/iscsi-tools` and `siderolabs/util-linux-tools` to
`talos.extensions` (all nodes). Storage nodes have no LAN NIC: with
`network.existingBridge`, `network.gateway` is required so that they can reach
the internet.

## `paths`

| Key | Type | Default | Description |
|---|---|---|---|
| `imagesDir` | string | `/var/lib/libvirt/images` | Where node disks and config ISOs go. Should be inside a libvirt storage pool. |
| `controlPlaneImagesDir`, `workerImagesDir`, `storageImagesDir` | string or null | `null` → `imagesDir` | Another directory for one role's disks and config ISOs (a storage node's data disk too), e.g. control planes on an SSD: etcd waits for every write to reach the disk, and slow writes make the API servers fail. Read by `create`, `scale` and `destroy`; an existing node's files are moved by hand ([Move node disks](../how-to/move-node-disks.md)). |
| `cacheDir` | string or null | `null` → `$XDG_CACHE_HOME/talos/<talos.version>`, i.e. `~/.cache/talos/<talos.version>` when `XDG_CACHE_HOME` is unset | Downloaded tools and images. Shared between clusters. |
| `clusterDir` | string or null | `null` → `<name>-cluster` next to the cluster file | Secrets, generated configs, talosconfig, kubeconfig. |
| `secretsDir` | string or null | `null` | Directory with the credential files (SSH keys, passwords, tokens), kept out of git. **Relative** credential paths resolve against it: `argocd.repository.auth.sshKeyFile`, `passwordFile`, `tokenFile`, a `knownHosts` file, `oidc.keycloakAdminPasswordFile`, `oidc.argocd.clientSecretFile` and `oidc.headlamp.clientSecretFile`. Absolute paths are used as is. `null`: relative paths resolve next to the cluster file. `oidc.caFile` (a public certificate) always resolves next to the cluster file. `template --secrets-dir DIR` sets it. |

## `libvirt`

| Key | Type | Default | Description |
|---|---|---|---|
| `uri` | string | `qemu:///system` | libvirt connection URI. |

## Locations at a glance

The script assumes no location of its own: every file it reads or writes is
set in the cluster file, or derived from it as below. `plan` prints the
resolved directories.

| What | Default | Change it with |
|---|---|---|
| Relative paths in the cluster file | relative to the cluster file's directory | absolute paths |
| Credential files (keys, passwords, tokens) | relative to `paths.secretsDir`, else to the cluster file | `paths.secretsDir`, `template --secrets-dir`, absolute paths |
| Cluster state (secrets, configs, kubeconfig) | `<name>-cluster` next to the cluster file | `paths.clusterDir` |
| Tools and node images | `$XDG_CACHE_HOME/talos/<version>`, default `~/.cache/talos/<version>` | `paths.cacheDir`, or `XDG_CACHE_HOME` |
| Node disks and config ISOs | `/var/lib/libvirt/images` | `paths.imagesDir`; per role `paths.controlPlaneImagesDir`, `workerImagesDir`, `storageImagesDir` |
| libvirt | `qemu:///system` | `libvirt.uri` |
