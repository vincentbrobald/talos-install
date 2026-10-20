# Security

> Explanation · [Documentation](../../README.md#documentation)

What the script protects, how, and the limits to keep in mind.

## Integrity of what is downloaded

`talosctl`, `kubectl`, `helm`, `kubelogin` and `omnictl` are SHA256-verified
against the checksums their release sites publish. Signatures (cosign) aren't
checked. The Image Factory publishes no checksums for generated images, so the
node image, like the Cilium chart and the Gateway API CRDs, relies on HTTPS.

## Credentials

- **Files, never values.** The cluster file names the files that hold
  credentials ([list](../reference/files-and-credentials.md#credential-files)),
  so it can be committed. Inline values are impossible: unknown keys are
  rejected.
- **Through stdin.** Credentials reach the cluster through `kubectl apply -f -`,
  never through a file on disk, and Helm values hold none: Argo CD's OIDC
  settings reference `$argocd-keycloak:clientSecret`, Headlamp and Grafana
  read Secrets.
- **Secrets on disk.** The cluster directory, the config ISOs and the node
  disks contain the cluster's secrets and are readable by root only.

## LAN exposure

In LAN mode the API VIP and every Gateway or LoadBalancer Service are
reachable from the whole LAN, and the API also answers on each control
plane's own LAN address. The API authenticates every request, but consider who
shares that network. `lan.range` must stay outside the router's DHCP pool: the
script can only check that nothing answers *now*.

## Argo CD credentials

- Repository credentials end up in a Secret in namespace `argocd`, readable by
  cluster admins: use read-only deploy keys or tokens.
- `knownHosts: auto` trusts whatever host key the server presents at deploy
  time (trust on first use). Pin a `known_hosts` file for production.
- `insecure` and `insecureSkipTLSVerify` disable server verification
  entirely.
- With SOPS, Argo CD's repo server runs plugins named in the repository
  ([GitOps](gitops.md#secrets-in-git)).

## OIDC

Admin rights follow Keycloak group membership: protect the Keycloak admin
account and the realm accordingly. With `keycloakAdminPasswordFile` the script
uses the *master* realm's admin; an admin with rights on the cluster realm
only is a tighter alternative.

## Backups

The talos-backup credential only needs to write. A bucket where it can't read
or delete (object lock) means a stolen cluster credential can't destroy the
backups, and snapshots are age-encrypted for a key kept off the cluster.

## Kubelet certificates

metrics-server and Prometheus don't verify the kubelets' self-signed serving
certificates (they authenticate with their tokens). Serving certificates
signed by the cluster CA (`rotate-server-certificates` and a CSR approver)
would close this.

## Single points of failure

With one control plane, the API is down whenever it reboots. With one worker,
that worker runs every workload and announces every LoadBalancer address.
