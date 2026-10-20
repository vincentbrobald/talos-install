# Add Longhorn storage

> How-to · [Documentation](../../README.md#documentation)

Give the cluster replicated persistent volumes on dedicated storage nodes.
How it works and its limits: [Storage](../explanation/storage.md). Settings:
[`longhorn`](../reference/cluster-file.md#longhorn-optional-section).

## Add it

1. Make sure every node runs `talos.version` (finish a pending
   [Talos upgrade](upgrade-talos.md)), and the host has room for the data
   disks: `nodes.count` × `dataDiskSize` in `paths.imagesDir`.
2. Add the section. On an existing bridge, storage nodes need
   `network.gateway` to reach the internet (they have no LAN NIC):

   ```yaml
   network:
     gateway: 192.168.122.1
   longhorn:
     nodes:
       count: 3
       dataDiskSize: 50G
   ```

3. Apply (part of `create` on a new cluster):

   ```sh
   ./deploy-talos.py longhorn -f lab.yaml
   ```

   Nodes without the iSCSI extensions are reinstalled first, one at a time;
   it asks before (`-y` skips the question).

4. Check:

   ```sh
   kubectl get nodes -l deploy-talos/role=storage
   kubectl -n longhorn-system get nodes.longhorn.io
   kubectl get storageclass longhorn
   ```

## Use a volume

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data
spec:
  accessModes: [ReadWriteOnce]      # or ReadWriteMany
  resources:
    requests:
      storage: 5Gi
```

With `defaultStorageClass: true` (default), claims without a class get
Longhorn.

## Open the Longhorn UI

The UI has no login, so it isn't on the gateway:

```sh
kubectl -n longhorn-system port-forward svc/longhorn-frontend 8081:80   # http://localhost:8081
kubectl -n longhorn-system get volumes.longhorn.io
```

## Add storage nodes

Raise `longhorn.nodes.count` and run `longhorn` again. New nodes get the
current `dataDiskSize`; existing disks aren't resized.

## Remove a storage node

The script never removes one. In the Longhorn UI, disable scheduling on the
node and request eviction; when its replicas have moved, delete the VM
(`virsh destroy`, `virsh undefine`, its disks) and the Kubernetes node, then
lower `nodes.count`.

## Back up volumes

Replicas don't protect against deletion or corruption: configure a backup
target (S3, NFS) in Longhorn's settings.
