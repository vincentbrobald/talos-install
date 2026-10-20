# Upgrade Talos

> How-to · [Documentation](../../README.md#documentation)

Move every node to a new Talos release, one node at a time. How the rollout
and rollback work: [Upgrades](../explanation/upgrades.md#talos-one-node-at-a-time).
Options: [`upgrade`](../reference/commands.md#upgrade). With a `tuppr` section
the rollout runs inside the cluster: [Hand upgrades to tuppr](hand-upgrades-to-tuppr.md).

1. Set the release in the cluster file. Talos goes one minor release at a time
   (1.13.x → 1.14.y); check that it supports the cluster's Kubernetes version.

   ```yaml
   talos:
     version: v1.14.2
   ```

2. See the per-node plan and check the cluster's health:

   ```sh
   ./deploy-talos.py upgrade -f lab.yaml --dry-run
   ```

3. Upgrade:

   ```sh
   ./deploy-talos.py upgrade -f lab.yaml
   ```

4. Check: `kubectl get nodes -o wide` shows the new OS image on every node.

Then consider [upgrading Kubernetes](upgrade-kubernetes.md): with
`kubernetesVersion: null`, `upgrade-k8s` moves to the version the new release
ships with.

## If it fails

`upgrade` stops at the failing node, rolls it back, and by default rolls back
the nodes upgraded earlier in the run. The error names the node, the reason,
and what was rolled back. Fix the cause and run `upgrade` again: it continues
with the nodes not yet on `talos.version`.

To keep the nodes that succeeded on the new release and roll back only the
failed one, pass `--on-failure rollback-node`.

## Rehearse a rollback

On a test cluster, `--simulate-failure <node>` runs the real upgrade but
treats that node's check as failed, exercising the whole rollback path:

```sh
./deploy-talos.py upgrade -f test.yaml --simulate-failure test-w-1
```

## Add extensions

Add them to `talos.extensions` and run `upgrade` with the same `talos.version`: nodes
whose image lacks a listed extension are reinstalled, one at a time, through
the same procedure.
