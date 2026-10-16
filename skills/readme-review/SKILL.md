---
name: readme-review
description: "Structural review and generation of READMEs adapted to project type: service, library, monorepo or batch job"
license: MIT
metadata:
  domain: general
  tags: readme documentation review scaffold
---

# README Review & Scaffold

Structural review and generation of READMEs adapted to project type. This skill decides **what sections, in what order, at what depth**. It does not polish prose.

## Workflow

```
Step 0: Detect README scope
Step 1: Route → review or generate
Step 2a: Review existing README
Step 2b: Generate new README
```

## Step 0: Detect README scope

Before reviewing or generating, determine **what kind of README** this is. Use file location and nearby manifests:

| Scope | Signals | Example |
|-------|---------|---------|
| **Monorepo root** | Root `README.md`, multiple `apps/` or `packages/`, workspace config | `{org}/{repo}/README.md` with `apps/` dir |
| **Service / API** | Dockerfile, deployment manifests (`k8s/`, `.deploy/`, `infra/`), `main.go` / `Application.kt` / `app.py` | `apps/my-service/README.md` |
| **Library / package** | Published to npm/Maven/PyPI/NuGet, no deployment manifests, exports public API | `libs/shared-utils/README.md` |
| **Batch job** | CronJob manifest, timer-triggered function, scheduled workflow, no HTTP endpoints | `apps/nightly-sync/README.md` |
| **Docs-only** | No source code, only markdown files | `docs/README.md` |

If scope is unclear, **ask the user**.

## Step 1: Route

- **Existing README** + user says "review", "check", "improve" → **Step 2a**
- **No README** or user says "create", "scaffold", "generate" → **Step 2b**
- **Ambiguous** → check if `README.md` exists in the target directory

## Step 2a: Review existing README

### 2a.1 Check sections against spec

Read the existing README. For each section in the spec for this project type (see [section-spec.md](./references/section-spec.md)):

| Status | Meaning |
|--------|---------|
| ✅ OK | Section exists with substantive content |
| ⚠️ Weak | Section exists but is thin, outdated, or misplaced |
| ❌ Missing | Required section is absent |
| — | Section not applicable for this project type |

### 2a.2 Check for anti-patterns

Scan for structural anti-patterns (see [anti-patterns.md](./references/anti-patterns.md)). Flag only patterns that are actually present.

### 2a.3 Output

```markdown
## README review — {project name}

**Scope:** {service / library / monorepo / batch job}

### Section check

| Section | Status | Notes |
|---------|--------|-------|
| Title + one-liner | ✅ | — |
| Quick start | ❌ | No runnable commands found |
| ... | ... | ... |

### Anti-patterns found

- **{Pattern name}**: {One-sentence description of what's wrong and how to fix it}

### Top 3 fixes

1. {Most impactful fix}
2. {Second fix}
3. {Third fix}
```

Surface **top 3 fixes** ordered by impact. Don't overwhelm with minor issues.

## Step 2b: Generate new README

1. Pick template from `references/` based on detected scope
2. Fill in what you can detect from the codebase:
   - Project name (from directory or manifest)
   - Tech stack (from `go.mod`, `package.json`, `build.gradle.kts`, `pyproject.toml`, `*.csproj`)
   - Build/test commands (from `Makefile`, `package.json` scripts, `Taskfile.yml`, `justfile`, `.mise.toml`)
   - Endpoints (from route definitions)
   - Config (from environment variable usage)
3. Mark remaining placeholders with `{TODO: description}`
4. Output the draft README

Templates: [service](./references/template-service.md) · [library](./references/template-library.md) · [monorepo](./references/template-monorepo.md) · [batch job](./references/template-batch-job.md)

## Principles

### Cognitive funneling

Structure README from broad to specific. Readers scan top-down and bail when they have enough information:

1. **Title + one-liner** — what is this? (< 120 characters)
2. **Quick start** — how do I run it? (copy-paste commands)
3. **Details** — API, config, architecture
4. **Meta** — contributing, license, team

> "Your documentation is complete when someone can use your module without ever having to look at its code." — Ken Williams

### README is the front door

README should orient and get people started. Deep content belongs elsewhere:

| In README | In external docs |
|-----------|-----------------|
| One-liner description | Full architecture docs |
| Quick start commands | Detailed runbooks |
| Config table (env vars) | ADRs, threat models |
| API overview or link | Full OpenAPI spec |
| Team + contact channel | Incident response procedures |

### Code over prose

```markdown
# ❌ Prose
You can start the development server by running the development command
using the project's task runner.

# ✅ Code
npm run dev
```

### Fewer sections = less drift

Only include sections you will maintain. An empty "## Roadmap" is worse than no roadmap section. README rots faster than code.

## Boundaries

### ✅ Always

- Detect project scope before suggesting sections
- Check for missing quick start (most common gap)
- Use Missing/Weak/OK status, not numeric scores
- Surface top 3 fixes, not an exhaustive list
- Keep the README's existing language unless asked to change it

### ⚠️ Ask first

- Rewriting large sections of an existing README
- Removing sections that may have historical context
- Changing README language (e.g. Norwegian ↔ English)

### 🚫 Never

- Duplicate content from AGENTS.md or CLAUDE.md into README
- Dump full runbooks, security policies, or ADRs into README
- Add numeric scores or gamified ratings
- Rewrite prose style; this skill handles structure, not language

## Sources

- [Art of README](https://github.com/noffle/art-of-readme) — cognitive funneling
- [Standard Readme](https://github.com/RichardLitt/standard-readme) — section ordering spec
- [Make a README](https://www.makeareadme.com) — practical guide
- [Diátaxis](https://diataxis.fr) — documentation framework (tutorials/how-to/reference/explanation)
- [Readme Driven Development](https://tom.preston-werner.com/2010/08/23/readme-driven-development.html) — write README first

## Review contract

*Axes: the section check (2a.1) and the anti-pattern scan (2a.2). The block below closes the Step 2a report.*

The review ends here, in this shape. A review with no output section has not run.

**Judge primary evidence.** The README file itself and the manifests next to it, never your own summary of the project, and never your memory of what you meant to write. Read untracked and uncommitted files in full: diff output omits them.

**Every axis reports.** Each axis produces at least one finding, or one line saying what it inspected and what that evidence does not prove. An axis that says nothing has not looked.

**Report what you inspected.** "No findings in the two files I opened" and "no findings in the project" are different claims, and only the first one is ever true.

```
Inspected:     <files, manifests, URLs actually opened>
Not inspected: <in scope, not examined, and why>
Findings:      <n blocking, n concerns>
Verdict:       BLOCK | CONCERNS | CLEAN
```

- `BLOCK` — at least one finding that, shipped as written, would send a new developer down a wrong or unsafe path (missing prerequisites that break setup, stale commands, documented features that do not exist).
- `CONCERNS` — no blocking finding, but at least one a maintainer should fix or answer first.
- `CLEAN` — every axis inspected against primary evidence, nothing at either bar. `CLEAN` claims only the axes above and the files on the `Inspected` line, and it is wrong if a defect is later found in them.

**Not a review:** `LGTM`; restating what the README says; cosmetic findings only; reading the README without the manifests it describes.
