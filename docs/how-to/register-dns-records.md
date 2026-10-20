# Register DNS records

> How-to · [Documentation](../../README.md#documentation)

Give a LAN-mode cluster names in the LAN's DNS. Clusters without a `lan`
section are refused: their addresses are private to the host.

1. Print the records:

   ```sh
   ./deploy-talos.py dns-records -f lab.yaml --domain example.org --format text
   ```

   | Name | Address |
   |---|---|
   | `api.<name>.<domain>` | the API VIP (first address of `lan.range`) |
   | `*.apps.<name>.<domain>` | the ingress gateway, read from the running cluster |
   | `argocd.hostname` | the gateway, only if outside that wildcard |

2. Register them. Without `--format text` the output is JSON for a
   registration tool that writes them to your DNS server, e.g. as host
   entries on the router:

   ```sh
   ./deploy-talos.py dns-records -f lab.yaml --domain example.org | your-dns-tool sync
   ```

3. Check: `dig +short api.lab.example.org` and
   `dig +short anything.apps.lab.example.org` answer the VIP and the gateway.

After `destroy`, remove them with your tool, e.g.:

```sh
your-dns-tool remove --owner deploy-talos.py:lab
```

The kubeconfig keeps using the VIP's address; the API name is for people and
tools that prefer names (the Talos API certificate doesn't list it).
