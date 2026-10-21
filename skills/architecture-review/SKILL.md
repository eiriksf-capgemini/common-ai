---
name: architecture-review
description: "Generate or review an Architecture Decision Record (ADR) with a multi-perspective review: architecture, security, platform & cost, and migration. Adapts to the repo's existing ADR conventions."
license: MIT
metadata:
  domain: general
  tags: architecture adr review planning decision-record
---

# Architecture Review — ADR generator and reviewer

Produce an Architecture Decision Record, or review an existing one, with findings from four
perspectives: **architecture**, **security & privacy**, **platform & cost**, and **migration**
(when an existing system changes). The skill decides *what must be considered and recorded*;
it does not make the decision for the team.

Organisation-specific principles are **not** hardcoded. Step 0 discovers them from the repo;
when none exist, [default-principles.md](./references/default-principles.md) applies.

## Workflow

```
Step 0: Discover ADR conventions and principles in the repo
Step 1: Route → generate or review
Step 2: Understand the change (context questions)
Step 3: Multi-perspective review (4 axes)
Step 4: Alternatives (at least two, always including "do nothing")
Step 5: Write or annotate the ADR
Step 6: Action items + review contract
```

## Step 0: Discover conventions

Before writing anything, look for what the repo already does and **follow it**:

| Look for | Use it for |
|---|---|
| `docs/adr/`, `doc/adr/`, `adr/`, `docs/decisions/` | Location. Pick the existing directory; create `docs/adr/` only when none exists. |
| Existing file names (`0001-slug.md`, `ADR-001-slug.md`, `2026-10-20-slug.md`) | Numbering and filename pattern. Match it exactly. |
| Existing ADR headings | Section set and order. Match them; add missing perspectives as new sections rather than renaming theirs. |
| `docs/adr/README.md`, `ARCHITECTURE.md`, `docs/architecture-principles.md`, `CLAUDE.md`, `AGENTS.md` | Organisation principles and the decision process. Quote them in the review instead of the defaults. |
| Open PRs and remote branches (`gh pr list`, `git branch -r`) | **Next free ADR number.** Numbers taken by unmerged work count as taken; say so in the ADR header. |

If no ADRs exist, use the template in [adr-template.md](./references/adr-template.md) and the
defaults in [default-principles.md](./references/default-principles.md).

## Step 1: Route

- User asks to "write", "create", "generate", "document the decision" → **generate** (Steps 2–6)
- User asks to "review", "check", "challenge" an existing ADR or design → **review** (Steps 3, 4 against the document, then 6)
- A design is described with no ADR and no explicit ask → generate, and say so

## Step 2: Context

Answer from the codebase, the conversation and the user. Ask only what cannot be found:

- What is the change? (one sentence)
- Why now? (business need, technical debt, regulatory, incident, cost)
- What happens if nothing is done?
- Who is affected? (teams, services, consumers, end users)
- What constraints apply? (budget, quota, compliance, deadlines, existing contracts)

## Step 3: Multi-perspective review

For each axis: list concerns, risks and recommendations. An axis with nothing to say must
state what it looked at and why that is not a concern.

### Axis 1: Architecture

- Does this fit the system's existing shape, or does it add a second way of doing something?
- Is there a simpler alternative that solves the actual problem?
- Does it add accidental complexity (new tool, new language, new runtime) for marginal gain?
- Does it respect team ownership boundaries and the organisation's decision process?
- Does it reuse platform capabilities already available, or rebuild them?
- Is the decision reversible? What does reversing it cost?

### Axis 2: Security & privacy

> For threat modelling and OWASP checklists, use the `security-review` and `security-owasp`
> skills; this axis checks that the ADR *records* the security posture, not that it is complete.

- Which data is processed? Classification? Personal data?
- Authentication and authorisation: which mechanism, for humans and for workloads?
- Least privilege: are roles and network paths the minimum needed?
- Secrets: where do they live, who can read them, how are they rotated?
- Exposure: what becomes reachable from where (Internet, VPN, cluster-internal)?
- Logging and retention: is personal data kept out of logs and metrics?

### Axis 3: Platform & cost

- Does it run on the platform the team actually operates (cluster, cloud, region, runtime)?
- Resource requirements: CPU, memory, storage, quota headroom, scaling behaviour.
- Standing cost and cost when idle; what can be stopped, scaled to zero or destroyed?
- Observability: metrics, logs, traces, alerts, dashboards; who gets paged?
- Delivery: does CI/CD stay simple? Is the change deployable by the normal path?
- Dependencies on legacy, on-prem or single points of failure.

### Axis 4: Migration (only when an existing system changes)

- Backward compatibility: can old and new run side by side?
- Rollout strategy: big bang, gradual, parallel run; feature toggle?
- Rollback plan without data loss; what triggers it?
- Exit criteria: when is the migration finished and the old path removed?
- Affected consumers identified and informed?
- Reconciliation or verification of data consistency between old and new.
- Decommissioning plan for the old solution.

## Step 4: Alternatives

At least two alternatives plus the chosen one. "Do nothing" is always listed.

| Alternative | Pros | Cons | Fit with principles |
|---|---|---|---|
| A: {chosen} | … | … | … |
| B: {rejected} | … | … | … |
| C: Do nothing | no change cost | {consequence of inaction} | … |

## Step 5: Write or annotate the ADR

**Generate:** fill the repo's own template, or [adr-template.md](./references/adr-template.md).
One decision per ADR. Write for a reader a year from now who was not in the room. Keep it
to one or two pages; deep analysis goes in linked docs.

**Review:** do not rewrite the author's ADR. Produce findings per axis and propose concrete
edits (missing alternative, missing rollback plan, unstated cost). Suggested text is fine;
unrequested wholesale rewrites are not.

## Step 6: Action items

End every generated ADR with concrete, owned action items:

- [ ] Implement the decision — {owner}
- [ ] Update deployment manifests / infrastructure code
- [ ] Update CI/CD
- [ ] Inform affected teams
- [ ] Update documentation (README, runbooks, this ADR's status)
- [ ] Set up observability for the new path

Optional companion: a technical-debt assessment using
[tech-debt-assessment.md](./references/tech-debt-assessment.md), useful when the ADR is about
modernisation or refactoring.

## Boundaries

### ✅ Always

- Follow the repo's existing ADR location, numbering and headings; check unmerged work for taken numbers
- Include at least two alternatives, including "do nothing"
- Report from all four axes (migration may report "not applicable: new system")
- State the standing cost and what can be turned off
- End with owned action items and the review contract

### ⚠️ Ask first

- Decisions that change another team's service, contract or data
- Deviations from the organisation's stated principles or golden paths
- Introducing a new technology, language or runtime
- Changing the status of someone else's ADR

### 🚫 Never

- Decide without a security & privacy assessment
- Skip alternatives; there are always at least two
- Hardcode one organisation's platform or tooling into the template; read it from the repo
- Rewrite an existing ADR wholesale during a review
- Invent an ADR number without checking existing files, open PRs and remote branches

## Review contract

*Axes: the four perspectives in Step 3 — architecture, security & privacy, platform & cost, and
migration where it applies. The verdict is on the chosen alternative and gates the ADR Status:
`BLOCK` means the ADR is not approvable as written.*

The review ends here, in this shape. A review with no output section has not run.

**Judge primary evidence.** The diff, the file, the manifest, the rendered page, the quota
and price you looked up — never your own summary of the change. Resolve the base first, then
cover committed, staged, unstaged **and untracked** changes. Read untracked files in full.

**Every axis reports.** Each axis produces at least one finding, or one line saying what it
inspected and what that evidence does not prove. An axis that says nothing has not looked.

**Report what you inspected.** "No findings in the two files I opened" and "no findings in the
change" are different claims, and only the first one is ever true.

```
Inspected:     <files, queries, URLs, consoles actually opened>
Not inspected: <in scope, not examined, and why>
Findings:      <n blocking, n concerns>
Verdict:       BLOCK | CONCERNS | CLEAN
```

- `BLOCK` — at least one finding that, shipped as written, risks data loss, a security or
  privacy breach, a production incident, an unbounded cost, or a wrong answer to a user.
- `CONCERNS` — no blocking finding, but at least one a maintainer should fix or answer first.
- `CLEAN` — every axis inspected against primary evidence, nothing at either bar. `CLEAN`
  claims only the axes above and the files on the `Inspected` line, and it is wrong if a
  defect is later found in them.

**Not a review:** `LGTM`; restating what the ADR says; cosmetic findings only; judging the
ADR without opening the code or manifests it describes.
