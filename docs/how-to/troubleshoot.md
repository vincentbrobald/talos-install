# Troubleshoot

> How-to · [Documentation](../../README.md#documentation)

Find the cause of an error and fix it. Errors print as `ERROR: ...` and the
command exits with status 1 ([exit status](../reference/commands.md#exit-status)).

## Look at a node

```sh
export TALOSCONFIG=$PWD/lab-cluster/talosconfig KUBECONFIG=$PWD/lab-cluster/kubeconfig
talosctl -n <node-ip> dashboard          # live node dashboard
talosctl -n <node-ip> services           # Talos services and their state
talosctl -n <node-ip> logs kubelet
talosctl -n <node-ip> dmesg -f
virsh console <name>-cp-1                # the VM console (Ctrl+] to leave)
```

`talosctl` works from the host or the internal network only, also in LAN mode.

## Cluster file and host checks

| Symptom | Cause / fix |
|---|---|
| `ERROR: unknown key(s) ...` | Typo in the cluster file; compare with `template` output. |
| `... is already routed on this host` | `network.prefix` collides with an existing network; pick another. |
| `libvirt network '...' already exists` | Another cluster or network uses that name; set `network.name`. |
| `this host has no route to ... on <bridge>` | With `network.existingBridge`, give the host an address in the prefix on that bridge (or pick the prefix that bridge already uses). |
| `node addresses already in use on <bridge>` | Something on the existing bridge uses `.10`–`.99` of the prefix; free them or choose another prefix. |
| `Not removing network ...` during `destroy` | The network named in the file wasn't created by this script for this cluster, so it is left alone on purpose. |
| `addresses in lan.range already in use: ...` | Something on the LAN answers on those addresses. Choose another range, or free them. |
| `domain '...' already exists` | A cluster with that name exists. Run `destroy`, or use another `name`. |

## Creating a cluster

| Symptom | Cause / fix |
|---|---|
| `create` hangs at "Waiting for the Talos API" | Look at the node console: `virsh console <name>-cp-1` (Ctrl+] to leave). |
| `create` hangs at the health check | In another shell: `talosctl -n <cp-ip> dmesg -f`, `talosctl -n <cp-ip> services`, `kubectl get pods -A`. |
| `ERROR: bootstrap failed: ... bootstrap is not available yet` | The first control plane didn't finish booting within five minutes: `talosctl -n <cp-ip> services` shows `cri` waiting for volumes, `dmesg` "Timed out while waiting for udev queue to empty". Seen on a host under heavy load. `destroy`, then `create` again. |
| Gateway returns `no healthy upstream` right after creation | Envoy is still picking up endpoints; retry after a few seconds. |
| New HTTPRoutes get no status; certificates stay "Issuing" with challenges `Waiting for HTTP-01 challenge propagation` | cilium-operator started while the API server was unreachable (e.g. during a node upgrade): its one-time check logged `Required GatewayAPI resources are not found` and its Gateway API controller never started. Existing routes keep working. `kubectl -n kube-system rollout restart deploy/cilium-operator` (traffic is not interrupted). |
| `create` failed half-way | Run `destroy -f FILE -y`, fix the cause, run `create` again. Secrets are reused. |

## Scaling

| Symptom | Cause / fix |
|---|---|
| `draining <node> failed within ...` | A PodDisruptionBudget or a stuck pod blocks eviction. The node is cordoned but kept; fix and re-run `scale`, or `kubectl uncordon` it. |
| `control planes can't be scaled` | `controlPlanes.count` in the file differs from the cluster; set it back. |
| `the new workers' LAN addresses are assigned to LoadBalancer services` | The pool's top addresses are in use; free them or enlarge `lan.range`. |

## Upgrades

| Symptom | Cause / fix |
|---|---|
| `upgrade ... cancelled at <node>: ...` | A step failed and the rollout stopped; the message lists what was rolled back. Fix the cause and run `upgrade` again. |
| `upgrade one minor release at a time` | Set `talos.version` to the next minor release first, upgrade, then continue. |
| `... newer than talos.version ...; downgrades are not supported` | `talos.version` is older than what runs; fix the file (rollback is automatic on failure). |
| `<node> does not answer; all nodes must be up before an upgrade` | Bring the node back (or remove it with `scale`) before upgrading. |
| `pre-upgrade gate failed: API versions removed in the target are still in use` | Migrate those clients/manifests to the newer API version, or `--force` if they're no longer used. |
| `... declares kubeVersion '...', which excludes <version>` | Upgrade that add-on first (`cilium.version` / `argocd.chartVersion`), or `--force` if you've checked compatibility. |
| `Talos vX supports Kubernetes A to B` | Choose a target in that window, or upgrade Talos first. |
| `Kubernetes upgrade to X stopped: ...` | Fix the cause and run `upgrade-k8s` again; the message shows each component's current version. |

## Login (OIDC)

| Symptom | Cause / fix |
|---|---|
| `Unauthorized` with `kubeconfig-oidc` | The token's audience must be this cluster's client (`k8s-<name>`), and the API servers must reach the issuer. Check `kubectl -n kube-system logs kube-apiserver-<cp>` for `jwt`/`oidc` errors. |
| `Forbidden` for an OIDC user | Authenticated but not authorized: put the user in one of `oidc.kubernetes.adminGroups` in Keycloak, or add a RoleBinding for their `oidc:` group. |
| Argo CD login loops or shows no groups | The user isn't in `oidc.argocd.adminGroups`, or the redirect URL changed (re-run `deploy-talos.py argocd -f FILE`). |

## Argo CD and Git

| Symptom | Cause / fix |
|---|---|
| `Application 'root' sync failed: ...` | Argo CD gave up after its retries; the message says why, e.g. a manifest needs an API (such as the Gateway API) the cluster doesn't have. |
| `cannot access <url> from this host: authentication failed` | Wrong username, password or token, or the account lacks read access. |
| `... is not a usable SSH private key` | The key has a passphrase (unsupported by Argo CD) or isn't a private key. |
| `the server's SSH host key does not match knownHosts` | The `knownHosts` file is outdated, or the server isn't the one you expect. |
| `revision '...' not found` | The branch or tag doesn't exist (yet); push it or fix `repository.revision`. |
| `Application 'root' reports: ... no such host` (local hostname) | The nodes' DNS can't resolve the name. With `existingBridge`, set `network.nameservers` to a DNS server that knows it (e.g. the LAN router). |
| `Application 'root' reports: ...` | Argo CD itself failed, e.g. the nodes can't reach the Git server or the credentials don't work from the cluster. `kubectl -n argocd describe application root`. |
| `Application 'root' not Synced/Healthy after 600s` | Manifests apply but workloads don't become healthy (image pulls, crash loops). Check `kubectl get pods -A`; the cluster itself is fine. |
