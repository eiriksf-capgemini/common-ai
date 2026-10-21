# Platform profile: cloud-infra on Azure (AKS + Argo CD + ACR)

Platform repo: `github.com/eiriksf-capgemini/cloud-infra` (public). Local default: `~/code/cloud-infra`.

**Recognise it by:** `gitops/apps/README.md` describing `<namespace>/<app>/{base,overlays/<env>}`, a
`gitops/clusters/<cluster>/templates/workloads-applicationset.yaml`, and `live/<cloud>/<env>/25-registry`.
Forks and renamed copies that keep this shape use this profile.
Authoritative documents inside it, read them before this file when they disagree:
`README.md`, `gitops/apps/README.md`, `docs/adr/0005` (layout), `0006` (registry), `0007` (namespaces),
`0008` (metrics), `0009` (access control), `docs/runbooks/`.

## How a workload gets deployed

- One Argo CD `ApplicationSet` per cluster scans `gitops/apps/*/*/overlays/<environment>` in the
  platform repo and creates an `Application` named `<namespace>-<app>` for every match. Nothing to register.
- A cluster serves exactly one environment, declared in `gitops/clusters/<cluster>/values.yaml`.
  Today: cluster `azure-dev`, `environment: dev`. No test or prod cluster exists.
- Sync is automated with prune and self-heal, poll interval 3 minutes, retries up to 10 times with
  backoff. A merged PR to `main` is a deployment.
- Namespaces are **never auto-created**. Each `gitops/apps/<namespace>/` has a `namespace` app
  holding the `Namespace` (PSA labels), a `LimitRange` and a per-environment `ResourceQuota`.
- Argo CD runs in the `platform` namespace. UI: `kubectl -n platform port-forward svc/argocd-server 8080:443`.

## Values to look up (never recall)

| Value | Command or file |
|---|---|
| Namespaces that exist | `ls gitops/apps/` (each folder with a `namespace/` app) |
| Namespace quota (dev) | `cat gitops/apps/<ns>/namespace/overlays/dev/resourcequota.yaml` |
| Namespace defaults and PSA | `cat gitops/apps/<ns>/namespace/base/{limitrange,namespace}.yaml` |
| Registry login server | `make output STACK=live/azure/poc/25-registry` (needs Azure login) or `az acr list --query '[].loginServer' -o tsv` |
| Ingress public IP | `kubectl -n ingress-nginx get svc ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}'` or copy the host from `gitops/apps/demo/podinfo/overlays/dev/ingress.yaml` |
| Ingress class | `nginx` (default class; `gitops/platform/ingress-nginx/values.yaml`) |
| Cluster environment | `grep environment: gitops/clusters/azure-dev/values.yaml` |
| Node headroom | `kubectl describe node \| grep -A6 'Allocated resources'` |
| Quota headroom | `kubectl -n <ns> describe resourcequota` |
| kubeconfig | `make output STACK=live/azure/poc/20-cluster` → `get_credentials_command` (`az aks get-credentials ... && kubelogin convert-kubeconfig -l azurecli`) |
| Cluster power state | `make aks-status` **first**; start with `make aks-start` (a few minutes). Stopped cluster = `kubectl` hangs |

Reference app: `demo/podinfo` (namespace `demo`); its dev ingress is the Git fallback for the ingress IP
when the cluster is stopped. Quotas are deliberately small and per namespace; read the quota file before
sizing, do not reuse numbers from a previous run.

## Registry

Azure Container Registry, Basic SKU, Entra ID auth only (admin user disabled). The AKS kubelet identity
holds `AcrPull`, so pods pull without an `imagePullSecret`. One registry for all environments; environments
differ by tag.

```sh
az acr login --name <registry>                                   # docker/podman client, token valid ~3 h
docker build -t <login_server>/<app>:<tag> . && docker push <login_server>/<app>:<tag>
az acr build --registry <registry> --image <app>:<tag> .         # no local docker; builds in Azure (ACR Tasks, ~$0.0001/s)
az acr repository show-tags --name <registry> --repository <app> -o table   # confirm the tag before pinning it
```

Basic SKU has no firewall; pushing works from anywhere with Entra ID. Storage beyond 10 GB costs extra,
so delete old tags occasionally (`az acr repository delete`).

## Cluster guardrails

- **One node**, `Standard_B2as_v2` (2 vCPU / 8 GB), CPU requests already near 90 %. Keep requests at
  `10m` CPU unless measured otherwise. A pod that does not fit stays `Pending` without an error in Argo CD.
- **Pod Security**: `baseline` enforced, `restricted` warned. Use the restricted-compatible
  `securityContext` from the templates.
- **Auto-stop** at 17:00 and 22:00 Europe/Oslo; manual start. `kubectl` hangs or times out when stopped.
- **Reachability** (ADR 0009): ingress 80/443 only from Norway-registered IPv4 prefixes and the operators'
  Zscaler Oslo egress; API server only from the Zscaler ranges. A `curl` from elsewhere times out; that is
  the NSG, not the app. `curl -s ifconfig.co` shows what Azure sees.
- **No TLS, no DNS zone yet.** Dev hosts are `<app>.<ingress-ip>.nip.io` over plain HTTP. cert-manager is
  installed but has no ClusterIssuer.
- **Builds are manual.** Tekton Pipelines and Triggers are installed but no pipelines exist yet
  (`docs/runbooks/tekton.md`). Build on a laptop or with `az acr build`.

## Metrics and logs

- Decision (ADR 0008): Azure Monitor managed Prometheus via the AKS `ama-metrics` add-on, dashboards in the
  free portal **Monitor > Dashboards with Grafana**. No Grafana instance, no Prometheus Operator, no
  `monitoring.coreos.com` CRDs.
- Application pods are scraped by **annotation** (`prometheus.io/scrape: "true"`, `prometheus.io/port`,
  `prometheus.io/path`) in the workload namespaces listed in
  `gitops/platform/azure-monitor-metrics/configmap.yaml` (`podannotationnamespaceregex`).
- Whether scraping is live changes over time (as of 2026-10-21 it was still a draft PR and the add-on was off).
  Check, do not assume: `az aks show -g rg-cloudinfra-poc -n aks-cloudinfra-poc --query azureMonitorProfile.metrics.enabled`
  and whether `gitops/platform/azure-monitor-metrics/` exists on `main`. Annotations are no-ops while it is off.
- Logs: no Container insights, no log shipper. `kubectl logs` only.
- Details for instrumenting the app: `observability-setup` skill, `references/azure-monitor-managed-prometheus.md`.

## Confirm after merge

```sh
kubectl -n platform get application <namespace>-<app>              # Synced / Healthy
kubectl -n <namespace> get pods,svc,ingress -l app.kubernetes.io/name=<app>
curl -sI http://<app>.<ingress-ip>.nip.io/                          # from an allowed egress
kubectl -n <namespace> describe pod -l app.kubernetes.io/name=<app> | grep -iE 'warn|pending|quota|forbidden'
```

## Cost

- Registry Basic ~$5/month flat. ACR Tasks builds ~$0.01 per 100 seconds.
- Nothing per application beyond its share of the node, as long as it fits. A second node is the
  expensive step (and uses the Free Trial's remaining vCPU quota); fit first.
- Metrics: billed per ingested sample once the add-on is on; keep label cardinality bounded.
