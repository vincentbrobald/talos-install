# Move node disks

> How-to · [Documentation](../../README.md#documentation)

Put one role's node disks on another disk of the host, e.g. the control
planes on an SSD: etcd waits for every write to reach its disk, and when that
disk is a hard disk shared with busy workers (image builds), slow writes make
the API servers fail their health checks. New nodes of the role are created
there once the cluster file says so; a running cluster's nodes are moved one
at a time, without downtime.

## Prepare the directory

Root on the host. A directory on the faster disk, labelled for libvirt's VM
images (SELinux) and declared as a storage pool:

```sh
mkdir -p /var/lib/libvirt/images-ssd && chmod 711 /var/lib/libvirt/images-ssd
semanage fcontext -a -t virt_image_t "/var/lib/libvirt/images-ssd(/.*)?"
restorecon -R /var/lib/libvirt/images-ssd
virsh pool-define-as images-ssd dir --target /var/lib/libvirt/images-ssd
virsh pool-start images-ssd && virsh pool-autostart images-ssd
```

## Name it in the cluster file

```yaml
paths:
  imagesDir: /var/lib/libvirt/images
  controlPlaneImagesDir: /var/lib/libvirt/images-ssd   # or workerImagesDir, storageImagesDir
```

`create`, `scale` and `destroy` use it from now on: a node's disk and config
ISO (and a storage node's data disk) live in its role's directory.

## Move a running node

One node at a time. For control planes, check etcd before each one (every
member answers, all name the same leader) and move last the one holding the
API's virtual IP, whose move interrupts the API for a few seconds:

```sh
talosctl -n <cp1-ip>,<cp2-ip>,<cp3-ip> etcd status
talosctl -n <ip> get addresses | grep <vip>      # who holds the VIP
```

Then, with `old=/var/lib/libvirt/images`, `new=/var/lib/libvirt/images-ssd`
and the node's name and address:

1. `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`
2. `talosctl -n <ip> shutdown`, then wait until `virsh domstate <node>` says
   `shut off`.
3. Copy the disk and the config ISO (sparse, keeping owner and mode) and
   check the copies:

   ```sh
   cp --sparse=always --preserve=mode,ownership $old/<node>.qcow2 $old/<node>-cidata.iso $new/
   restorecon $new/<node>.qcow2 $new/<node>-cidata.iso
   qemu-img compare $old/<node>.qcow2 $new/<node>.qcow2 && cmp $old/<node>-cidata.iso $new/<node>-cidata.iso
   ```

   A storage node's `<node>-data.qcow2` goes the same way (target `vdb`).
4. Point the VM at the copies and start it:

   ```sh
   virt-xml <node> --edit target=vda --disk path=$new/<node>.qcow2
   virt-xml <node> --edit target=sda --disk path=$new/<node>-cidata.iso
   virsh domblklist <node>
   virsh start <node>
   ```

5. Wait until the node is `Ready` again (for a control plane: `etcd status`
   shows all members, one leader), then `kubectl uncordon <node>`.
6. Remove the old files: `rm $old/<node>.qcow2 $old/<node>-cidata.iso`.

Until step 6, going back is `virt-xml` with the old paths.
