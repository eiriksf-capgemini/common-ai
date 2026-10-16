# scripts

- `gh-app-token.mjs` — mints a one-hour GitHub App installation token so agents push and open PRs as `<app>[bot]`. Configure with a gitignored `.gh-app-identity.json` at the repo root; the helper finds it from any directory inside the repo. Run `node scripts/gh-app-token.mjs --check` to verify, `eval "$(node scripts/gh-app-token.mjs --env)"` to use. Full setup in [skills/github-app-agent-identity](../skills/github-app-agent-identity/SKILL.md).
