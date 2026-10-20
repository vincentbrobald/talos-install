# Serve HTTPS and Headlamp

> How-to · [Documentation](../../README.md#documentation)

Serve the cluster's UIs over HTTPS with certificates from your ACME CA, and
add the Headlamp web console. How it works:
[HTTPS and Headlamp](../explanation/https-and-headlamp.md). LAN mode only.

1. Make sure the ACME server resolves `*.apps.<name>.<domain>` to the ingress
   gateway and reaches it on port 80 ([Register DNS records](register-dns-records.md)):
   certificates are proven by HTTP-01.
2. Add the sections:

   ```yaml
   certManager:
     acmeServer: https://pki.example.com/acme/acme/directory   # e.g. step-ca's ACME provisioner
     caFile: /path/to/root_ca.crt                            # if the ACME CA is private
   headlamp:
     hostname: headlamp.apps.lab.example.com
   ```

3. Apply (part of `create` on a new cluster):

   ```sh
   ./deploy-talos.py headlamp -f lab.yaml
   ```

   With `oidc`, this first adds Headlamp's client to the API servers' accepted
   audiences, one control plane at a time, after confirmation.

4. Check: `https://headlamp.apps.lab.example.com` shows Headlamp with a valid
   certificate; with `oidc`, "Sign in" goes through Keycloak.

## Before you turn on `certManager`

Port 443 of the shared gateway will only terminate TLS. Your own `TLSRoute`s
on it stop working: move them to `HTTPRoute`s on an HTTPS listener first
([Expose an application](expose-an-application.md)). Argo CD's route moves by
itself; its CLI then needs `--grpc-web`.

## Without a host name

Leave out `headlamp.hostname`, then:

```sh
kubectl -n headlamp port-forward svc/headlamp 8080:80   # http://localhost:8080
```
