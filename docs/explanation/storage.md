# Storage

> Explanation · [Documentation](../../README.md#documentation)

How Longhorn provides persistent volumes, and what it doesn't protect
against. To add it: [Add Longhorn storage](../how-to/add-longhorn-storage.md).
Settings: [`longhorn`](../reference/cluster-file.md#longhorn-optional-section).

## Dedicated storage nodes

[Longhorn](https://longhorn.io) replicates block volumes across nodes and
serves them through its CSI driver. The script gives it storage nodes of
their own, `<name>-st-N`, rather than putting replicas on the workers, so
replica rebuilds and workload scheduling don't compete.

- Each storage node has a second, thin disk (`/dev/vdb`) that Talos formats
  and mounts at `/var/mnt/longhorn` (`UserVolumeConfig` `longhorn`). Longhorn
  only creates disks on nodes labelled `node.longhorn.io/create-default-disk=true`,
  with nothing reserved, since the disk holds nothing else.
- **No LAN NIC:** replication stays on the internal network. The nodes reach
  the internet for images through the internal network's router (libvirt's,
  or `network.gateway` on an existing bridge), and the L2 announcement policy
  excludes them, since they couldn't answer ARP on the LAN.
- **Label and taint** `deploy-talos/role=storage` (`NoSchedule`): only
  Longhorn, and DaemonSets tolerating every taint (Cilium), run there.

## Every node needs the iSCSI tools

A volume is attached over iSCSI on the node that runs the workload, so
`siderolabs/iscsi-tools` and `siderolabs/util-linux-tools` go into the image
of *every* node. A running cluster gets them by reinstalling the nodes that
lack them, with the same Talos version and the upgrade procedure; `upgrade`
does the same for any node missing an extension listed in the file.

## Longhorn's setup

- `longhorn.replicas` replicas per volume, each on a different storage node.
- The CSI plugin runs on every worker, so any pod can mount a volume.
- StorageClass `longhorn` (the default unless `defaultStorageClass: false`):
  reclaim policy `Delete`, expansion allowed, `ReadWriteOnce` and
  `ReadWriteMany` (an NFS share manager serves the latter).
- Namespace `longhorn-system` runs at the privileged Pod Security level.
- Longhorn's upgrade checker, which reports to an external server, is off.
- The UI has no authentication of its own, so it isn't routed on the gateway.

## Storage in the health gate

With Longhorn, the [health gate](architecture.md#the-health-gate) also waits
until every attached volume is `healthy`, so a storage node only goes down
(upgrade, reinstall) once the previous one's replicas are rebuilt.

**Tested** with 1 control plane, 1 worker and 3 storage nodes: RWO and RWX
volumes with a pod writing every 2 s; a storage node powered off left volumes
`degraded` with writes uninterrupted, and after its restart replicas were
rebuilt and the gate passed after 85 s; a drain, reboot and gate as `upgrade`
does it took 7 s for the drain, with volumes healthy before the gate passed.

## Limits

- **Replicas aren't backups.** They protect against losing a node, not
  against deletion or corruption: configure a backup target (S3, NFS) in
  Longhorn for that.
- **Storage nodes are never removed** by the script, and removing the section
  leaves Longhorn running: data is never deleted by accident.
- **Thin disks grow** up to `dataDiskSize` in `paths.imagesDir`; keep that much
  free per storage node. `dataDiskSize` only applies to nodes created later.
