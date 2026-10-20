# Requirements

> Reference · [Documentation](../../README.md#documentation)

What the host needs before `deploy-talos.py` can build a cluster. `plan`
checks most of it ([commands](commands.md#plan)); the host setup that makes
clusters survive a reboot is in [Prepare the host](../how-to/prepare-the-host.md).

## Host

| Requirement | Detail |
|---|---|
| CPU architecture | x86_64 (`amd64` images and binaries only) |
| Virtualization | KVM (`/dev/kvm`), libvirt with `qemu:///system` access; run as root |
| libvirt daemons | started at boot, networks first (see [Prepare the host](../how-to/prepare-the-host.md)) |
| Commands | `virsh`, `virt-install`, `qemu-img`, `xorriso`, `ip`, `ping` |
| Python | 3.9 or later, with PyYAML and Jinja2 (`python3-pyyaml`, `python3-jinja2` on Fedora/RHEL/AlmaLinux) |
| Templates | `templates/` next to `deploy-talos.py` (Jinja2 sources of the `plan` output and of `template`) |
| Resources | the `minimal` preset needs about 12 GiB RAM and 10 GB disk |

`talosctl`, `kubectl` and `helm` are downloaded on first use, checksum-verified,
into the cache directory ([`paths.cacheDir`](cluster-file.md#paths)). Nothing is
installed system-wide.

## Network access

| From the host to | For |
|---|---|
| `github.com`, `factory.talos.dev`, `dl.k8s.io` | `talosctl`, the node image, `kubectl` |
| `get.helm.sh` | LAN mode or Argo CD |
| `helm.cilium.io` | LAN mode |
| `argoproj.github.io` | Argo CD |
| the container registries the cluster pulls from | node images (or a [registry mirror](../how-to/use-a-registry-mirror.md)) |

## With an `argocd` section

| Requirement | Detail |
|---|---|
| Commands | `git`; for SSH repositories also `ssh-keyscan` and `ssh-keygen` |
| Git server | reachable from the cluster nodes, and from the host unless `argocd.repository.checkFromHost: false` |

## In LAN mode (a `lan` section)

| Requirement | Detail |
|---|---|
| Host bridge | an existing Linux bridge connected to the LAN, e.g. `br0` (`ip -br link show type bridge`) |
| Addresses | a block of unused LAN addresses outside the router's DHCP pool ([address plan](address-plan.md)) |
