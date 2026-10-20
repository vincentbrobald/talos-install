# Set up GitOps with Argo CD

> How-to · [Documentation](../../README.md#documentation)

Make a cluster apply a Git repository, or change its repository or
credentials. How it works: [GitOps and add-ons](../explanation/gitops.md).
Settings: [`argocd`](../reference/cluster-file.md#argocd-optional-section).

## Connect a repository

1. Create a credential that can only **read** the repository:

   | Git server | Credential |
   |---|---|
   | Forgejo / Gitea | a read-only deploy key, or a token with scope `read:repository` |
   | GitHub | a deploy key, or a fine-grained token with *Contents: read* |

   Put it in a file (an SSH key without passphrase, or the token alone).

2. Add the section, with the auth method that fits the URL:

   | Method | URL | Example |
   |---|---|---|
   | `none` | `https://` | `{method: none}` (public repositories) |
   | `ssh` | `ssh://` or `user@host:path` | `{method: ssh, sshKeyFile: keys/deploy}` |
   | `basic` | `http(s)://` | `{method: basic, username: argocd, passwordFile: secrets/pw}` |
   | `token` | `http(s)://` | `{method: token, tokenFile: keys/git-token}` |

   ```yaml
   argocd:
     hostname: argocd.apps.lab.example.com   # LAN mode: the UI on the gateway
     repository:
       url: ssh://git@git.example.com:2222/platform/gitops.git
       revision: main
       path: clusters/lab
       recurse: true                          # plain YAML in subdirectories
       auth:
         method: ssh
         sshKeyFile: keys/lab-deploy-key
         knownHosts: keys/known_hosts         # or auto
   ```

3. Check access from the host, then apply. A new cluster does it as part of
   `create`:

   ```sh
   ./deploy-talos.py plan -f lab.yaml
   ./deploy-talos.py argocd -f lab.yaml
   ```

4. Check: the command ends with the root Application Synced and Healthy, and
   prints how to reach the UI.

## Rotate a credential or switch repository

Change the file the key points at, or the `repository` settings (URL,
revision, path, auth method), and run `./deploy-talos.py argocd -f lab.yaml`
again. The old credential is removed from the cluster. A failing check stops
before anything in the cluster changes.

## Reach the UI

| Setup | Address |
|---|---|
| `hostname`, LAN mode | `https://<hostname>`: TLS passed through to Argo CD's self-signed certificate, or with `certManager` terminated by the gateway with your CA's certificate (the `argocd` CLI then needs `--grpc-web`) |
| no `hostname` | `kubectl -n argocd port-forward svc/argocd-server 8080:443`, then `https://localhost:8080` (with `certManager`: `8080:80` and `http://`) |

The name must resolve to the [ingress gateway](../reference/ingress-gateway.md)
or a load balancer in front of it. The admin password:

```sh
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
```

## Next

- Let Argo CD manage the add-ons as well: [Manage the add-ons in Git](manage-addons-in-git.md).
- Log in with Keycloak instead of `admin`: [Add Keycloak login](add-keycloak-login.md).
