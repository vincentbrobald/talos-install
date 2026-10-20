# Metrics and monitoring

> Explanation · [Documentation](../../README.md#documentation)

What the `metricsServer` and `monitoring` add-ons collect, and the choices
behind them. To add them: [Add monitoring](../how-to/add-monitoring.md).

## metrics-server

Serves the resource metrics API (`kubectl top`, HorizontalPodAutoscaler) from
namespace `kube-system`. Talos' kubelets have self-signed serving
certificates, so it runs with `--kubelet-insecure-tls`: it still
authenticates to each kubelet with its token but doesn't verify the kubelet's
certificate ([Security](security.md#kubelet-certificates)).

## kube-prometheus-stack

Application and release `monitoring` in namespace `monitoring` (privileged,
for node-exporter).

- **Prometheus** scrapes the API servers, the kubelets and cAdvisor, CoreDNS,
  kube-state-metrics and node-exporter on every node. It picks up every
  `ServiceMonitor`, `PodMonitor`, `Probe` and `PrometheusRule` in the
  cluster, so applications bring their own. Data sits on a Longhorn volume,
  kept for `retention` or until 80% of the volume is used.
- **Trimmed series.** Two thirds of the API servers' series are histogram
  buckets no rule or dashboard of the chart reads (watch, storage, flow
  control, admission, response sizes, etcd request latency…). They are dropped
  at scrape time; their `_sum` and `_count` stay, as does
  `apiserver_request_sli_duration_seconds`, which the latency alerts use. On
  the lab cluster this took Prometheus from 254,000 series to about 120,000.
- **Not scraped:** the controller manager, the scheduler and etcd (Talos binds
  their metrics to localhost) and kube-proxy (replaced by Cilium in LAN mode).
  Their jobs and alert rules are off: they would only report targets down.
- **Alertmanager** evaluates the chart's default alerts but has no receivers:
  alerts show in Alertmanager and Grafana until you add one.
- **Grafana** has Prometheus as its data source and the chart's Kubernetes
  dashboards. With `oidc`, members of `oidc.grafana.adminGroups` are `Admin`
  and everyone else a `Viewer`. The local `admin` account (Secret
  `monitoring/grafana-admin`, kept once created) is the way in when Keycloak
  is down. The client secret is in Secret `monitoring/grafana-oidc`, never in
  the values.

## Sizing

Prometheus requests 768 MiB (limit 2 GiB) and grows with the number of
series. Grafana, Alertmanager, the operator and kube-state-metrics add about
500 MiB, node-exporter about 20 MiB per node. Without a `longhorn` section
Prometheus has no volume and loses its data on restart.
