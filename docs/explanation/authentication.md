# Authentication

> Explanation · [Documentation](../../README.md#documentation)

How people log in to a cluster with an `oidc` section, and who may do what.
To set it up: [Add Keycloak login](../how-to/add-keycloak-login.md). Settings:
[`oidc`](../reference/cluster-file.md#oidc-optional-section).

## Two ways in

- **The admin kubeconfig** (`<clusterDir>/kubeconfig`) authenticates with a
  client certificate. It always works and is the break-glass access.
- **OIDC** (`<clusterDir>/kubeconfig-oidc`): people log in through an OIDC
  provider and get the rights of their groups. The script is written for
  Keycloak, but any provider works once its clients exist.

## What a login involves

- **The API servers** trust the issuer through a `KubeAuthenticationConfig`:
  usernames from `preferred_username`, groups from `groups`, both with a
  prefix (`oidc:`), so OIDC names can't collide with built-in ones. Talos'
  anonymous `/livez`, `/readyz` and `/healthz` stay open.
- **Audiences.** Each cluster has its own client (`k8s-<name>`), and the API
  servers only accept tokens issued for it: a token for another cluster is
  rejected. Headlamp's client is accepted too, because Headlamp passes the
  user's own token on (below).
- **kubelogin** runs the device-code flow: it prints a URL, you open it in any
  browser and log in, which works from a headless host. Tokens are cached in
  `~/.kube/cache/oidc-login`.
- **Rights.** ClusterRoleBinding `oidc-cluster-admins` gives the admin groups
  (prefixed, e.g. `oidc:k8s-admins`) `cluster-admin`. Everyone else is
  authenticated but has nothing until a (Cluster)RoleBinding names their
  `oidc:` group. Users never come from the script: people are put into groups
  in Keycloak.
- **Argo CD** shows "Log in via Keycloak", gives `role:admin` to its admin
  groups and nothing to others; its local `admin` account remains.

## Keycloak managed by the script

With `keycloakAdminPasswordFile`, the script creates what the login needs:

| Object | Shape |
|---|---|
| realm | created if missing |
| groups | the admin groups (`k8s-admins`, `argocd-admins`, `grafana-admins`) |
| `k8s-<name>` | public; authorization code with PKCE and the device-code grant; no password grant |
| `argocd-<name>` | confidential, redirect to `/auth/callback` |
| `headlamp-<name>` | confidential, redirect to `/oidc-callback` |
| `grafana-<name>` | confidential with PKCE, redirect to `/login/generic_oauth` |
| `groups` mapper | on every client: group names (not paths) in the tokens |

**Crossplane for the add-ons' clients.** With `oidc.crossplane.enabled`, the
Headlamp and Grafana clients (and Grafana's groups) are written to the
repository as Crossplane objects instead of API calls: Crossplane keeps them
as the file says and undoes console edits. The Kubernetes and Argo CD clients
stay API calls of the script, because they are needed before Crossplane
exists in the cluster.

## Applying to a running cluster

The API servers restart one control plane at a time, each confirmed before
the next. Clients using the VIP see a short interruption (about 25 s) while
the VIP holder's API server restarts.

**Tested:** members of the admin group got `cluster-admin`, users without it
were authenticated but forbidden; another cluster's token was rejected; the
kubelogin path worked; Argo CD single sign-on worked through a gateway route
(also behind an external SNI load balancer) and through a port-forward.

## Related

- [HTTPS and Headlamp](https-and-headlamp.md): how Headlamp uses the user's token.
- [Security](security.md#oidc): who controls admin rights.
