# Template: Monorepo Root

README template for a monorepo root containing multiple apps, libraries, or packages. Replace `{placeholders}` with actual values.

---

# {Monorepo Name}

{One-sentence description of what this monorepo contains — under 120 characters.}

## Contents

- [{App/lib name}]({path}/README.md) — {one-line description}
- [{App/lib name}]({path}/README.md) — {one-line description}
- [{App/lib name}]({path}/README.md) — {one-line description}

## Structure

```
{root}/
├── apps/
│   ├── {app-1}/          # {short description}
│   └── {app-2}/          # {short description}
├── libs/
│   └── {lib-1}/          # {short description}
├── docs/                  # Documentation
└── infra/                 # Shared deployment manifests (if any)
```

## Quick start

**Prerequisites:** {e.g., Node.js ≥ 22, Go ≥ 1.24, Docker}

```bash
git clone https://github.com/{org}/{monorepo-name}
cd {monorepo-name}
{install-command}        # Install dependencies for all apps
{dev-command}            # Start everything locally
{test-command}           # Run all tests
{check-command}          # Lint + typecheck + test
```

### Per app

```bash
cd apps/{app-name}
{app-dev-command}
```

## Tech stack

| App | Language | Framework | Database |
|-----|----------|-----------|----------|
| {app-1} | {e.g., TypeScript} | {e.g., Next.js 16} | {e.g., —} |
| {app-2} | {e.g., Go} | {e.g., stdlib} | {e.g., PostgreSQL} |

## Deploy

Each app is deployed independently via {e.g., GitHub Actions} to {platform}.

| App | Dev | Prod | Manifest |
|-----|-----|------|----------|
| {app-1} | Push to `main` | {Manual/Tag} | `apps/{app-1}/{manifest-dir}/` |
| {app-2} | Push to `main` | {Manual/Tag} | `apps/{app-2}/{manifest-dir}/` |

## Contributing

1. Create a branch from `main`
2. Make changes in the relevant `apps/` or `libs/` folder
3. Run `{check-command}` from the root
4. Open a PR

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Team

- **Team:** {team-name}
- **Chat:** [{#team-channel}]({teams-or-slack-url})

## License

[{License}](LICENSE)
