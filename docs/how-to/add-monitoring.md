# Add monitoring

> How-to · [Documentation](../../README.md#documentation)

Add `kubectl top` (metrics-server) and Prometheus, Alertmanager and Grafana
(kube-prometheus-stack). What they collect: [Metrics and monitoring](../explanation/monitoring.md).
Needs [the add-ons in Git](manage-addons-in-git.md); a `longhorn` section
gives Prometheus and Grafana persistent volumes.

1. Add the sections:

   ```yaml
   metricsServer: {}
   monitoring:
     hostname: grafana.apps.lab.example.com   # needs certManager; omit for port-forward
     retention: 7d
     storageSize: 10Gi
   ```

2. Apply: `./deploy-talos.py argocd -f lab.yaml`.
3. Check:

   ```sh
   kubectl top nodes
   kubectl -n argocd get application monitoring metrics-server
   ```

## Open the UIs

| UI | How |
|---|---|
| Grafana | `https://<monitoring.hostname>`: "Sign in with Keycloak" with `oidc`, or the local `admin` |
| Prometheus | `kubectl -n monitoring port-forward svc/monitoring-prometheus 9090` |
| Alertmanager | `kubectl -n monitoring port-forward svc/monitoring-alertmanager 9093` |

Grafana's local admin password, the way in when Keycloak is down:

```sh
kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d
```

## Send alerts somewhere

Alertmanager has no receivers: alerts only show in its UI and in Grafana. Add
a receiver in `alertmanager.config` of the chart's values.

## Monitor your own application

Create a `ServiceMonitor`, `PodMonitor` or `PrometheusRule` anywhere in the
cluster: Prometheus picks up all of them.
