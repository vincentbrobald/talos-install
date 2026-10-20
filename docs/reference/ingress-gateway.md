# Ingress gateway

> Reference · [Documentation](../../README.md#documentation)

The shared Gateway the script creates in LAN mode. How to use it:
[Expose an application](../how-to/expose-an-application.md). Why it looks
like this: [LAN mode](../explanation/lan-mode.md#the-ingress-gateway).

| Property | Value |
|---|---|
| Gateway | `ingress/ingress` |
| GatewayClass | `cilium` |
| Address | the first free LoadBalancer pool address ([address plan](address-plan.md#lan-range-lan-mode)); `kubectl -n ingress get gateway ingress` |
| DNS | `*.apps.<cluster>.<domain>` points at it ([register DNS records](../how-to/register-dns-records.md)) |

## Listeners

| Listener | Port | Exists | Use |
|---|---|---|---|
| `http` | 80 | always | `HTTPRoute`s from any namespace, routed by host name |
| `tls-passthrough` | 443 | without `certManager` | `TLSRoute`s, routed by SNI name, TLS passed through to the backend |
| `https-argocd` | 443 | with `certManager` and `argocd.hostname` | Argo CD's UI |
| `https-headlamp` | 443 | with `certManager` and `headlamp.hostname` | Headlamp |
| `https-grafana` | 443 | with `certManager` and `monitoring.hostname` | Grafana |
| `https-<first label>` | 443 | with `certManager`, one per `certManager.extraHosts` entry | applications from Git |

An `https-*` listener terminates TLS with the certificate in Secret
`ingress/tls-<host>` (cert-manager, ClusterIssuer `acme`).

## Listeners from other namespaces

| Property | Value |
|---|---|
| Kind | `ListenerSet` (`gateway.networking.k8s.io/v1`, Gateway API v1.5+) |
| Parent | `{name: ingress, namespace: ingress}` |
| Allowed namespaces | those labelled `<certManager.listenersLabel>=ingress` (default `deploy-talos/listeners=ingress`) |
| Requires | a `certManager` section |
| Certificate | in the ListenerSet's own namespace |

Routes attach to a ListenerSet with
`parentRefs: [{group: gateway.networking.k8s.io, kind: ListenerSet, name: <name>, sectionName: <listener>}]`.
