# Hand upgrades to tuppr

> How-to · [Documentation](../../README.md#documentation)

Let the cluster run its Talos and Kubernetes rollouts itself, from resources in
Git, with [tuppr](https://github.com/home-operations/tuppr). How it works:
[Upgrades](../explanation/upgrades.md#tuppr-upgrades-from-inside-the-cluster).
Needs `argocd.addons.enabled` ([Manage the add-ons in Git](manage-addons-in-git.md)).

## Enable it

1. Add the section:

   ```yaml
   tuppr:
     chartVersion: 0.5.8
   ```

2. Apply:

   ```sh
   ./deploy-talos.py argocd -f lab.yaml
   ```

   The repository gains the `tuppr` Application and `generated/tuppr/`
   (`TalosUpgrade talos`, `KubernetesUpgrade kubernetes`); the control planes
   get Talos API access for namespace `system-upgrade`, without a reboot.

3. Check:

   ```sh
   kubectl get talosupgrade,kubernetesupgrade
   ```

   Both should be `Completed` at the current versions.

## Upgrade

Nothing changes in how you start an upgrade: edit `talos.version` or
`talos.kubernetesVersion` and run `upgrade` or `upgrade-k8s`, as in
[Upgrade Talos](upgrade-talos.md) and [Upgrade Kubernetes](upgrade-kubernetes.md).
The script runs its gates, pushes the new version, and follows tuppr until it
completes. Watch it with:

```sh
kubectl get talosupgrade talos -w
```

Keep the cluster file as the source: editing the version in Git also starts a
rollout, but the next run of the script resets it to the file's version.
