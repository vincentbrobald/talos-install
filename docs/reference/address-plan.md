# Address plan

> Reference · [Documentation](../../README.md#documentation)

Which address each node and service gets. `plan` prints the exact allocation
for a cluster file. Why the layout is this way: [Architecture](../explanation/architecture.md#the-address-plan).

## Private network

`<network.prefix>.0/24`. With a created network every node gets its address
through a DHCP reservation; on an existing bridge (`network.existingBridge`) it
is configured statically on the node.

| Address | Use |
|---|---|
| `.1` | Created network: gateway and DNS (host side). Existing bridge: free for your router (`network.gateway`) |
| `.10` | Kubernetes API VIP, when there are several control planes and no LAN |
| `.11`–`.19` | Control planes `cp-1` … `cp-9` |
| `.21`–`.90` | Workers `w-1` … `w-70` |
| `.91`–`.99` | Storage nodes `st-1` … `st-9` (`longhorn` section) |
| `.100`–`.199` | Created network: DHCP pool (unused by the cluster) |

On an existing bridge nothing else may use `.10`–`.99`, a DHCP server on that
bridge included. `plan` and `create` refuse to start if any node address
answers ping.

## LAN range (LAN mode)

`lan.range`, e.g. `192.0.2.200-229`:

| Address | Use |
|---|---|
| 1st | Kubernetes API VIP |
| next | One per control plane |
| last, counting down | One per worker: `w-1` gets the last address, `w-2` the one before, … |
| in between | Cilium LoadBalancer pool (Gateways, `type: LoadBalancer` Services) |

With `lan.addressing: dhcp` the nodes' LAN addresses come from the LAN's DHCP
server, and the range holds only the API VIP and the pool (everything after
the VIP). Storage nodes take no LAN address.

Example: `192.0.2.200-229`, 3 control planes, 2 workers:

| Address | Use |
|---|---|
| `.200` | API VIP |
| `.201`–`.203` | control planes |
| `.204`–`.227` | LoadBalancer pool (the [ingress gateway](ingress-gateway.md) takes the first) |
| `.228` | `w-2` |
| `.229` | `w-1` |

The range must hold at least *1 + nodes + 1* addresses (VIP, every node, one
pool address).

## API endpoint

| Cluster | Endpoint |
|---|---|
| LAN mode | the LAN VIP |
| several control planes, no LAN | the internal VIP `.10` |
| one control plane, no LAN | the first control plane's address |
