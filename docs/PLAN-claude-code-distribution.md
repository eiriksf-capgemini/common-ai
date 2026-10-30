# Plan: distributing common-ai to Claude Code

Status: draft, 2026-10-25. Decides how the agents, skills, hooks and prompts in this repo
reach every Claude Code (and Copilot) user without copy-paste.

## Premise check: an MCP server cannot deliver skills or agents

The idea was "an MCP server that makes the elements available in Claude Code". Checked
against the current Claude Code documentation (October 2026):

- An MCP server can expose **tools**, **resources** (`@server:...` mentions) and **prompts**
  (which appear as `/mcp__server__prompt` slash commands). That is the whole list.
  https://code.claude.com/docs/en/mcp.md
- **Skills** are discovered from the filesystem only: `~/.claude/skills/`, `.claude/skills/`
  and installed plugins. **Subagents** likewise: `~/.claude/agents/`, `.claude/agents/`,
  plugins, or the `--agents` flag. There is no remote or URL source for either.
  https://code.claude.com/docs/en/skills.md, https://code.claude.com/docs/en/sub-agents.md
- The supported distribution unit is the **plugin**, and the supported distribution channel is
  a **plugin marketplace**: a Git repo with `.claude-plugin/marketplace.json` listing plugins
  (which can live in the same repo). A plugin bundles skills, agents, hooks, commands, MCP
  servers and more. https://code.claude.com/docs/en/plugins/create-marketplace.md
- Organisations pre-install marketplaces and plugins through managed settings
  (`extraKnownMarketplaces`, `enabledPlugins`, `strictKnownMarketplaces`), delivered by MDM
  or from the claude.ai admin console. https://code.claude.com/docs/en/plugins/org.md

So the plan is **marketplace first**. An MCP server still has a place, but as a source of
*tools* (search the catalogue, talk to the platform), not as the delivery mechanism for
skills and agents. Steps 1 to 4 need no MCP at all.

Today the repo is consumed by symlinking skill folders into `~/.claude/skills/`
(`gitops-app-deploy` and `readme-review` on the maintainer's machine) and by copying files
for Copilot. That stays possible throughout.

## Target shape

```
common-ai/
├── .claude-plugin/
│   └── marketplace.json          # name: common-ai; lists the packs below with relative sources
├── plugins/
│   ├── common-ai-core/           # general engineering: conventional-commit, readme-review,
│   │   ├── .claude-plugin/plugin.json      #   no-ai-slop, security-review, security-owasp,
│   │   ├── skills/<name>/SKILL.md          #   api-design, architecture-review, cut-release,
│   │   ├── agents/<name>.md                #   playwright-testing, klarsprak; agents: worker,
│   │   └── hooks/hooks.json                #   local-worker, research, code-review
│   ├── common-ai-platform/       # gitops-app-deploy, observability-setup,
│   │                             #   github-app-agent-identity (+ require-bot-identity hook),
│   │                             #   github-actions-hardening-audit
│   ├── common-ai-backstage/      # backstage-* skills
│   └── common-ai-languages/      # java-to-kotlin, kotlin-app-config, postgresql-review, rust-development
├── copilot/                      # generated .github/ layout for Copilot users (step 6)
├── docs/
└── scripts/                      # gh-app-token.mjs, build-copilot.mjs, validate.mjs
```

Why packs instead of one plugin: each installed plugin's skill descriptions are loaded into
every session, so a Kotlin team should not carry the Backstage skills. Marketplace
`renames` lets us split or merge packs later without breaking installs, so start with these
four and adjust.

Plugin paths must stay inside the plugin directory, which is why the content moves under
`plugins/<pack>/`. The per-element `metadata.json` files are harmless to Claude Code and keep
feeding the README tables and the Copilot generator. Agents keep only the Claude file
(`agents/<name>.md`); the `.agent.md` Copilot variants move to `copilot/` so the plugin's
agent scan does not pick up two files per agent.

## Steps

### 1. Decide and record (half a day)

- Write `docs/adr/0001-plugin-marketplace-not-mcp.md` with the premise check above, the pack
  split and the MCP role. Decisions: pack names, versioning (semver per pack, Git tag
  `<pack>@<version>`), who reviews.
- Done when: ADR merged.

### 2. Restructure into packs and a marketplace (one day)

- `git mv` skills, agents and hooks into `plugins/<pack>/...`; write each
  `.claude-plugin/plugin.json` (`name`, `version`, `description`, `author`, explicit
  `skills`/`agents`/`hooks` paths); write `.claude-plugin/marketplace.json` with
  `owner`, `plugins[].source` as relative paths.
- Hooks: `require-bot-identity.hook.json` becomes `hooks/hooks.json` in the platform pack,
  with the script referenced as `${CLAUDE_PLUGIN_ROOT}/hooks/require-bot-identity.sh`
  instead of `~/.claude/hooks/...`.
- Validate: `claude plugin validate plugins/<pack>` for each pack, then
  `/plugin marketplace add ~/code/common-ai`, install each pack, confirm `/skills` lists
  them and the hook fires.
- Replace the maintainer's symlinks with the installed plugins.
- Done when: all four packs install from the local checkout and every existing skill is
  reachable by name.

### 3. CI: validate and evaluate (one day)

- GitHub Actions on PRs (hardened per our own `github-actions-hardening-audit`): manifest
  validation, SKILL.md frontmatter lint (name matches folder, description present,
  metadata.json consistent), shell lint for hook scripts.
- Eval suites for the three most used skills (`gitops-app-deploy`, `readme-review`,
  `conventional-commit`) under `plugins/<pack>/evals/<case>/` with deterministic graders
  (`tool_used`, `file_exists`, `regex`); run `claude plugin eval plugins/<pack> --json` on
  a weekly schedule and on changes to those skills. Needs an Anthropic API key as a
  repository secret; the run cost is a few dollars.
- Release: a tag per pack bumps `plugin.json` version; CHANGELOG from conventional commits.
- Done when: a PR that breaks a manifest fails CI; the eval job produces a report artifact.

### 4. Roll out (one week, mostly waiting)

- README: the Claude Code row of the "where it goes" table becomes
  `/plugin marketplace add eiriksf-capgemini/common-ai` then `/plugin install
  common-ai-core@common-ai`. Keep the copy-paste table for Copilot.
- Pilot with one team for a week; collect `/skill-doctor` output (per-skill uses and cost over
  7 days) and fix descriptions that never trigger.
- Managed-settings snippet for IT (`docs/managed-settings.md`):
  `extraKnownMarketplaces.common-ai` with `autoUpdate: true`, `enabledPlugins` for
  `common-ai-core@common-ai`, optional `strictKnownMarketplaces` restricting to
  `eiriksf-capgemini/*` plus `anthropics/claude-plugins-official`. Delivery on managed Macs
  is `/Library/Application Support/ClaudeCode/managed-settings.json`.
- Done when: pilot team installed without help; snippet handed to IT.

### 5. MCP server where it earns its place (two to three days, after step 4)

Decided in more detail in cloud-infra ADR 0017: the server lives inside the OpenChoreo
console's Backstage backend (`openchoreo-ai-elements-backend`), the skills themselves are
ingested into the console catalog by a provider reading this repo, and the server exposes
one MCP prompt per skill plus catalog/Azure/cost tools. `openchoreo-api` already serves its
own MCP server for OpenChoreo objects, so this one does not duplicate those. The text below
is the original sketch; where they differ, the ADR wins.

Build `plugins/common-ai-platform/mcp/` (TypeScript, MCP SDK) and reference it from that
pack's `plugin.json` (`mcpServers`, stdio via `npx` for local use). Tools, in priority order:

1. `platform_catalog_search` / `platform_catalog_entity`: query the OpenChoreo console's
   Backstage catalog (projects, components, environments, and the Azure resources once
   cloud-infra ADR 0015 lands) so Claude Code can answer "where does this run" from the
   catalog instead of guessing. Auth: Thunder OIDC bearer, same identity as the portal user.
2. `common_ai_find`: full-text search over this repo's skills, agents and prompts with the
   `metadata.json` examples, returning the install command. This is the "make them
   discoverable" part of the original idea, done the way MCP supports.
3. `prompts/` exposed as MCP prompts, so `/mcp__common-ai__<prompt>` works even for users who
   only connect the server.

Hosted variant: deploy the same server as HTTP on the AKS cluster with `gitops-app-deploy`
(namespace `platform`, ingress under the private CA) for users who cannot run `npx`, and add
it to the managed MCP allow-list. Do this only if the pilot asks for it.

Done when: the catalog tool answers against the live console; the pack installs the server
without manual config.

### 6. Copilot parity (one day)

- `scripts/build-copilot.mjs` renders `copilot/.github/{agents,instructions,prompts,skills}`
  from the packs (agents from `copilot/*.agent.md`, skills copied, instructions and prompts
  as-is) so the Copilot copy-paste source stays current without a second edit.
- Done when: CI fails if the generated tree is stale.

### 7. Measure and prune (ongoing)

- Monthly: `/skill-doctor` from a few users, eval trend from step 3, and the Claude Code
  telemetry already flowing to the console (cloud-infra ADR 0014) for usage by team.
- Skills unused for two months move to an `attic/` pack with `defaultEnabled: false`.

## Open questions

- Does the organisation want the marketplace public (GitHub public repo, as today) or behind
  the GitHub App? Private marketplaces need every user authenticated to GitHub in Claude Code.
- Which team pilots step 4.
- Whether Claude Code telemetry carries skill invocations with enough detail to replace
  `/skill-doctor` sampling; to verify against the OTel event list when step 7 starts.

## Sources

- Plugin components: https://code.claude.com/docs/en/plugins/components.md
- Manifest reference: https://code.claude.com/docs/en/plugins/manifest-reference.md
- Create and host a marketplace: https://code.claude.com/docs/en/plugins/create-marketplace.md,
  https://code.claude.com/docs/en/plugins/host-marketplace.md
- Enterprise plugin management: https://code.claude.com/docs/en/plugins/org.md
- Managed MCP: https://code.claude.com/docs/en/managed-mcp.md
