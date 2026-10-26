# Azure Monitor managed Prometheus (AKS add-on)

What changes when the cluster's Prometheus is the Azure-managed one instead of a self-hosted
kube-prometheus-stack. The application code in SKILL.md is identical; the Kubernetes and dashboard side
is not. Verified against one AKS platform on 2026-10-21; re-check the commands, the add-on moves fast.
Where a value lives in a specific platform repo, the `gitops-app-deploy` platform profile names the file or command.

## What is there

| Piece | Self-hosted stack | Azure managed |
|---|---|---|
| Scraper | Prometheus pods you run | `ama-metrics` add-on pods in `kube-system` (replica set + node DaemonSet + targets operator) |
| Storage | Prometheus TSDB / Mimir | Azure Monitor workspace, 18 months retention, billed per ingested sample |
| Scrape config | `ServiceMonitor` / `PodMonitor` (`monitoring.coreos.com/v1`) | pod annotations, or `PodMonitor`/`ServiceMonitor` in the **`azmonitoring.coreos.com/v1`** group (same schema, different apiVersion) |
| Rules | `PrometheusRule` CRD | Azure resource `Microsoft.AlertsManagement/prometheusRuleGroups` (OpenTofu: `azurerm_monitor_alert_prometheus_rule_group`); no CRD |
| Dashboards | Grafana | portal **Monitor > Dashboards with Grafana** (free, preview), or Azure Managed Grafana, or any Grafana with the Azure-authenticated Prometheus data source |
| Alert routing | Alertmanager | Azure Monitor action groups (mail, Teams, webhook) |
| Logs | Loki / Elastic | not part of this; Container insights is a separate, costlier add-on |

The `monitoring.coreos.com` CRDs do **not** exist unless someone also installed the Prometheus Operator.
Applying a `PodMonitor` or `PrometheusRule` from SKILL.md on such a cluster fails with "no matches for kind".
Check first:

```sh
kubectl get crd | grep -E 'monitoring.coreos.com|azmonitoring.coreos.com'
az aks show -g <rg> -n <cluster> --query azureMonitorProfile.metrics.enabled      # add-on on?
kubectl -n kube-system get pods -l rsName=ama-metrics                            # scraper running?
```

## Getting an application scraped

### Annotations

The add-on scrapes pods annotated `prometheus.io/scrape: "true"` **only in namespaces matched by**
`podannotationnamespaceregex` in the `ama-metrics-settings-configmap` (`kube-system`). The default is
no namespaces at all; the platform repo sets it to the workload namespaces (the platform profile says
where; on cloud-infra it is `gitops/platform/azure-monitor-metrics/configmap.yaml`). A new namespace must
be added there or nothing is scraped, and there is no error anywhere.

```yaml
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: /metrics       # default /metrics
        prometheus.io/scheme: http         # default http
```

### PodMonitor in the Azure group

Use when you need relabeling, several ports, or a scrape interval the annotation cannot express.

```yaml
apiVersion: azmonitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: my-app
  namespace: myteam
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: my-app
  podMetricsEndpoints:
    - port: http
      path: /metrics
      interval: 30s
```

## Verifying a target

```sh
# the collector's own Prometheus UI shows targets and last scrape errors
kubectl -n kube-system port-forward "$(kubectl -n kube-system get pod -l rsName=ama-metrics -o name | head -1)" 9090 &
sleep 2 && curl -s localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.namespace=="<ns>") | {pod: .labels.pod, health, lastError}'
# or browse http://localhost:9090/targets; stop with: kill %1
# a sample is in the workspace: portal > Monitor > Metrics explorer with PromQL, query up{job=~".*my-app.*"}
```

Expect a few minutes of lag between the first scrape and the first query result.

## Rules and alerts

Recording and alerting rules are Azure resources, not cluster objects. Keep them in the platform repo's
OpenTofu next to the workspace (the platform profile names the file; on cloud-infra
`modules/azure/managed-prometheus/rules.tf`), scoped to the
cluster with `cluster_name`. An alert rule needs an action group; the free portal Grafana has no alerting.

```hcl
# Lives next to the workspace resource in the platform repo;
# `azurerm_monitor_workspace.this` is that module's workspace and `var.action_group_id` an input you add.
resource "azurerm_monitor_alert_prometheus_rule_group" "my_app" {
  name                = "my-app"
  location            = var.location
  resource_group_name = var.resource_group_name
  cluster_name        = var.cluster_name
  scopes              = [azurerm_monitor_workspace.this.id]
  rule_group_enabled  = true
  interval            = "PT1M"

  rule {
    alert      = "MyAppHighErrorRate"
    enabled    = true
    expression = <<-EOT
      sum(rate(http_requests_total{app="my-app",status=~"5.."}[5m]))
        / sum(rate(http_requests_total{app="my-app"}[5m])) > 0.05
    EOT
    for        = "PT5M"
    severity   = 3
    labels     = { team = "myteam" }
    annotations = { summary = "my-app error rate above 5%" }
    action { action_group_id = var.action_group_id }
  }
}
```

## Dashboards

- **Portal Grafana** (Monitor > Dashboards with Grafana): import community dashboards by ID; the
  Kubernetes ones work because the platform installed the default recording rules. No alerting, library
  panels or plugins. Entra ID login; share by portal RBAC on the workspace (`Monitoring Reader`).
- **Any Grafana** (desktop, Grafana Cloud, Managed Grafana): data source type *Prometheus*, URL = the
  workspace `query_endpoint` (the platform profile says how to read it; on cloud-infra
  `make output STACK=live/azure/poc/40-observability`),
  authentication *Azure Monitor managed service for Prometheus* with a managed identity or app
  registration holding `Monitoring Data Reader` on the workspace.
- PromQL is standard; the `cluster` label is added by the add-on, use it when more than one cluster
  ships to the workspace.

## Cost rules

- Billing is per ingested sample. The *minimal ingestion profile* trims only the add-on's own targets
  (kubelet, cAdvisor, kube-state-metrics); **application metrics are ingested in full**.
- A histogram with the default 11 buckets times the number of routes times status codes adds up fast.
  Keep label values bounded (no ids, no paths with parameters), prefer summary-free counters and a
  small set of histograms, and check **Cost analysis > Azure Monitor** after the first week.
- Scrape interval: the add-on default is 30 s; `prometheus.io/` annotations cannot change it, a
  `PodMonitor` can (`interval: 60s` halves the bill for that app).
- When the cluster is stopped nothing is ingested and nothing is billed.

## Logs

Not shipped. `kubectl logs` is the only log store on this platform; structured JSON on stdout still
helps `kubectl logs | jq`. Enabling Container insights turns on Log Analytics ingestion, which costs more
than the rest of the dev cluster combined; a decision for the platform owner, not for an app.
