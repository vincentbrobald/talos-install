# Import a cluster into Omni

> How-to · [Documentation](../../README.md#documentation)

Show a cluster in [Omni](https://docs.siderolabs.com/omni), Sidero Labs'
console for Talos clusters, without handing it over. What the command does:
[`omni`](../reference/commands.md#omni). Settings:
[`omni`](../reference/cluster-file.md#omni-optional-section).

1. Create an Omni service account (Operator or Admin) and save its key in a
   file.
2. Add the section:

   ```yaml
   omni:
     endpoint: https://omni.example.com
     serviceAccountKeyFile: omni/service-account-key
     caFile: pki/root_ca.crt          # if Omni's certificate isn't publicly trusted
   ```

3. Check first, then import:

   ```sh
   ./deploy-talos.py omni -f lab.yaml --dry-run
   ./deploy-talos.py omni -f lab.yaml
   ```

4. Check: the cluster appears in Omni, **locked**.

Keep `<clusterDir>/<name>-backup-<time>.zip` private: it holds the cluster's
secrets.

## Locked

While locked, Omni changes nothing: this script, the GitOps repository and
tuppr keep managing the cluster. `omnictl cluster unlock <name>` would hand
the machine configs and the Kubernetes endpoint to Omni.

## Abort an import

`./deploy-talos.py omni -f lab.yaml --abort` aborts an import still locked.
The nodes keep Omni's documents until their backed-up configs are applied
again with `talosctl apply-config`.
