# Prepare the host

> How-to · [Documentation](../../README.md#documentation)

Make clusters come back by themselves after the host reboots. What the host
needs in general: [Requirements](../reference/requirements.md).

The VMs and the created networks are set to autostart, but that only works if
libvirt's daemons start at boot, networks first. With the modular daemons
(`virtqemud`, `virtnetworkd`, e.g. AlmaLinux 10) the network daemon is only
socket-activated, so `virbr0` is missing at boot.

1. Start both daemons at boot, the network one first:

   ```sh
   systemctl enable virtqemud.service virtnetworkd.service
   mkdir -p /etc/systemd/system/virtqemud.service.d
   printf '[Unit]\nWants=virtnetworkd.service\nAfter=virtnetworkd.service\n' \
       > /etc/systemd/system/virtqemud.service.d/10-networks-first.conf
   systemctl daemon-reload
   ```

2. Check:

   ```sh
   systemctl is-enabled virtqemud virtnetworkd   # enabled, enabled
   virsh net-list --autostart                    # the clusters' networks
   ```

After the next reboot, `virsh list` shows the cluster's VMs running and
`kubectl get nodes` shows them Ready within a few minutes.
