# Keep Secrets in Git

> How-to · [Documentation](../../README.md#documentation)

Store the add-ons' Secrets in the repository, encrypted with SOPS, and edit
them. How it works: [GitOps and add-ons](../explanation/gitops.md#secrets-in-git).
Which Secrets: [Repository files](../reference/repository-files.md#secrets-in-git-sops-mode).
Needs [the add-ons in Git](manage-addons-in-git.md).

## Turn it on

1. Choose where the cluster's age key lives (created if missing), and add your
   own public key so you can decrypt from your machine:

   ```yaml
   argocd:
     addons:
       enabled: true
       pushSshKeyFile: forgejo/gitops-push_key
       sopsAgeKeyFile: sops/lab.agekey
       sopsRecipients: [age1...]
   ```

2. Apply: `./deploy-talos.py argocd -f lab.yaml`.
3. Check: `generated/<topic>/secret-*.enc.yaml` files appear in the
   repository, and the Applications are Synced and Healthy (Argo CD decrypts
   them).

Keep a copy of your age key off the host: losing every key that can decrypt
means re-creating the Secrets.

## Edit an encrypted Secret

From inside the cluster's folder in the repository (its generated
`.sops.yaml` lists the recipients):

```sh
SOPS_AGE_KEY_FILE=~/.config/sops/age/me.key sops edit generated/monitoring/secret-monitoring-grafana-admin.enc.yaml
```

`sops edit` decrypts into your editor and re-encrypts on save. Commit and
push; Argo CD applies it.

## Replace a generated Secret

Delete its file from the repository and run `./deploy-talos.py argocd -f
lab.yaml`: the script writes it again from its origin. A client secret then
comes from Keycloak (with `oidc.crossplane`, a new random one that Crossplane
sets in Keycloak), the S3 keys from the `talosBackup.s3` files, Grafana's
admin password from the cluster.

## Add your own encrypted Secrets

Put them next to the manifests that use them, encrypted with
`sops encrypt -i new.enc.yaml`, and list them in a KSOPS generator in that
folder's kustomization. Not under `generated/`: the script owns it.
