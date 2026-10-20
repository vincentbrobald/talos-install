# Back up and restore etcd

> How-to · [Documentation](../../README.md#documentation)

Back the cluster's etcd up to S3 with
[talos-backup](https://github.com/siderolabs/talos-backup), and restore it.
Settings: [`talosBackup`](../reference/cluster-file.md#talosbackup-optional-section).
Needs [the add-ons in Git](manage-addons-in-git.md).

## Set up backups

1. Prepare a bucket and a key pair that can **write only** (never read or
   delete), with object lock if you can: a stolen cluster credential then
   can't destroy the backups.
2. Make an age key pair for the snapshots and keep the private key off the
   cluster:

   ```sh
   age-keygen -o talos-backup-age.key
   age-keygen -y talos-backup-age.key > talos-backup-age.pub
   ```

3. Add the section (credential files relative to `paths.secretsDir`):

   ```yaml
   talosBackup:
     s3:
       endpoint: https://backup.example.com
       bucket: talos-backups
       accessKeyFile: backup/talos-backup-access-key
       secretKeyFile: backup/talos-backup-secret-key
       caFile: pki/root_ca.crt
     agePublicKeyFile: backup/talos-backup-age.pub
   ```

4. Apply: `./deploy-talos.py argocd -f lab.yaml`. Besides the CronJob in
   `generated/talos-backup/` and the S3 keys as Secret `talos-backup-s3`, the
   control planes grant `os:etcd:backup` to namespace `talos-backup` and admit
   the pod network to the Talos API, applied without a reboot. The first backup runs right
   away, so a wrong key, CA or permission shows at once; later runs follow
   `schedule` (every 6 hours by default).
5. Check: a file `<name>/<name>-<time>.snap.zst.age` is in the bucket.

## Take a backup now

```sh
kubectl -n talos-backup create job --from=cronjob/talos-backup manual-$(date +%s)
```

## Restore

When the cluster's etcd is lost, e.g. all control planes rebuilt:

1. Fetch a snapshot `<name>/<name>-<time>.snap.zst.age` with a credential that
   can read the bucket.
2. Decrypt and decompress it:

   ```sh
   age -d -i /path/to/talos-backup-age.key -o db.snapshot.zst <name>-<time>.snap.zst.age
   zstd -d db.snapshot.zst -o db.snapshot
   ```

3. Recover etcd on one control plane booted into maintenance/bootstrap state:

   ```sh
   talosctl -n <cp-ip> bootstrap --recover-from=./db.snapshot
   ```

Follow Talos' disaster recovery guide for the full procedure.

A snapshot of a 5-node cluster (55.7 MB) was 5.8 MB compressed and encrypted,
and restored into a valid etcd database of the original size.
