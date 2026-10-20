# Change a running cluster

> Tutorial · [Documentation](../../README.md#documentation)

In this tutorial you build a throwaway cluster on an older Talos release and
put it through the changes a real cluster goes through: more workers, fewer
workers, an upgrade that fails and rolls back, and an upgrade that succeeds.
An application keeps running throughout, and you watch where it goes. At the
end you remove the cluster.

You need what [Getting started](getting-started.md) needed, about 12 GiB of
free memory, and 40 minutes, most of it waiting. Run every command as root,
from the directory that holds `deploy-talos.py`. The cluster's network is
private to this host.

## 1. Build a cluster on the previous release

Write a cluster file named `day2` and set it one patch release back from
what `template` writes (here v1.14.2, so v1.14.1):

```sh
./deploy-talos.py template --preset minimal --name day2 -o day2.yaml
sed -i 's/^  version: v1.14.2$/  version: v1.14.1/' day2.yaml
grep -n '^  version: v1' day2.yaml
./deploy-talos.py create -f day2.yaml
```

You should see `version: v1.14.1`, and after a few minutes "Cluster 'day2'
is ready", with three nodes `Ready` on `Talos (v1.14.1)`. Use the commands it
prints:

```sh
export KUBECONFIG=$PWD/day2-cluster/kubeconfig
export TALOSCONFIG=$PWD/day2-cluster/talosconfig
export PATH=~/.cache/talos/v1.14.1:$PATH
```

Run an application with two replicas, and a PodDisruptionBudget that keeps
at least one of them up whenever a node is drained:

```sh
kubectl create deployment hello --image=docker.io/nginxinc/nginx-unprivileged:stable-alpine --replicas=2
kubectl create poddisruptionbudget hello --selector=app=hello --min-available=1
kubectl rollout status deployment/hello
kubectl get pods -o wide
```

`create deployment` prints a warning about Pod Security `restricted`: only a
warning here. You should see the two pods `Running`, one on `day2-w-1` and
one on `day2-w-2`.

## 2. Add a worker

In `day2.yaml`, set `workers.count` to `3`. See what would change, then do it:

```sh
./deploy-talos.py scale -f day2.yaml --dry-run
./deploy-talos.py scale -f day2.yaml
```

The dry run lists `add day2-w-3 (10.44.0.23)`. Within two minutes the new
worker is `Ready` in `kubectl get nodes`. Give it something to run:

```sh
kubectl scale deployment hello --replicas=3
kubectl get pods -o wide
```

You should see a third pod, on `day2-w-3`.

## 3. Remove it again

Set `workers.count` back to `2`, and:

```sh
./deploy-talos.py scale -f day2.yaml
kubectl get pods -o wide
```

It asks before removing a worker. Then it drains `day2-w-3` (its pod is
evicted, within what the PodDisruptionBudget allows), removes it, and checks
the cluster. You should see three pods again, all on `day2-w-1` and
`day2-w-2`: the evicted one was started elsewhere before the node went.

## 4. Rehearse a failed upgrade

Set `talos.version` to `v1.14.2` in `day2.yaml`. First the plan:

```sh
./deploy-talos.py upgrade -f day2.yaml --dry-run
```

You should see the three nodes in order, control plane first, each
`v1.14.1 -> v1.14.2`, and "on failure: roll back the failed node and every
node upgraded in this run, then stop".

Now upgrade, telling the script to treat `day2-w-1`'s check as failed:

```sh
./deploy-talos.py upgrade -f day2.yaml --simulate-failure day2-w-1 -y
```

Follow the log. `day2-cp-1` is drained, upgraded, checked and put back;
`day2-w-1` is upgraded, then "fails". The script cancels the upgrade, rolls
`day2-w-1` back to its previous installation, checks the cluster, then rolls
back `day2-cp-1` too, one node at a time, checking the cluster after each. It
ends with an `ERROR` that says what happened:

```
ERROR: upgrade to v1.14.2 cancelled at day2-w-1: simulated failure (--simulate-failure)
rolled back: day2-w-1, day2-cp-1; still on v1.14.2: none; the cluster is healthy
```

Then:

```sh
kubectl get nodes -o wide
```

You should see every node `Ready` on `Talos (v1.14.1)`, none
`SchedulingDisabled`. Talos keeps the previous installation next to the new
one, so a rollback is a reboot, not a reinstall.

## 5. Upgrade for real

```sh
./deploy-talos.py upgrade -f day2.yaml -y
kubectl get nodes -o wide
kubectl get pods -o wide
```

The same rollout runs without the simulated failure and ends with "All 3
nodes of 'day2' run v1.14.2". You should see `Talos (v1.14.2)` on every node,
and the three `hello` pods `Running`: each drain moved them, and the
PodDisruptionBudget kept at least one up the whole time. They may all sit on
one worker now: Kubernetes doesn't rebalance pods after a drain.

## 6. Remove the cluster

```sh
./deploy-talos.py destroy -f day2.yaml
```

It asks for confirmation, then removes the VMs and the network.
`day2-cluster/` stays with the cluster's secrets; delete it too.

## What you did

You changed a running cluster in the ways that matter day to day, each with a
preview first, and saw the safety nets work: drains that respect
PodDisruptionBudgets, an upgrade that checks the cluster after every node,
and a rollback that undoes a failed rollout node by node.

## Next steps

- On a real cluster: [Scale workers](../how-to/scale-workers.md),
  [Upgrade Talos](../how-to/upgrade-talos.md),
  [Upgrade Kubernetes](../how-to/upgrade-kubernetes.md).
- Let the cluster upgrade itself: [Hand upgrades to tuppr](../how-to/hand-upgrades-to-tuppr.md).
- How the rollout and its rollback work: [Upgrades](../explanation/upgrades.md).
