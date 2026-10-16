# Template: Batch Job (Scheduled Job)

README template for a scheduled or event-triggered batch job: a Kubernetes CronJob, a timer-triggered function, a scheduled pipeline or similar. Replace `{placeholders}` with actual values.

---

# {Job Name}

{One-sentence description of what this job does — under 120 characters.}

## Schedule

| | |
|---|---|
| **Schedule** | `{cron-expression}` ({human-readable, e.g., daily at 06:00}) |
| **Trigger** | {Cron / manual / event-driven} |
| **Duration** | {Typical run time, e.g., 2–5 minutes} |
| **Idempotent** | {Yes/No — safe to run multiple times?} |

## What does the job do?

{2–3 sentences describing the job's purpose and what data it processes.}

1. {Step 1 — e.g., Fetches data from the data warehouse}
2. {Step 2 — e.g., Transforms and validates}
3. {Step 3 — e.g., Writes to database / publishes to message queue}

## Failure handling

| Scenario | Handling |
|----------|----------|
| Transient error (network timeout) | {e.g., 3 retries with exponential backoff} |
| Permanent error (invalid data) | {e.g., Logs and skips, notifies team} |
| Job fails entirely | {e.g., Alert to team channel, manual re-run from platform console} |

## Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| {`ENV_VAR`} | {Description} | {Yes/No} | {default or —} |

## Observability

- **Dashboard:** [{Grafana / Azure Monitor / Datadog}]({dashboard-url})
- **Logs:** [{Loki / Application Insights / CloudWatch}]({logs-url})
- **Alerts:** {Team chat channel for job failure alerts}
- **Metrics:** `/metrics` (Prometheus)

## Deploy

- **Platform:** {e.g., Kubernetes CronJob, Azure Functions timer trigger, AWS EventBridge + Lambda}
- **Dev:** {e.g., Automatically on push to `main`}
- **Prod:** {e.g., Manual dispatch}
- **Manifests:** {e.g., `k8s/cronjob.yaml`, `infra/`}

## Development

```bash
git clone https://github.com/{org}/{job-name}
cd {job-name}
{install-command}
{test-command}
```

### Run locally

```bash
{command to run the job locally, e.g.:}
{env-vars} {run-command}
```

## Team

- **Team:** {team-name}
- **Chat:** [{#team-channel}]({teams-or-slack-url})
- **Contact:** {email}

## License

[{License}](LICENSE)
