# Upgrade Kubernetes

> How-to · [Documentation](../../README.md#documentation)

Move the Kubernetes components to a new version, without rebooting nodes.
How the gates and phases work: [Upgrades](../explanation/upgrades.md#kubernetes-gated-phased-no-rollback).
Options: [`upgrade-k8s`](../reference/commands.md#upgrade-k8s).

1. Make sure the add-ons support the target first: Cilium (`cilium.version`),
   the Gateway API CRDs and Argo CD (`argocd.chartVersion`, then
   `./deploy-talos.py argocd -f lab.yaml`). Check each project's own
   compatibility matrix, not only its chart's `kubeVersion`.
2. Set the version; `null` means the default of the cluster's Talos release:

   ```yaml
   talos:
     kubernetesVersion: 1.37.1
   ```

3. Run the gates and see Talos' own plan:

   ```sh
   ./deploy-talos.py upgrade-k8s -f lab.yaml --dry-run
   ```

4. Upgrade:

   ```sh
   ./deploy-talos.py upgrade-k8s -f lab.yaml
   ```

5. Check: `kubectl get nodes` shows the new version on every kubelet, and with
   Argo CD the root Application is still Synced and Healthy.

## If a gate refuses

| Finding | What to do |
|---|---|
| a node isn't on `talos.version` | finish the [Talos upgrade](upgrade-talos.md) first |
| the target is outside the Talos release's window | pick a target in the window, or upgrade Talos first |
| API versions removed in the target are still requested | migrate those clients or manifests; `--force` if they're no longer used |
| a chart's `kubeVersion` excludes the target | upgrade that add-on; `--force` if you've checked compatibility |

## If it stops halfway

There is no rollback for Kubernetes. The error shows the API server's and each
kubelet's version; fix the cause and run `upgrade-k8s` again, it continues
where it stopped.
