# ADR template

Use only when the repo has no ADRs yet. Otherwise match the existing files (see SKILL.md Step 0).

## File name

`docs/adr/{NNNN}-{short-slug}.md` — four-digit zero-padded sequence, lowercase slug.
Before picking `NNNN`, check existing files **and** open PRs / remote branches for numbers
already taken by unmerged work.

Also keep a `docs/adr/README.md` with three lines: what ADRs are, the format, and the rule
that old ADRs are superseded, never edited.

## Template

```markdown
# ADR {NNNN}: {Title stating the decision, not the topic}

Date: YYYY-MM-DD
Status: Proposed | Accepted | Rejected | Superseded by ADR {n}
Deciders: {team or people}

## Context

{The situation that forces a decision. What is the problem or opportunity? Why now? Which
constraints apply (budget, quota, compliance, deadlines, existing contracts)? What happens
if nothing is done?}

## Decision

We will {concrete choice}.

## Alternatives considered

### A: {name} ✅ chosen
- **Pros:** …
- **Cons:** …
- **Fit with principles:** …

### B: {name}
- **Pros:** …
- **Cons:** …
- **Why not:** …

### C: Do nothing
- **Pros:** no change cost
- **Cons:** {consequence of inaction}

## Assessment

### Security & privacy
- **Data:** {what is processed; classification; personal data yes/no}
- **Authentication / authorisation:** {humans; workloads}
- **Exposure:** {what is reachable from where}
- **Secrets:** {where they live; rotation}

### Platform & cost
- **Runs on:** {platform, region, runtime}
- **Resources:** {CPU, memory, storage, quota headroom}
- **Cost:** {standing cost; cost when idle; what can be stopped or destroyed}
- **Observability:** {metrics, logs, alerts, dashboards}
- **Delivery:** {CI/CD changes}

### Team & migration
- **Affected teams / consumers:** …
- **Rollout:** {big bang / gradual / parallel; feature toggle}
- **Rollback:** {plan; trigger}
- **Exit criteria:** {when the old path is removed}
- *(omit this block for a brand-new system; say "new system, no migration")*

## Consequences

### Positive
- …

### Negative
- …

### Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| … | Low / Medium / High | … | … |

## Action items

- [ ] {task} — {owner} — {due}
- [ ] Update infrastructure code / manifests
- [ ] Update CI/CD
- [ ] Inform affected teams
- [ ] Update README / runbooks; set this ADR to Accepted
```

## Tips

- One decision per ADR. If you need "and", you probably need two ADRs.
- The title states the decision ("Use OpenTofu"), not the topic ("IaC tooling").
- "Do nothing" is always an alternative.
- Write for a future reader who lacks today's context; link evidence (prices, quotas, docs).
- Never edit an accepted ADR's decision; write a new one and mark the old "Superseded by".
