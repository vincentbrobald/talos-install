# Getting started

> Tutorial · [Documentation](../../README.md#documentation)

In this tutorial you build a Kubernetes cluster on this host, run an
application on it, then move to a cluster on your LAN that deploys from Git
and lets people log in with Keycloak. Each part ends with a working result;
parts 1 and 2 need nothing but this host.

You need a Linux host with KVM and libvirt, and root access. Run every command
as root, from the directory that holds `deploy-talos.py`.

## 1. Check the host

```sh
ls -l /dev/kvm && virsh -c qemu:///system list --all
python3 -c 'import yaml, jinja2' && echo PyYAML and Jinja2 ok
free -g; df -h /var/lib/libvirt/images
```

You should see `/dev/kvm`, an (empty) list of VMs, `PyYAML and Jinja2 ok`,
and at least 12 GiB of free memory and 10 GB of disk. If a command is
missing, install what [Requirements](../reference/requirements.md) lists.
`talosctl`, `kubectl` and `helm` come later by themselves.

## 2. Build your first cluster

Write a cluster file from the `minimal` preset (one control plane, two
workers), check it, and build it:

```sh
./deploy-talos.py template --preset minimal -o dev.yaml
./deploy-talos.py plan -f dev.yaml
./deploy-talos.py create -f dev.yaml
```

`plan` prints the settings and the address of every node and changes nothing.
`create` takes a few minutes the first time (it downloads the node image and
the tools) and ends with the commands to use the cluster. Use them:

```sh
export KUBECONFIG=$PWD/dev-cluster/kubeconfig
export TALOSCONFIG=$PWD/dev-cluster/talosconfig
export PATH=~/.cache/talos/v1.14.2:$PATH
kubectl get nodes -o wide
```

You should see three nodes, `dev-cp-1`, `dev-w-1` and `dev-w-2`, all `Ready`.

## 3. Run an application

```sh
kubectl create deployment hello --image=docker.io/nginxinc/nginx-unprivileged:stable-alpine
kubectl rollout status deployment/hello
kubectl port-forward deployment/hello 8080:8080 &
curl -s localhost:8080 | grep title
kill %1
```

You should see `<title>Welcome to nginx!</title>`. You have a working
cluster, private to this host. Remove it:

```sh
./deploy-talos.py destroy -f dev.yaml
```

It asks for confirmation. The directory `dev-cluster/` stays: it holds the
cluster's secrets, and a new `create` would reuse them.

## 4. Put a cluster on the LAN

Now a cluster other machines can reach. You need the host bridge that
connects VMs to your LAN (`ip -br link show type bridge`) and a block of
about 30 unused LAN addresses outside your router's DHCP pool. This tutorial
uses `bridge0`, `192.0.2.200-229` and the domain `example.org`; use yours.

```sh
./deploy-talos.py template --preset lan-ha --name lab --lan-bridge bridge0 \
    --lan-range 192.0.2.200-229 --domain example.org -o lab.yaml
./deploy-talos.py plan -f lab.yaml
./deploy-talos.py create -f lab.yaml
```

`plan` also checks that nothing on the LAN answers on those addresses.
`create` prints the API address (`.200`) and the ingress gateway's address.
You should see five nodes `Ready` with `kubectl get nodes` (use
`lab-cluster/kubeconfig` now).

Give the cluster names in your LAN's DNS. Print them first:

```sh
./deploy-talos.py dns-records -f lab.yaml --domain example.org --format text
```

You should see `api.lab.example.org` and `*.apps.lab.example.org`. Register
them in your DNS server ([how](../how-to/register-dns-records.md)).

Then publish the nginx application from step 3 on
`hello.apps.lab.example.org`, through the ingress gateway:

```sh
kubectl create deployment hello --image=docker.io/nginxinc/nginx-unprivileged:stable-alpine
kubectl expose deployment hello --port=80 --target-port=8080
kubectl apply -f - <<'YAML'
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata: {name: hello, namespace: default}
spec:
  parentRefs: [{name: ingress, namespace: ingress, sectionName: http}]
  hostnames: [hello.apps.lab.example.org]
  rules: [{backendRefs: [{name: hello, port: 80}]}]
YAML
curl -s http://hello.apps.lab.example.org | grep title
```

You should see the nginx title again, this time from any machine on the LAN.

## 5. Deploy from Git

From now on the cluster will apply what is in a Git repository. You need a
repository the cluster can reach and a read-only deploy key for it. Add an
`argocd` section to `lab.yaml` (the file has a commented one):

```yaml
argocd:
  hostname: argocd.apps.lab.example.org
  repository:
    url: ssh://git@git.example.org:2222/platform/gitops.git
    revision: main
    path: clusters/lab
    auth: {method: ssh, sshKeyFile: keys/lab-deploy-key, knownHosts: auto}
```

```sh
./deploy-talos.py plan -f lab.yaml
./deploy-talos.py argocd -f lab.yaml
```

`plan` reads the repository with that key from this host, so a wrong key fails
here. `argocd` installs Argo CD and prints the UI address and the admin
password. You should see the Application `root` Synced and Healthy in the UI
at `https://argocd.apps.lab.example.org`.

Commit a manifest under `clusters/lab` and push it: within about three minutes
it appears in the cluster.

## 6. Log in with Keycloak

Last, people log in with their own accounts instead of the admin kubeconfig.
You need a Keycloak and its admin password in a file. Add an `oidc` section:

```yaml
oidc:
  issuer: https://oauth.example.org/realms/example
  caFile: /path/to/root_ca.crt
  keycloakAdminPasswordFile: /path/to/keycloak-admin-password
  kubernetes: {adminGroups: [k8s-admins]}
  argocd: {adminGroups: [argocd-admins]}
```

```sh
./deploy-talos.py oidc -f lab.yaml
./deploy-talos.py argocd -f lab.yaml
```

`oidc` creates the realm, groups and clients in Keycloak and restarts the API
servers one at a time. In Keycloak, put your user into `k8s-admins` and
`argocd-admins`, then:

```sh
KUBECONFIG=lab-cluster/kubeconfig-oidc kubectl get nodes
```

You should see a login URL and a code. Open the URL, log in, and the node list
follows. Argo CD's login page now shows "Log in via Keycloak".

## What you built

A highly available cluster on your LAN, reachable by name, deploying from Git,
with single sign-on for `kubectl` and Argo CD.

## Next steps

- Practise the day-to-day changes on a throwaway cluster:
  [Change a running cluster](change-a-running-cluster.md).
- Day-to-day tasks: [scale workers](../how-to/scale-workers.md),
  [upgrade Talos](../how-to/upgrade-talos.md),
  [upgrade Kubernetes](../how-to/upgrade-kubernetes.md).
- More from Git: [manage the add-ons in Git](../how-to/manage-addons-in-git.md),
  [keep Secrets in Git](../how-to/keep-secrets-in-git.md).
- HTTPS, a web console, storage: [Serve HTTPS and Headlamp](../how-to/serve-https-and-headlamp.md),
  [Add Longhorn storage](../how-to/add-longhorn-storage.md).
- Every setting: [Cluster file](../reference/cluster-file.md).
- How it fits together: [Architecture](../explanation/architecture.md).
