# Expose an application

> How-to · [Documentation](../../README.md#documentation)

Publish an application on the cluster's shared ingress gateway, by host name.
LAN mode only. The listeners: [Ingress gateway](../reference/ingress-gateway.md).
Why one gateway: [LAN mode](../explanation/lan-mode.md#the-ingress-gateway).

The examples use `my-app` in namespace `my-app` and the domain
`apps.lab.example.com`; `*.apps.lab.example.com` must resolve to the gateway
([Register DNS records](register-dns-records.md)).

## Over HTTP

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata: {name: my-app, namespace: my-app}
spec:
  parentRefs: [{name: ingress, namespace: ingress, sectionName: http}]
  hostnames: [my-app.apps.lab.example.com]
  rules: [{backendRefs: [{name: my-app, port: 80}]}]
```

Check: `curl http://my-app.apps.lab.example.com`.

## Over HTTPS, the certificate from the cluster file

With a `certManager` section:

1. List the host:

   ```yaml
   certManager:
     extraHosts: [my-app.apps.lab.example.com]
   ```

2. Run `./deploy-talos.py argocd -f lab.yaml` (or `headlamp`): the gateway gets
   a listener `https-my-app` and a certificate.
3. Attach the route to it:

   ```yaml
   spec:
     parentRefs: [{name: ingress, namespace: ingress, sectionName: https-my-app}]
   ```

First labels must be unique and can't be `argocd`, `headlamp` or `grafana`.

## Over HTTPS, the listener in your own namespace

With a `certManager` section, and the namespace labelled
labelled with `certManager.listenersLabel``=ingress` (default `deploy-talos/listeners`; a
platform decision: the namespace may then claim any free host name), no change
to the cluster file is needed:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: ListenerSet
metadata: {name: my-app, namespace: my-app}
spec:
  parentRef: {name: ingress, namespace: ingress}
  listeners:
    - name: https
      port: 443
      protocol: HTTPS
      hostname: my-app.apps.lab.example.com
      tls: {mode: Terminate, certificateRefs: [{name: my-app-tls}]}   # e.g. a cert-manager Certificate
      allowedRoutes: {namespaces: {from: Same}}
```

The route attaches to the ListenerSet:

```yaml
spec:
  parentRefs: [{group: gateway.networking.k8s.io, kind: ListenerSet, name: my-app, sectionName: https}]
```

## TLS passed through to the application

Without `certManager`, the backend terminates TLS itself:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: TLSRoute
metadata: {name: my-app, namespace: my-app}
spec:
  parentRefs: [{name: ingress, namespace: ingress, sectionName: tls-passthrough}]
  hostnames: [my-app.apps.lab.example.com]
  rules: [{backendRefs: [{name: my-app, port: 443}]}]
```

## Behind a load balancer

Forward `*.apps.<cluster>.<domain>` on ports 80 and 443 to the gateway's
address (`kubectl -n ingress get gateway ingress`).
