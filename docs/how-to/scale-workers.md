# Scale workers

> How-to · [Documentation](../../README.md#documentation)

Add or remove workers on a running cluster. Option details:
[`scale`](../reference/commands.md#scale).

## Change the worker count

1. Set the new count in the cluster file:

   ```yaml
   workers:
     count: 4
   ```

2. See what would change; this also runs the checks:

   ```sh
   ./deploy-talos.py scale -f lab.yaml --dry-run
   ```

3. Apply it:

   ```sh
   ./deploy-talos.py scale -f lab.yaml
   ```

4. Check: `kubectl get nodes` lists the new workers Ready, or the removed ones
   gone.

**Scaling out**, new workers are numbered after the existing ones. In LAN mode
the LoadBalancer pool first shrinks to free their addresses; `scale` refuses
if those addresses are taken by a LoadBalancer Service.

**Scaling in**, the highest-numbered workers go first, one at a time: each is
drained (PodDisruptionBudgets respected), deleted from Kubernetes, shut down,
and its disk removed; in LAN mode its address goes back to the pool. Keep
enough capacity on the remaining workers for the drained pods. Data in
`emptyDir` or local volumes on a removed worker is lost.

Measured on a 3+4 LAN cluster with requests every 0.2 s: scaling out 2→4 lost
none; scaling in 4→1 lost one in about 900 (a pod shutting down). Apps that
handle SIGTERM or have a short `preStop` delay lose none.

## When a drain doesn't finish

If a drain exceeds `--drain-timeout` (a PodDisruptionBudget allows no
eviction, a pod is stuck), `scale` stops: the node is cordoned but running,
nothing is deleted. Fix the cause and run `scale` again, or keep the node with
`kubectl uncordon <node>`.

## Grow a running worker's disk

A changed `workers.diskSize` only applies to new workers. To grow an existing
worker's disk, one worker at a time:

1. `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`
2. `talosctl -n <ip> shutdown`
3. `qemu-img resize <imagesDir>/<node>.qcow2 <size>`
4. `virsh start <node>`. Talos grows its `EPHEMERAL` partition at boot; check
   with `talosctl -n <ip> get volumestatus EPHEMERAL`.
5. `kubectl uncordon <node>`

Changed `vcpus` and `memory` likewise only apply to workers added later.

## Limits

- Control planes can't be scaled: `scale` refuses if `controlPlanes.count`
  differs from the cluster.
- In LAN mode, `lan.range` needs room for VIP, control planes, workers and at
  least one pool address.
- With `workers.count: 0`, workloads have nowhere to go: control planes keep
  their `NoSchedule` taint.
