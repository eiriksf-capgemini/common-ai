# 🤖 Common AI

Agents, instructions, prompts, skills and hooks that make GitHub Copilot and Claude Code smarter. A shared home for AI developers at Capgemini Bergen.

## What is this?

A collection of customizations you can drop into your own repo:

- **🤖 [Agents](agents/)** — Specialised AI assistants for a domain or task
- **📋 [Instructions](instructions/)** — Coding standards applied automatically based on file patterns
- **⚡ [Prompts](prompts/)** — Scaffolding templates for common tasks
- **🎯 [Skills](skills/)** — Reusable patterns with bundled templates and references
- **🪝 [Hooks](hooks/)** — Guardrails that run before or after a tool call

## Getting started

Pick what you need and copy it into your project:

| Tool               | Where it goes                                                                |
| ------------------ | ---------------------------------------------------------------------------- |
| **GitHub Copilot** | `.github/agents/`, `.github/instructions/`, `.github/prompts/`, `.github/skills/` |
| **Claude Code**    | `.claude/agents/`, `.claude/skills/`, and `CLAUDE.md` for instructions       |

Each customization has its own documentation in the table below.

## Customizations

| Type                | Description                                                                             | Documentation                                 |
| ------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------- |
| 🤖 **Agents**       | Specialised assistants, invoked with `@agent-name` in chat                              | **[Agents →](docs/README.agents.md)**         |
| 📋 **Instructions** | Coding standards activated by file pattern (`*.kt`, `*.tsx`, `*.sql`)                  | **[Instructions →](docs/README.instructions.md)** |
| ⚡ **Prompts**      | Scaffolding templates available via `/prompt-name` in chat                              | **[Prompts →](docs/README.prompts.md)**       |
| 🎯 **Skills**       | Production patterns with bundled templates and references                               | **[Skills →](docs/README.skills.md)**         |
| 🪝 **Hooks**        | Pre- and post-tool-use guardrails                                                       | **[Hooks →](docs/README.hooks.md)**           |

## 📖 Folder structure

```plaintext
├── agents/               # One folder per agent: <name>.md (Claude Code), <name>.agent.md (Copilot), metadata.json
├── instructions/         # File-pattern-based coding standards (.instructions.md + .metadata.json)
├── prompts/              # Task-specific scaffolding templates (.prompt.md + .metadata.json)
├── skills/               # One folder per skill, each with a SKILL.md and metadata.json
├── hooks/                # Tool-use guardrails (.hook.json + script)
├── docs/                 # Detailed documentation for each customization type
└── .github/              # Workflows and repo-level Copilot configuration
```

## 🔌 MCP servers for the POC platform

`.mcp.json` at the repo root connects Claude Code (project scope) to the two MCP servers of
the cloud-infra POC when you work inside this checkout:

- **`openchoreo`**: OpenChoreo's own server (`openchoreo-api`, `/mcp`): projects,
  components, deployments, builds. OAuth login against Thunder on first use.
- **`platform`**: the console's server (cloud-infra ADR 0017): platform facts, catalog
  search, Azure resources and cost, every skill in this repo as a prompt
  (`/mcp__platform__<skill>`), the cloud-infra docs as resources. Same Thunder login as
  `openchoreo` (`/mcp` → platform → Authenticate).

Both entries name Thunder's pre-registered public client `user_mcp_client` with callback
port 8075 (Thunder does not allow anonymous dynamic client registration, so Claude Code
cannot register itself). Only the private CA is needed:

```sh
export NODE_EXTRA_CA_CERTS=~/.config/poc-root-ca.crt   # the POC's private CA
```

Outside this checkout, `claude mcp add --transport http ...` with the same URLs (see the
cloud-infra runbook `docs/runbooks/openchoreo-console-image.md`).

## 🤝 Contributing

1. **Agents**: Add a folder to `agents/` with `<name>.md` for Claude Code. A `<name>.agent.md` for Copilot is welcome but optional
2. **Instructions**: Add `*.instructions.md` to `instructions/`
3. **Prompts**: Add `*.prompt.md` to `prompts/`
4. **Skills**: Add a folder with a `SKILL.md` to `skills/`
5. **Hooks**: Add `*.hook.json` with its script to `hooks/`

Keep each customization self-contained, and never commit secrets.

### Pull requests from agents

Agents (Claude Code, Copilot coding agent) open PRs as **`hal9000-agent-bot[bot]`**, not as the human whose machine they run on, so the PR author and the reviewer are different principals. The identity is a GitHub App installed on this repo; the gitignored `.gh-app-identity.json` at the repo root points at its private key. Before every commit, push or `gh pr create`, mint a token in the same shell call (shell state does not survive between agent tool calls):

```sh
eval "$(node scripts/gh-app-token.mjs --env)"          # GH_TOKEN, the bot's git author/committer and a shell-scoped git credential helper for github.com; valid 1 h
git push https://github.com/eiriksf-capgemini/common-ai.git HEAD:<branch>   # HTTPS: the SSH remote ignores the token
gh pr create --draft --title ... --body ...
gh pr view --json author -q .author.login                 # must print app/hal9000-agent-bot
```

A PR that shows a human author was opened without the token; close it and open it again. Setup for a new repo or machine: [skills/github-app-agent-identity](skills/github-app-agent-identity/SKILL.md).

---

<sub>Inspired by <a href="https://github.com/navikt/copilot">navikt/copilot</a>. Thanks to NAV IT for showing how to do this well.</sub>
