# Section Spec — Required and Optional Sections by Project Type

Sections are listed in **cognitive funneling order**: broad context first, details later. This is the recommended order for README sections.

## Section Matrix

| # | Section | Service | Library | Monorepo | Batch job | Notes |
|---|---------|:-------:|:-------:|:--------:|:---------:|-------|
| 1 | Title + one-liner | **R** | **R** | **R** | **R** | Self-explanatory name + < 120 char description |
| 2 | Badges | O | O | O | O | 2–4 max (CI, coverage, license). No badge walls. |
| 3 | Quick start | **R** | **R** | **R** | O | Copy-paste commands to run locally |
| 4 | Tech stack | **R** | O | **R** | O | Languages, frameworks, key dependencies |
| 5 | Structure map | O | — | **R** | — | Directory layout with descriptions |
| 6 | API / endpoints | **R** | **R** | — | — | Table of endpoints or link to OpenAPI. For libraries: exported API. |
| 7 | Configuration | **R** | O | — | **R** | Table: env var, description, required, default |
| 8 | Deployment | **R** | — | **R** | **R** | Platform, environments, manifest location |
| 9 | Schedule / triggers | — | — | — | **R** | Cron expression, trigger mechanism, frequency |
| 10 | Failure semantics | — | — | — | **R** | What happens on failure? Retry? Alert? Manual intervention? |
| 11 | Auth / integrations | C | — | O | C | Which auth mechanism, which services consumed/exposed |
| 12 | Observability | **R** | — | O | **R** | Dashboards, logs, alerts, metrics |
| 13 | Install / compatibility | — | **R** | — | — | Package manager install, supported versions/platforms |
| 14 | Usage examples | O | **R** | — | — | Code samples showing common use cases |
| 15 | Contributing | O | **R** | **R** | O | How to run tests, submit PRs |
| 16 | Team / ownership | **R** | O | **R** | **R** | Owning team, chat channel, contact |
| 17 | License | **R** | **R** | **R** | **R** | License name and link |
| 18 | Table of Contents | >100 | >100 | **R** | >100 | Required if README exceeds 100 lines |

**Legend:** **R** = Required, O = Optional, C = Conditional (include if relevant), — = Not applicable, >100 = Required if README > 100 lines

## Section Details

### 1. Title + one-liner

```markdown
# order-service

Receives orders from the webshop and forwards them to the warehouse system.
```

- Title must match repository or directory name
- One-liner directly below title, no heading, < 120 characters
- Say what it **does**, not what it **is** ("Receives orders" not "A service for order handling")

### 2. Badges

```markdown
[![CI](https://github.com/{org}/order-service/actions/workflows/ci.yml/badge.svg)](...)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](...)
```

- Max 2–4 badges. CI status and license are most useful.
- Don't add badges for metrics nobody checks in the README.

### 3. Quick start

```markdown
## Quick start

**Prerequisites:** Node.js ≥ 22, Docker

npm ci          # Install dependencies
npm run dev     # Start dev server (http://localhost:8080)
npm test        # Run tests
```

- Must contain runnable commands, not just prose
- List prerequisites explicitly (versions if unusual)
- Show the shortest path from `git clone` to working app

### 4. Tech stack

```markdown
## Tech stack

- **Backend:** Kotlin 2.0, Spring Boot 3.4
- **Database:** PostgreSQL (via Flyway + HikariCP)
- **Platform:** Kubernetes (AKS)
- **Auth:** Entra ID (OAuth2 / OIDC)
```

- Bullet list with specific versions
- Only list what matters for understanding the project

### 5. Structure map (monorepo)

```markdown
## Structure

| Directory | Description |
|-----------|-------------|
| `apps/frontend/` | Next.js customer frontend |
| `apps/backend/` | Kotlin/Spring Boot API |
| `libs/shared/` | Shared types and utility functions |
```

- Use a table for > 3 directories
- Link to per-app READMEs if they exist

### 6. API / endpoints

```markdown
## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/orders` | List orders for current user |
| GET | `/api/orders/{id}` | Get order by ID |
| POST | `/api/orders` | Create new order |
| GET | `/health` | Health check |
```

- Table for < 10 endpoints; link to OpenAPI/Swagger for more
- For libraries: document exported functions/types

### 7. Configuration

```markdown
## Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DB_URL` | PostgreSQL connection string | Yes | — |
| `PORT` | Server port | No | `8080` |
| `LOG_LEVEL` | Log level | No | `INFO` |
```

- Table format with required/default columns
- Don't list platform-injected variables that are standard (e.g., `KUBERNETES_SERVICE_HOST`, `WEBSITE_HOSTNAME`)

### 8. Deployment

```markdown
## Deploy

Deployed to {platform} via GitHub Actions.

- **Dev:** Automatically on push to `main`
- **Prod:** Manual dispatch or tag
- **Manifests:** `k8s/dev.yaml`, `k8s/prod.yaml`
```

### 9. Schedule / triggers (batch job)

```markdown
## Schedule

- **Cron:** `0 6 * * *` (daily at 06:00)
- **Trigger:** Can also be run manually via `kubectl create job`
- **Duration:** Typically 2–5 minutes
```

### 10. Failure semantics (batch job)

```markdown
## Failure handling

- **Retry:** 3 attempts with exponential backoff
- **Alert:** Notification to the team channel on failure
- **Manual:** Can be re-run from the platform console
- **Idempotent:** Yes — safe to run multiple times
```

### 11. Auth / integrations

```markdown
## Auth and integrations

- **Inbound:** Entra ID (internal admin frontend)
- **Outbound:** Customer API via OAuth2 client credentials, ERP via API key
- **Network policy:** See `k8s/dev.yaml`
```

- Only include if the service has non-trivial auth or external integrations

### 12. Observability

```markdown
## Observability

- **Dashboard:** [Grafana]({dashboard-url})
- **Logs:** [Loki / Application Insights]({logs-url})
- **Alerts:** Team channel #order-service-alerts
- **Metrics:** `/metrics` (Prometheus)
```

### 13. Install / compatibility (library)

```markdown
## Installation

npm install @{org}/my-lib

# or
dependencies {
    implementation("com.{org}:my-lib:1.2.3")
}
```

- Show the package manager command
- Note compatible versions/platforms if relevant

### 14. Usage examples (library)

```markdown
## Usage

import { validateOrgNumber } from '@{org}/my-lib'

const result = validateOrgNumber('123456789')
// { valid: true }
```

- Show the simplest working example first
- Link to more examples if complex

### 15. Contributing

```markdown
## Contributing

1. Fork and clone the repo
2. Run `npm ci` to install tools
3. Create a branch from `main`
4. Run `npm run check` before pushing
5. Open a PR

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.
```

### 16. Team / ownership

```markdown
## Team

- **Team:** Team Orders
- **Chat:** [#team-orders]({teams-or-slack-url})
- **Contact:** team-orders@example.com
```

### 17. License

```markdown
## License

[MIT](LICENSE)
```

### 18. Table of Contents

Required if README exceeds 100 lines. Place after title + one-liner, before first H2.
