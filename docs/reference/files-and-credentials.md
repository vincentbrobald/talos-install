# Files and credentials

> Reference · [Documentation](../../README.md#documentation)

Every file the script reads or writes. Where each location comes from is set
in the cluster file ([`paths`](cluster-file.md#paths),
[locations at a glance](cluster-file.md#locations-at-a-glance)); `plan` prints
the resolved directories. Why credentials are handled this way:
[Security](../explanation/security.md#credentials).

## Credential files

The cluster file names the **files** holding credentials; it never holds a
value itself.

| Credential | Key in the cluster file |
|---|---|
| Git SSH deploy key (read) | `argocd.repository.auth.sshKeyFile` |
| Git password / token (read) | `argocd.repository.auth.passwordFile` / `tokenFile` |
| Git key / token with write access (add-ons) | `argocd.addons.pushSshKeyFile` / `pushTokenFile` |
| The cluster's age key | `argocd.addons.sopsAgeKeyFile` |
| Keycloak admin password | `oidc.keycloakAdminPasswordFile` |
| Argo CD OIDC client secret (Keycloak not managed) | `oidc.argocd.clientSecretFile` |
| Headlamp / Grafana OIDC client secret (Keycloak not managed) | `oidc.headlamp.clientSecretFile`, `oidc.grafana.clientSecretFile` |
| talos-backup S3 key pair | `talosBackup.s3.accessKeyFile`, `secretKeyFile` |
| Omni service account key | `omni.serviceAccountKeyFile` |

- Each file holds just the value; a trailing newline is ignored.
- Relative paths resolve against `paths.secretsDir` when set, otherwise
  against the cluster file's directory.
- Keep them mode 600 and out of Git.
- Inline values are rejected (unknown keys); the removed `passwordEnv` /
  `tokenEnv` keys give an error naming the file key to use.

## Credentials in the cluster

| Secret | Holds |
|---|---|
| `argocd/gitops-repository` | the Git URL and credential (label `argocd.argoproj.io/secret-type: repository`) |
| `argocd/argocd-keycloak` | Argo CD's OIDC client secret (`$argocd-keycloak:clientSecret` in its OIDC settings) |
| `argocd/sops-age` | the cluster's age key (SOPS mode) |
| `argocd/argocd-initial-admin-secret` | Argo CD's local admin password |
| `headlamp/headlamp-oidc` | Headlamp's OIDC settings and client secret |
| `monitoring/grafana-oidc`, `monitoring/grafana-admin` | Grafana's client secret, its local admin |
| `talos-backup/talos-backup-s3` | the S3 key pair |

## Files the script writes

| Path | Content |
|---|---|
| `<cacheDir>/talosctl`, `kubectl`, `helm`, `kubelogin`, `omnictl` | Downloaded tools (SHA256-verified) |
| `<cacheDir>/nocloud-amd64-<schematic>.qcow2` | Talos node image for the extension set |
| `<cacheDir>/helm-home/` | Helm config and cache (`~/.config/helm` stays untouched) |
| `<clusterDir>/secrets.yaml` | Cluster PKI and tokens. **Keep it private** |
| `<clusterDir>/talosconfig` | `talosctl` client config (endpoints: control planes) |
| `<clusterDir>/kubeconfig` | Admin kubeconfig: certificate-based, the break-glass access |
| `<clusterDir>/kubeconfig-oidc` | Kubeconfig for OIDC users via kubelogin (no credentials inside) |
| `<clusterDir>/controlplane.yaml`, `worker.yaml`, `nodes/*.yaml` | Generated machine configs |
| `<clusterDir>/patch-*.yaml`, `network.xml` | Inputs used for this cluster |
| `<clusterDir>/<name>-backup-<time>.zip` | `omni`: Omni's backup of the node configs (holds the cluster's secrets) |
| `<imagesDir>/<node>.qcow2` | Node disk (holds the machine config) |
| `<imagesDir>/<node>-data.qcow2` | Storage node data disk (`longhorn`) |
| `<imagesDir>/<node>-cidata.iso` | Node config as cloud-init user-data |
| `~/.kube/cache/oidc-login` | kubelogin's token cache |

| Permission | Applies to |
|---|---|
| mode 700 | the cluster directory |
| readable by root only | `secrets.yaml`, the machine configs, `talosconfig`, `kubeconfig`, the config ISOs, the node disks |

## Files next to the script

| Path | Content |
|---|---|
| `templates/plan.txt.j2` | the `plan` output |
| `templates/cluster.yaml.j2` | the cluster file `template` writes |
