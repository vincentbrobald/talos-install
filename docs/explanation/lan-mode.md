# LAN mode

> Explanation · [Documentation](../../README.md#documentation)

What changes when a cluster file has a `lan` section, and why. To build one:
[Getting started, step 4](../tutorials/getting-started.md#4-put-a-cluster-on-the-lan).
Settings: [`lan`](../reference/cluster-file.md#lan-optional-section),
[address plan](../reference/address-plan.md#lan-range-lan-mode).

## Two networks

Every node keeps its NIC on the private network (`eth0`) and gets a second one
(`eth1`) on `lan.bridge`.

- **Cluster traffic stays internal.** etcd, kubelet, the pod network and the
  Talos API use `eth0`. The LAN only carries what is meant for it.
- **Replies take the way they came.** The LAN default route (through
  `lan.gateway`) wins over the internal one, so answers to LAN clients leave
  through the LAN.
- **The Kubernetes API is on the LAN VIP,** moved between control planes on
  failure (about 30 seconds).
- **IPv6 is off on `eth1`,** so router advertisements can't give nodes
  globally routable addresses.
- **The host isn't changed.** The VMs are only attached to the existing
  bridge. `talosctl` therefore only works from the host or the internal
  network, by design.

## Cilium instead of flannel

LAN mode needs LoadBalancer addresses and a Gateway API implementation, so
Cilium replaces flannel and kube-proxy, with:

- the Gateway API controller (GatewayClass `cilium`);
- a `CiliumLoadBalancerIPPool` `lan` covering the rest of the range;
- a `CiliumL2AnnouncementPolicy` `lan` that answers ARP for LoadBalancer and
  external IPs on `eth1` (storage nodes are excluded: they have no LAN NIC);
- the shared ingress gateway, below.

## Firewalled node services

The Talos API (50000), trustd (50001), kubelet (10250) and etcd (2379–2380)
only accept connections from the internal network. Three rules do this:
`node-services` (50001, etcd), `kubelet` (10250) and `talos-api` (50000).

Each port is in exactly one rule, because a rule drops what doesn't come from
its own subnets: two rules on one port would admit nothing. Some add-ons need
a port from inside the cluster, and a pod connecting to its own node keeps its
pod address, so:

- with `tuppr` or `talosBackup`, `talos-api` also admits the pod network
  (`10.244.0.0/16`): tuppr and talos-backup talk to the Talos API from a pod;
- with `metricsServer` or `monitoring`, `kubelet` admits the pod network:
  metrics-server and Prometheus read the kubelets, which authenticate and
  authorize every request.

## The ingress gateway

One shared Gateway, `ingress/ingress`, takes one LoadBalancer address and
serves every application by host name ([listeners](../reference/ingress-gateway.md)).
One address for everything is what makes a single DNS wildcard
(`*.apps.<cluster>.<domain>`) and a single forward from an outside load
balancer (ports 80 and 443) enough.

**Passthrough or termination, not both.** Cilium can't mix TLS passthrough and
TLS termination on one port. Without `certManager`, port 443 passes TLS
through by SNI name and backends terminate it themselves (Argo CD with its
self-signed certificate). With `certManager`, port 443 only terminates, with
a certificate per host from the ACME CA, and the passthrough listener goes
away: [HTTPS and Headlamp](https-and-headlamp.md). An application that needs
termination without `certManager` can bring its own Gateway, at the cost of a
LoadBalancer address of its own.

**Listeners from other namespaces.** A namespace labelled
`<label>=ingress` may add HTTPS listeners with a `ListenerSet`, each with its
own certificate, without touching the Gateway or the cluster file. The label
key is `certManager.listenersLabel` (default `deploy-talos/listeners`). Labelling a namespace
is a decision for whoever runs the platform: it lets the namespace claim any
host name not yet taken. A GitOps repository can, for example, label its
teams' namespaces so that their own Argo CDs get host names this way.

## Exposure

The API VIP and every Gateway or LoadBalancer Service are reachable from the
whole LAN; the API also answers on each control plane's own LAN address. See
[Security](security.md#lan-exposure).

## Related

- [Expose an application](../how-to/expose-an-application.md)
- [Register DNS records](../how-to/register-dns-records.md)
