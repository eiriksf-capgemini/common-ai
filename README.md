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

## 🤝 Contributing

1. **Agents**: Add a folder to `agents/` with `<name>.md` for Claude Code. A `<name>.agent.md` for Copilot is welcome but optional
2. **Instructions**: Add `*.instructions.md` to `instructions/`
3. **Prompts**: Add `*.prompt.md` to `prompts/`
4. **Skills**: Add a folder with a `SKILL.md` to `skills/`
5. **Hooks**: Add `*.hook.json` with its script to `hooks/`

Keep each customization self-contained, and never commit secrets.

---

<sub>Inspired by <a href="https://github.com/navikt/copilot">navikt/copilot</a>. Thanks to NAV IT for showing how to do this well.</sub>
