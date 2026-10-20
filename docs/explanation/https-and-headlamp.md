# HTTPS and Headlamp

> Explanation · [Documentation](../../README.md#documentation)

How the gateway gets certificates, and how the Headlamp web console works
with the users' own rights. To set it up:
[Serve HTTPS and Headlamp](../how-to/serve-https-and-headlamp.md).

## Certificates from your ACME CA

With a `certManager` section the script installs cert-manager (Gateway API
support on) and a ClusterIssuer `acme` for `certManager.acmeServer`, trusting
`caFile`.

Certificates are proven by **HTTP-01**: cert-manager adds a temporary route on
the gateway's HTTP listener, to a solver pod behind a ClusterIP Service (so
quotas forbidding NodePorts don't block it), and the ACME server fetches
`http://<host>/.well-known/acme-challenge/...`. That is why the ACME server must
resolve the host name to the gateway and reach it on port 80; the
`*.apps.<name>.<domain>` record covers every UI host. cert-manager renews
before expiry (step-ca issues 24-hour certificates; renewal after about 16
hours).

## Termination on the gateway

Port 443 then terminates TLS: one HTTPS listener per host, each with its own
certificate ([listeners](../reference/ingress-gateway.md#listeners)). Cilium
can't mix this with passthrough on the same port, so:

- the passthrough listener is removed, and your own `TLSRoute`s on the shared
  gateway stop working (use HTTPRoutes on an HTTPS listener instead);
- Argo CD moves from its TLSRoute to an HTTPRoute, and argocd-server serves
  plain HTTP behind the gateway; the `argocd` CLI then needs `--grpc-web`.

The script checks that every listener is programmed and stops otherwise.
Each host also gets an `http://` route that redirects to `https://`.

## Headlamp: the user's rights, not its own

[Headlamp](https://headlamp.dev) is the Kubernetes web console (the successor
of the archived Kubernetes Dashboard). Its service account gets **no**
cluster-admin binding. With `oidc`, users sign in through Keycloak and
Headlamp sends their ID token to the API server, so each user has exactly
their own Kubernetes permissions: members of `kubernetes.adminGroups` are
cluster-admin, others see what RBAC grants them. For that the API servers
accept Headlamp's client as a second token audience
([Authentication](authentication.md#what-a-login-involves)).

The client secret lives only in Secret `headlamp/headlamp-oidc`, never in Helm
values. Without `oidc`, Headlamp asks for a token.
