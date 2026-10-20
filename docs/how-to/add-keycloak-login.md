# Add Keycloak login

> How-to · [Documentation](../../README.md#documentation)

Let people log in to `kubectl` and Argo CD with their Keycloak accounts. How
it works: [Authentication](../explanation/authentication.md). Settings:
[`oidc`](../reference/cluster-file.md#oidc-optional-section).

## With the script managing Keycloak

1. Put the Keycloak admin password in a file, and add the section:

   ```yaml
   oidc:
     issuer: https://oauth.example.com/realms/example
     caFile: /path/to/issuer-root-ca.crt          # if Keycloak uses a private CA
     keycloakAdminPasswordFile: oauth/keycloak-admin-password
     kubernetes: {adminGroups: [k8s-admins]}
     argocd: {adminGroups: [argocd-admins]}
   ```

2. Apply to the API servers (one control plane at a time, each confirmed;
   `-y` skips the questions), then to Argo CD:

   ```sh
   ./deploy-talos.py oidc -f lab.yaml
   ./deploy-talos.py argocd -f lab.yaml
   ```

   A new cluster gets both during `create`.

3. In Keycloak, put people into the admin groups.

4. Check:

   ```sh
   KUBECONFIG=lab-cluster/kubeconfig-oidc kubectl get nodes
   ```

   It prints a URL and a code the first time; log in in any browser and the
   node list follows. Argo CD shows "Log in via Keycloak".

## With clients that already exist

Without `keycloakAdminPasswordFile`, create the clients yourself
(`k8s-<name>`, `argocd-<name>`, ...; their shape is in
[Authentication](../explanation/authentication.md#keycloak-managed-by-the-script)),
put each confidential client's secret in a file, and name the files:

```yaml
oidc:
  issuer: https://login.example.com/realms/example
  argocd: {clientSecretFile: oidc/argocd-client-secret}
```

## Give other people rights

The admin groups get `cluster-admin`. For anyone else, bind their prefixed
group:

```sh
kubectl create rolebinding team-a-edit -n team-a --clusterrole=edit --group=oidc:team-a
```

## Put Headlamp's and Grafana's clients under Crossplane

With Crossplane and provider-keycloak in the cluster and
[Secrets in Git](keep-secrets-in-git.md):

1. Take the existing clients over without changes first:

   ```yaml
   oidc:
     crossplane: {enabled: true, observeOnly: true}
   ```

   Run `./deploy-talos.py argocd -f lab.yaml`, then compare each object's
   `status.atProvider` with Keycloak.
2. Remove `observeOnly` and run `argocd` again: Crossplane now manages them.

To hand them back to the script, set `crossplane.enabled: false` and run
`argocd`: the objects leave the repository and Keycloak keeps the clients.
