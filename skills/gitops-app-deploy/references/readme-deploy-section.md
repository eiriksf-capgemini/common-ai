# README: Deploy and Observability sections

Drop-in for the service README, matching the `readme-review` service template (sections "Deploy" and
"Observability"). Replace the app placeholders with the values discovered in Step 1 and the platform
placeholders with the **README values** section of the platform profile. Keep the platform's own
documentation out of here; link to it.

| Placeholder | Source |
|---|---|
| `{app}`, `{namespace}`, `{tag}`, `{liveness_path}`, `{readiness_path}` | Step 0 inputs |
| `{registry}`, `{login_server}` | Step 1 discovery |
| `{dev_host}` | the profile's hostname pattern, filled with what Step 1 discovered (for example the ingress IP) |
| `{tag_policy}` | Step 0 (`semver` or `the short git SHA`) |
| `{build_and_push}` | profile: registry commands (build, push, build-in-cloud if offered) |
| `{platform_repo}`, `{platform_repo_url}`, `{app_dir}` | profile: repo name, URL and application directory |
| `{cluster}`, `{reconciler}`, `{sync_time}` | profile: cluster name, what reconciles (e.g. Argo CD), time from merge to running |
| `{dev_url_access}` | profile: who can reach the dev URL, and over what protocol |
| `{status_command}`, `{cluster_power_note}` | profile: confirm-after-merge command; sentence on stopped clusters, or empty |
| `{metrics_scraper}`, `{dashboards}`, `{logs}` | profile: metrics and logs section |

````markdown
## Build

The image is built from the `Dockerfile` and pushed to the platform registry. Tags are {tag_policy}; `latest` is never deployed.

```sh
{build_and_push}
```

## Deploy

Runs on the **{cluster}** cluster, reconciled by {reconciler} from
[`{platform_repo}/{app_dir}/`]({platform_repo_url}/tree/main/{app_dir}).
This repo holds no manifests.

- **Release:** set `newTag` in `overlays/dev/kustomization.yaml` to a pushed tag, open a PR in {platform_repo}. A merged PR is a deployment ({sync_time}).
- **Dev URL:** http://{dev_host} ({dev_url_access}).
- **Secrets:** `kubectl -n {namespace} create secret generic {app}-secrets --from-literal=KEY=value` (not in Git).
- **Status:** `{status_command}`. {cluster_power_note}

## Observability

- **Metrics:** `/metrics` (Prometheus format), scraped by {metrics_scraper}. {Delete this line if the app has no metrics endpoint yet.}
- **Dashboards:** {dashboards}.
- **Logs:** {logs}.
- **Health:** `{liveness_path}` (liveness), `{readiness_path}` (readiness).
````

If the README already has a Deploy section for another platform, add this one next to it under a
sub-heading rather than replacing it; the old platform may still be live.
