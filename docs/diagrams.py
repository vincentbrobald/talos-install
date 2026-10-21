#!/usr/bin/env python3
import sys
from pathlib import Path
from xml.sax.saxutils import escape

C = {
    "bg": "#ffffff", "ink": "#1f2933", "muted": "#52606d", "line": "#7b8794",
    "host": "#f5f7fa", "hostb": "#9aa5b1",
    "net": "#e8f1fb", "netb": "#4a7fc1",
    "lan": "#fdf5e6", "lanb": "#c98a1c",
    "cp": "#fde8e1", "cpb": "#c4572e",
    "wk": "#e3f4e8", "wkb": "#2f8a4c",
    "vip": "#f1e8fb", "vipb": "#7a4fb5",
    "ext": "#eef0f2", "extb": "#7b8794",
    "tool": "#ffffff", "toolb": "#52606d",
}
FONT = "font-family=\"-apple-system,'Segoe UI',Helvetica,Arial,sans-serif\""


class Svg:
    def __init__(self, w, h, title, desc):
        self.w, self.h = w, h
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t d" {FONT} font-size="13">',
            f"<title id=\"t\">{escape(title)}</title>",
            f"<desc id=\"d\">{escape(desc)}</desc>",
            "<defs><marker id=\"a\" viewBox=\"0 0 10 10\" refX=\"9\" refY=\"5\" markerWidth=\"7\" markerHeight=\"7\" "
            f"orient=\"auto-start-reverse\"><path d=\"M0,0 L10,5 L0,10 z\" fill=\"{C['line']}\"/></marker></defs>",
            f'<rect width="{w}" height="{h}" fill="{C["bg"]}"/>',
        ]

    def box(self, x, y, w, h, kind, lines=(), title=None, dashed=False, rx=8, align="middle", size=13):
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{C[kind]}" '
                          f'stroke="{C[kind + "b"]}" stroke-width="1.5"{dash}/>')
        if title:
            self.text(x + 12, y + 20, title, bold=True, anchor="start", color=C[kind + "b"])
        if lines:
            n = len(lines)
            lh = size + 4
            top = y + h / 2 - (n - 1) * lh / 2 + size * 0.35
            tx = x + w / 2 if align == "middle" else x + 12
            for i, ln in enumerate(lines):
                bold = i == 0 and not title
                self.text(tx, top + i * lh, ln, bold=bold, anchor=align, size=size if i == 0 else size - 1,
                          color=C["ink"] if i == 0 else C["muted"])

    def text(self, x, y, s, bold=False, anchor="start", size=13, color=None, italic=False):
        self.parts.append(f'<text x="{x}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" '
                          f'fill="{color or C["ink"]}"{" font-weight=\"600\"" if bold else ""}'
                          f'{" font-style=\"italic\"" if italic else ""}>{escape(s)}</text>')

    def line(self, pts, arrow_end=True, arrow_start=False, dashed=False, color=None, label=None, lx=None, ly=None,
             anchor="middle"):
        d = " ".join(f"{'M' if i == 0 else 'L'}{x},{y}" for i, (x, y) in enumerate(pts))
        attrs = ""
        if arrow_end:
            attrs += ' marker-end="url(#a)"'
        if arrow_start:
            attrs += ' marker-start="url(#a)"'
        if dashed:
            attrs += ' stroke-dasharray="5 4"'
        self.parts.append(f'<path d="{d}" fill="none" stroke="{color or C["line"]}" stroke-width="1.6"{attrs}/>')
        if label:
            self.label(lx, ly, label, anchor)

    def label(self, x, y, s, anchor="middle", size=12):
        w = len(s) * size * 0.56 + 10
        x0 = {"middle": x - w / 2, "start": x - 5, "end": x - w + 5}[anchor]
        self.parts.append(f'<rect x="{x0:.1f}" y="{y - size - 1}" width="{w:.1f}" height="{size + 7}" rx="3" '
                          f'fill="{C["bg"]}" fill-opacity="0.92"/>')
        self.text(x, y + 1, s, anchor=anchor, size=size, color=C["muted"])

    def legend(self, x, y, items):
        for i, (kind, s, dashed) in enumerate(items):
            xx = x + i * 150
            dash = ' stroke-dasharray="4 3"' if dashed else ""
            self.parts.append(f'<rect x="{xx}" y="{y - 11}" width="16" height="12" rx="3" fill="{C[kind]}" '
                              f'stroke="{C[kind + "b"]}" stroke-width="1.3"{dash}/>')
            self.text(xx + 22, y, s, size=12, color=C["muted"])

    def save(self, path):
        self.parts.append("</svg>")
        Path(path).write_text("\n".join(self.parts) + "\n")


LEGEND = [("cp", "control plane", False), ("wk", "worker", False), ("vip", "virtual IP", True),
          ("net", "network", False), ("ext", "outside the host", False)]


def talos_private(out):
    s = Svg(900, 680, "Talos: private network topology",
            "Nodes on a libvirt NAT network created for the cluster; only the host reaches them.")
    s.text(20, 32, "Talos — private network (default)", bold=True, size=18)
    s.text(20, 52, "Only this host reaches the cluster. Addresses for network.prefix 10.44.0 (the default).",
           size=12, color=C["muted"])
    s.box(600, 14, 280, 50, "ext", ["Internet", "Image Factory, GitHub, registries"])
    s.box(20, 80, 860, 560, "host", title="KVM host (libvirt, qemu:///system)")
    s.box(40, 112, 320, 70, "tool", ["deploy-talos.py, kubectl, talosctl",
                                     "<name>-cluster/: kubeconfig, talosconfig"])
    s.box(40, 250, 820, 370, "net", title="libvirt NAT network talos-<name>  ·  10.44.0.0/24")
    s.box(600, 280, 240, 62, "net", [".1  virbrN on the host", "gateway (NAT), DHCP, DNS"])
    s.line([(720, 280), (720, 64)], label="NAT", lx=720, ly=100)
    s.box(330, 280, 240, 62, "vip", [".10  API VIP :6443", "3+ control planes; else cp-1"], dashed=True)
    s.line([(340, 182), (450, 280)], label="kubectl", lx=395, ly=222)
    s.line([(110, 182), (110, 250)], label="talosctl :50000, all nodes", lx=110, ly=222)
    for i, ip in enumerate((11, 12, 13)):
        x = 60 + i * 270
        s.box(x, 380, 240, 84, "cp", [f"cp-{i + 1}   .{ip}", "etcd, API server, scheduler", "Talos API :50000"])
        s.line([(450, 342), (x + 120, 380)], arrow_end=True, dashed=True)
    for i, ip in enumerate((21, 22)):
        x = 60 + i * 270
        s.box(x, 500, 240, 84, "wk", [f"w-{i + 1}   .{ip}", "kubelet, workloads", "pod network: flannel"])
    s.box(600, 500, 240, 84, "wk", ["w-3 … w-79", ".23 – .99", "added by scale"], dashed=True)
    s.text(450, 612, ".100–.199: DHCP pool, unused by the cluster  ·  existingBridge: same layout, "
                     "static addresses, your router on .1", anchor="middle", size=12, color=C["muted"])
    s.legend(40, 666, LEGEND)
    s.save(out)


def talos_lan(out):
    s = Svg(900, 780, "Talos: LAN mode topology",
            "Each node has a private NIC for cluster traffic and a LAN NIC; API VIP, Gateway and "
            "LoadBalancer addresses come from lan.range.")
    s.text(20, 32, "Talos — LAN mode (lan section)", bold=True, size=18)
    s.text(20, 52, "Example: lan.range 192.0.2.200-229, 3 control planes + 2 workers.", size=12, color=C["muted"])
    s.box(20, 70, 860, 200, "lan", title="LAN  ·  lan.bridge (e.g. bridge0)  ·  192.0.2.0/24")
    s.box(40, 104, 240, 62, "ext", ["Router .1", "default gateway, DNS"])
    s.box(300, 104, 260, 62, "ext", ["LAN clients", "kubectl, browsers, Argo CD UI"])
    s.box(580, 104, 280, 62, "ext", ["DNS (dns-records)", "api.<name>: .200, *.apps: .204"])
    s.text(40, 194, "lan.range", bold=True, size=12, color=C["lanb"])
    segs = [(120, "vip", ".200", "API VIP"), (180, "cp", ".201–.203", "control planes"),
            (370, "vip", ".204–.227", "LoadBalancer pool (.204 = ingress gateway)"),
            (150, "wk", ".228–.229", "workers")]
    x = 40
    for w, kind, a, b in segs:
        s.box(x, 202, w, 52, kind, [a, b], dashed=kind == "vip", rx=4, size=12)
        x += w
    s.box(20, 300, 860, 440, "host", title="KVM host")
    s.box(40, 660, 400, 58, "tool", ["deploy-talos.py, talosctl",
                                     "Talos API only from the private network"])
    s.box(460, 660, 400, 58, "tool", ["Cilium (replaces flannel and kube-proxy)",
                                      "Gateway API, L2 announcements (ARP on eth1)"])
    s.line([(240, 660), (240, 630)])
    nodes = [("cp", "cp-1", ".201", ".11"), ("cp", "cp-2", ".202", ".12"), ("cp", "cp-3", ".203", ".13"),
             ("wk", "w-1", ".229", ".21"), ("wk", "w-2", ".228", ".22")]
    for i, (kind, n, lan, priv) in enumerate(nodes):
        x = 40 + i * 166
        s.line([(x + 75, 362), (x + 75, 270)], arrow_end=False, color=C["lanb"])
        s.line([(x + 75, 454), (x + 75, 500)], arrow_end=False, color=C["netb"])
        s.box(x, 362, 150, 92, kind, [n, f"eth1  {lan}  (LAN)", f"eth0  {priv}  (private)"])
    s.label(450, 340, "eth1 bridged to the LAN: API VIP, Gateways, LoadBalancer IPs, default route")
    s.box(40, 500, 820, 130, "net", title="private network  ·  created NAT network or existingBridge  ·  10.44.0.0/24")
    s.text(60, 550, "Cluster traffic stays here: etcd, kubelet, pod network, Talos API.", size=13)
    s.text(60, 572, "Node services (Talos API 50000, trustd 50001, kubelet 10250, etcd 2379-2380) are firewalled",
           size=12, color=C["muted"])
    s.text(60, 590, "to this network. IPv6 is disabled on eth1. The API VIP moves between control planes (~30 s).",
           size=12, color=C["muted"])
    s.text(60, 610, ".1: gateway (NAT), DHCP, DNS for a created network.", size=12, color=C["muted"])
    s.legend(40, 766, LEGEND[:4] + [("lan", "LAN", False)])
    s.save(out)


def integrations(out):
    title = "Talos"
    s = Svg(900, 600, f"{title}: integrations",
            "How a cluster uses Keycloak, a Git server and the LAN DNS, and what the deploy script configures.")
    s.text(20, 32, f"{title} — Argo CD, Keycloak and DNS", bold=True, size=18)
    s.text(20, 52, "Optional sections argocd and oidc; dns-records in LAN mode.",
           size=12, color=C["muted"])
    script = "deploy-talos.py"
    s.box(20, 80, 270, 90, "tool", [script, "plan, create, argocd, oidc", "dns-records; kubeconfig"])
    s.box(20, 250, 220, 96, "ext", ["LAN DNS (e.g. OPNsense)", "Dnsmasq host entries",
                                    "owner deploy-*.py:<name>"])
    s.line([(100, 170), (100, 250)], label="registration tool", lx=105, ly=214, anchor="start")
    s.box(320, 80, 560, 330, "net", title="cluster")
    s.box(340, 112, 250, 84, "cp", ["kube-apiserver", "OIDC tokens, audience k8s-<name>",
                                    "groups prefixed oidc:"])
    s.box(610, 112, 250, 84, "wk", ["Argo CD (Helm chart)", "namespace argocd",
                                    "SSO client argocd-<name>"])
    s.box(610, 214, 250, 70, "vip", ["ingress gateway (LAN mode)", "argocd.hostname, *.apps"], dashed=True)
    s.box(340, 214, 250, 70, "cp", ["oidc-cluster-admins", "admin groups get cluster-admin"])
    s.box(340, 302, 220, 84, "wk", ["root Application", "syncs repository.path",
                                    "automated, prune, self-heal"])
    s.line([(290, 150), (340, 150)])
    s.box(20, 450, 270, 110, "ext", ["Keycloak", "realm, groups, clients",
                                     "users log in here", "OIDC issuer for cluster and Argo CD"])
    s.line([(265, 170), (265, 450)], label="admin API", lx=265, ly=400)
    s.line([(320, 395), (282, 450)], dashed=True)
    s.box(330, 450, 240, 110, "ext", ["Git server (e.g. Forgejo)", "repository, revision, path",
                                      "read-only deploy key or token", "polled every 3 min"])
    s.line([(450, 386), (450, 450)], label="git (SSH / HTTPS)", lx=500, ly=426, anchor="start")
    s.box(610, 450, 270, 110, "ext", ["Users", "browser: console, Argo CD",
                                      "kubectl: Keycloak login", "by name, via LAN DNS"])
    s.line([(745, 450), (745, 284)], label="HTTPS", lx=745, ly=372)
    s.text(450, 588, "Dashed: the cluster fetches Keycloak's discovery document and keys; "
                     "after login, Keycloak redirects back to the cluster.", anchor="middle", size=12,
           color=C["muted"])
    s.save(out)


if __name__ == "__main__":
    t = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
    t.mkdir(parents=True, exist_ok=True)
    talos_private(t / "topology-private.svg")
    talos_lan(t / "topology-lan.svg")
    integrations(t / "integrations.svg")
