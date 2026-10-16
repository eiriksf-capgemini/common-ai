# Template: Service / API

README template for a deployed service or API. Replace `{placeholders}` with actual values.

---

# {Project Name}

{One-sentence description of what this service does — under 120 characters.}

## Quick start

**Prerequisites:** {e.g., Node.js ≥ 22, Docker, VPN}

```bash
git clone https://github.com/{org}/{project-name}
cd {project-name}
{install-command}
{dev-command}        # {e.g., http://localhost:8080}
{test-command}
```

## Tech stack

- **Language:** {e.g., Kotlin 2.0}
- **Framework:** {e.g., Spring Boot 3.4}
- **Database:** {e.g., PostgreSQL via Flyway + HikariCP}
- **Platform:** {e.g., Kubernetes (AKS), Azure App Service, AWS ECS}
- **Auth:** {e.g., Entra ID, Keycloak, OAuth2 client credentials}

## API

| Method | Path | Description |
|--------|------|-------------|
| {GET} | {/api/resource} | {Description} |
| {GET} | `/health` | Health check |
| {GET} | `/metrics` | Prometheus metrics |

{If > 10 endpoints: link to OpenAPI spec instead.}

## Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| {`ENV_VAR`} | {Description} | {Yes/No} | {default or —} |

## Deploy

Deployed to {platform} via {e.g., GitHub Actions, Azure DevOps}.

- **Dev:** {e.g., Automatically on push to `main`}
- **Prod:** {e.g., Manual dispatch}
- **Manifests:** {e.g., `k8s/dev.yaml`, `k8s/prod.yaml`, `infra/`}

## Observability

- **Dashboard:** [{Grafana / Azure Monitor / Datadog}]({dashboard-url})
- **Logs:** [{Loki / Application Insights / CloudWatch}]({logs-url})
- **Alerts:** {Team chat channel}
- **Metrics:** `/metrics` (Prometheus)

## Team

- **Team:** {team-name}
- **Chat:** [{#team-channel}]({teams-or-slack-url})
- **Contact:** {email}

## Contributing

1. Create a branch from `main`
2. Run `{check-command}` before pushing
3. Open a PR

## License

[{License}](LICENSE)
