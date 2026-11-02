# Manifest templates (kustomize base + dev overlay)

Replace `{app}`, `{namespace}`, `{port}`, `{login_server}`, `{tag}`, `{liveness_path}`, `{readiness_path}`, and
the profile-supplied `{app_dir}` (the application's directory in the platform repo), `{dev_host}` (dev hostname
pattern) and `{ingress_class}`. Everything else is deliberate; the comments say why. Directory layout, names and
labels follow the profile's **reference app**; diff against it after writing. Added on top of a plain reference app:
the restricted-compatible security context, the overlay `images:` pin, and optional scrape annotations. A diff
that shows only those three differences is the intended result.

## base/kustomization.yaml

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
```

## base/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app}
  labels:
    app.kubernetes.io/name: {app}
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: {app}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {app}
      # ONLY if the app serves Prometheus metrics on /metrics (observability-setup, Step 7) AND the profile
      # says pods are scraped by annotation. Delete the three annotations otherwise: a missing endpoint becomes
      # a permanently failing scrape target and nothing reports it.
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "{port}"
        prometheus.io/path: /metrics
    spec:
      # Pod Security "restricted"-compatible. Namespaces that enforce baseline and warn on restricted
      # (the profile says) stay quiet with these four settings, and they cost nothing.
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      automountServiceAccountToken: false   # the app does not talk to the Kubernetes API
      containers:
        - name: {app}
          # Tag is pinned per environment in overlays/<env>/kustomization.yaml (images:), never here.
          image: {login_server}/{app}
          ports:
            - name: http
              containerPort: {port}
          env:
            - name: PORT
              value: "{port}"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          readinessProbe:
            httpGet:
              path: {readiness_path}
              port: http
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: {liveness_path}
              port: http
            initialDelaySeconds: 10
            periodSeconds: 10
          resources:
            # Dev node is small and shared; start here and raise from measurements, not guesses.
            requests:
              cpu: 10m
              memory: 64Mi
            limits:
              memory: 128Mi
```

If the image runs as root, the pod is rejected by `runAsNonRoot`. Fix the Dockerfile (`USER`), or as a
last resort set `runAsUser` to a uid that exists in the image. If the app writes to disk, add an
`emptyDir` volume at that path rather than loosening the security context.

Secrets: reference, never inline.

```yaml
          envFrom:
            - secretRef:
                name: {app}-secrets
                optional: true          # pod starts without it; drop `optional` if the app cannot
```

and document `kubectl -n {namespace} create secret generic {app}-secrets --from-literal=KEY=value` in the README.

## base/service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {app}
  labels:
    app.kubernetes.io/name: {app}
spec:
  selector:
    app.kubernetes.io/name: {app}
  ports:
    - name: http
      port: 80
      targetPort: http
```

## overlays/dev/kustomization.yaml

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: {namespace}
labels:
  - pairs:
      environment: dev
    includeSelectors: false
resources:
  - ../../base
  - ingress.yaml
images:
  # Promotion = copying this block to the next environment's overlay with the tag you tested.
  - name: {login_server}/{app}
    newTag: "{tag}"
```

## overlays/dev/ingress.yaml

```yaml
# Dev-only. Hostname pattern, ingress class, TLS and who can reach it are defined by the platform profile;
# add TLS the way the profile describes once the platform supports it.
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {app}
spec:
  ingressClassName: {ingress_class}
  rules:
    - host: {dev_host}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {app}
                port:
                  name: http
```

## Overlay patches

Environment-specific env vars go in a strategic-merge patch, as the profile's reference app does:

```yaml
# overlays/dev/patch-env.yaml   (add `patches: [{path: patch-env.yaml}]` to the overlay kustomization)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app}
spec:
  template:
    spec:
      containers:
        - name: {app}
          env:
            - name: PUBLIC_URL
              value: http://{dev_host}
```

## Render check

```sh
kubectl kustomize {app_dir}/overlays/dev
kubectl apply --dry-run=server -k {app_dir}/overlays/dev    # cluster must be running
```
