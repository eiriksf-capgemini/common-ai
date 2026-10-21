---
name: gitops-app-deploy
description: "Make an application deployable to a GitOps-managed Kubernetes cluster: container image to the registry, kustomize manifests in the platform repo, README deploy section. Platform profiles under references/ (currently: cloud-infra on AKS)."
license: MIT
compatibility: Application with a Dockerfile (or one this skill adds), deployed to a cluster whose manifests live in a separate GitOps repo reconciled by Argo CD
metadata:
  domain: platform
  tags: kubernetes gitops argocd kustomize aks acr deploy
---

# GitOps application deploy

Takes an application from "it builds locally" to "it runs on the cluster and the README says how". The platform owns the manifests: they go into the **platform repo**, not the app repo. The app repo gets a Dockerfile, a build recipe and a README section.

This skill edits two repos. Say which one every file goes to.

## Workflow

```
Step 0: Pick the platform profile and collect inputs
Step 1: Discover platform values from primary evidence
Step 2: Container image: Dockerfile, build, push
Step 3: Manifests in the platform repo
Step 4: Verify the render (and the cluster, if it is up)
Step 5: README in the app repo
Step 6: Ship and confirm
Step 7: Hand off metrics to observability-setup
```

## Step 0: Platform profile and inputs

A platform profile is a file under `references/platform-*.md` describing one GitOps platform: repo layout, discovery rules, registry, guardrails, and **where to look up** the values that change (IP addresses, registry names, namespace lists). Profiles available:

| Profile | Platform | File |
|---|---|---|
| `cloud-infra-azure` | cloud-infra repo, AKS + Argo CD ApplicationSet + ACR | [platform-cloud-infra-azure.md](./references/platform-cloud-infra-azure.md) |

Pick the profile whose **Recognise it by** line matches the platform repo (files and conventions, not the repo name, so forks and renames still match). If no profile matches, say so and stop: writing manifests for an unknown platform produces files Argo CD will never pick up.

Collect before writing anything:

| Input | How to get it | Notes |
|---|---|---|
| App repo | current directory | must contain the source and (eventually) a Dockerfile |
| Platform repo path | ask, or the profile's default | you will create files here |
| Namespace | ask; must already exist in the platform repo | a new namespace is a platform change, see Boundaries |
| App name | directory or manifest name | lowercase DNS label; becomes `<namespace>-<app>` in Argo CD |
| Container port | source, Dockerfile `EXPOSE`, or framework default | |
| Health paths | source | liveness and readiness; add them if missing (observability-setup has the pattern) |
| Image tag policy | ask once | semver or short git SHA; never `latest` |
| Environments | default: only the ones a cluster serves today | an overlay directory **is** a deployment; do not create overlays for environments you do not intend to deploy to |

## Step 1: Discover platform values

Read them, never recall them. The profile lists a command or file for each. **Check the cluster's power state first** (the cloud-infra cluster auto-stops in the evening and `kubectl` hangs against a stopped cluster): if it is stopped, either start it and wait, or take the values that need the cluster (ingress IP) from the profile's Git fallback and record that as the source.

- registry login server
- ingress public IP (for dev hostnames) and ingress class
- the environment the target cluster serves
- the namespace's `LimitRange`, `ResourceQuota` and Pod Security labels
- current headroom on the node and in the namespace quota

Record what you found and where, you will need it for the review contract at the end.

## Step 2: Container image

Check the Dockerfile against this list and fix what is missing. If there is no Dockerfile, write one for the detected stack.

- Multi-stage build; the final stage carries only the runtime.
- Base image pinned to a literal tag in `FROM` (renovate and Dependabot skip `FROM` lines that use an `ARG`).
- `USER` set to a non-root uid; the Pod Security `restricted` profile rejects root.
- Listens on `0.0.0.0` on the container port; reads `PORT` if the framework supports it.
- No secrets, tokens or `.env` files copied in; `.dockerignore` excludes `.git`, `node_modules`, build output.
- `EXPOSE <port>` documented; no `HEALTHCHECK` (Kubernetes probes replace it).

Build and push with the profile's registry commands. Tag with the chosen policy and verify the tag exists in the registry before touching manifests. Put the exact commands in the README (Step 5), not only in the chat.

## Step 3: Manifests in the platform repo

Follow the profile's directory layout exactly; the templates are in [manifest-templates.md](./references/manifest-templates.md). For the cloud-infra profile that is:

```
gitops/apps/<namespace>/<app>/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   └── service.yaml
└── overlays/dev/
    ├── kustomization.yaml      # namespace, environment label, image tag pin
    └── ingress.yaml            # dev-only hostname
```

Rules the templates already follow; keep them when you adapt:

- **Image pinned in the overlay** (`images:` transformer), base carries the repository only. Promotion is changing the tag in the next overlay.
- **Resource requests on every container.** Start small (`10m` / `64Mi`); the dev node is shared and the quota is per namespace. The namespace `LimitRange` adds defaults, but explicit is reviewable.
- **Pod Security `restricted`-compatible** `securityContext`: `runAsNonRoot`, `seccompProfile: RuntimeDefault`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`. The namespaces enforce `baseline` and warn on `restricted`; a warning on every sync is noise nobody reads.
- **Named port `http`**, Service on 80 targeting it, probes by port name.
- **Prometheus annotations** on the pod template (`prometheus.io/scrape`, `port`, `path`) **only if the app serves `/metrics`**. Otherwise leave them out and drop the metrics line from the README section; add both when Step 7 has been done. An annotated pod without the endpoint is a silently failing scrape target.
- **Dev ingress only in `overlays/dev`**, hostname `<app>.<ingress-ip>.nip.io`, no TLS until the platform has a DNS zone and ClusterIssuers.
- **No secrets in Git.** Reference a `Secret` by name with `optional: true` where the app can start without it; creating the Secret is a manual `kubectl` step documented in the README.

## Step 4: Verify

```sh
kubectl kustomize gitops/apps/<namespace>/<app>/overlays/dev          # must render; read the output once
kubectl apply --dry-run=server -k gitops/apps/<namespace>/<app>/overlays/dev   # needs the cluster up; catches PSA and quota rejections
```

If the cluster is stopped (the profile says when and how to start it), run the first command now and the second after it is started, or leave the server dry-run to the user. Say which one you ran.

## Step 5: README in the app repo

Add or update the **Deploy** and **Observability** sections of the service README, in the shape the `readme-review` skill expects ([readme-deploy-section.md](./references/readme-deploy-section.md)): build and push commands, where the manifests live, how a release happens (change the tag, open a PR, merged PR = deployment), the dev URL and its access restriction, and where metrics and logs are read. Keep it under 40 lines; the platform repo's own README holds the rest.

## Step 6: Ship and confirm

1. Open a PR in the platform repo. On the cloud-infra profile a merged PR **is** a deployment; say so in the PR description.
2. After merge, confirm with the profile's commands: the Argo CD `Application` exists and is `Synced`/`Healthy`, the pod is `Running`, the dev URL answers. Report the actual output, not the expectation.
3. If the first sync fails with "namespace not found", the namespace app has not synced yet; Argo CD retries. If it fails on quota or PSA, fix the manifest, do not raise the quota.

## Step 7: Metrics hand-off

Application-side instrumentation (a `/metrics` endpoint, business metrics, health endpoints) is the `observability-setup` skill's job. Invoke it for the code; this skill already placed the scrape annotations in the manifest. The profile says what scrapes the annotations and where dashboards are.

## Boundaries

### ✅ Always

- Look up registry, IP and namespace facts from the platform repo or the cluster; quote the source
- Pin image tags in overlays; set requests; use a restricted-compatible `securityContext`
- Render with `kubectl kustomize` before committing
- State which repo each file goes to
- Tell the user when a step was skipped because the cluster was stopped

### ⚠️ Ask first

- Creating a new namespace (needs a `namespace` app with quota and PSA labels: a platform decision)
- Raising a `ResourceQuota` or `LimitRange`
- Creating `test` or `prod` overlays, or anything under `gitops/platform/`, `gitops/clusters/` or `live/`
- Replacing an existing Dockerfile rather than amending it

### 🚫 Never

- `kubectl apply` the workload directly to the cluster; Argo CD self-heals and reverts it, and the change is invisible in Git
- Use `latest` or an unpinned image, an `imagePullSecret` with registry admin credentials, or enable the registry admin user
- Commit secrets, `.env` files or kubeconfigs to either repo
- Put the ingress IP, registry name or namespace list into prose without having read it this session

## Review contract

The skill ends with this block. Files written without it have not been checked.

```
Platform profile: <name>
Inputs:          <namespace, app, port, tag policy, environments>
Discovered:      <registry, ingress IP, cluster environment, quota headroom: value and where it was read>
Files written:   <repo: path, ...>
Rendered:        kubectl kustomize <path> → OK | FAILED (<error>)
Server dry-run:  OK | FAILED (<error>) | SKIPPED (cluster stopped)
Image in registry: <repo:tag> confirmed by <command> | NOT PUSHED
Left for the user: <manual secrets, PR to open, start cluster, ...>
```

## Sources

- [Argo CD ApplicationSet Git directory generator](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-Git/)
- [Kustomize images transformer](https://kubectl.docs.kubernetes.io/references/kustomize/kustomization/images/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Azure Container Registry authentication with Entra ID](https://learn.microsoft.com/azure/container-registry/container-registry-authentication)
- [`az acr build`](https://learn.microsoft.com/azure/container-registry/container-registry-tutorial-quick-task)
