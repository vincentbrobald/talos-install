# Use a registry mirror

> How-to · [Documentation](../../README.md#documentation)

Make every node pull its images through a mirror registry, falling back to the
upstream when the mirror fails. Settings:
[`registry`](../reference/cluster-file.md#registry-optional-section).

1. Prepare the mirror. It must serve each upstream under its own namespace,
   `<mirror>/docker.io/library/nginx`: in Harbor, one proxy-cache project per
   upstream named after it (`docker.io`, `registry.k8s.io`, ...); in zot,
   on-demand sync with its `docker2s2` compatibility (many images still use
   Docker manifest types).
2. Add the section:

   ```yaml
   registry:
     mirror: https://registry.example.com
     caFile: pki/root_ca.crt          # if the mirror uses a private CA
   ```

3. Apply: new clusters get it at `create`; a running cluster without a reboot:

   ```sh
   ./deploy-talos.py node-config -f lab.yaml   # argocd runs the same step
   ```

4. Check: start a pod with an image the nodes don't have yet, and see the pull
   in the mirror's logs or cache.

Each upstream gets a `RegistryMirrorConfig` pointing containerd at its
namespace on the mirror with `overridePath` (`docker.io/library/nginx` comes
from `https://registry.example.com/v2/docker.io/library/nginx/...`), and the
CA a `RegistryTLSConfig`.

Images pulled before the mirror existed stay in each node's cache; only new
pulls go through it.

## Change which upstreams go through it

Edit `registry.registries` (default: `docker.io`, `ghcr.io`, `quay.io`,
`registry.k8s.io`, `gcr.io`, `factory.talos.dev`) and run `node-config`. Nodes
change live.
