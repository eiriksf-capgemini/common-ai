# README: Deploy and Observability sections

Drop-in for the service README, matching the `readme-review` service template (sections "Deploy" and
"Observability"). Replace placeholders with the values discovered in Step 1. Keep the platform's own
documentation out of here; link to it.

````markdown
## Build

The image is built from the `Dockerfile` and pushed to the platform registry. Tags are {semver | the short git SHA}; `latest` is never deployed.

```sh
az login && az acr login --name {registry}
docker build -t {login_server}/{app}:{tag} . && docker push {login_server}/{app}:{tag}
# or, without local docker:
az acr build --registry {registry} --image {app}:{tag} .
```

## Deploy

Runs on the **{cluster}** AKS cluster, reconciled by Argo CD from
[`cloud-infra/gitops/apps/{namespace}/{app}/`](https://github.com/eiriksf-capgemini/cloud-infra/tree/main/gitops/apps/{namespace}/{app}).
This repo holds no manifests.

- **Release:** set `newTag` in `overlays/dev/kustomization.yaml` to a pushed tag, open a PR in cloud-infra. A merged PR is a deployment (within ~3 minutes).
- **Dev URL:** http://{app}.{ingress_ip}.nip.io (plain HTTP; reachable from Norwegian networks and the operators' egress only).
- **Secrets:** `kubectl -n {namespace} create secret generic {app}-secrets --from-literal=KEY=value` (not in Git).
- **Status:** `kubectl -n platform get application {namespace}-{app}`; the cluster is stopped outside working hours (`make aks-start` in cloud-infra).

## Observability

- **Metrics:** `/metrics` (Prometheus format), scraped by Azure Monitor managed Prometheus via pod annotations. {Delete this line if the app has no metrics endpoint yet.}
- **Dashboards:** Azure portal → Monitor → Dashboards with Grafana (Entra ID login).
- **Logs:** `kubectl -n {namespace} logs deploy/{app}`; no central log store yet.
- **Health:** `{liveness_path}` (liveness), `{readiness_path}` (readiness).
````

If the README already has a Deploy section for another platform, add this one next to it under a
sub-heading rather than replacing it; the old platform may still be live.
