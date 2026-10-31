---
name: cost-data-audit
description: Audit a repository for the data needed to measure and compare the cost of AI-assisted development — join key from tokens to work items, harness-measured token counts, pass and round labels, review policy recorded as data, findings per round, covariates, outcomes, human cost, cost of controls, prefix size, versioned definitions. Read-only; runs a dependency-free detector that prints a match count for every check, then the agent maps gaps to the project's own tracker and proposes the minimum fields to add. Use when onboarding a project to cost measurement, before a release-cost report, or when the user says "audit our cost data", "can we compare our AI cost with another project", "what should we track", "set up token tracking".
roles: [all]
integrations: [github]
license: MIT
metadata:
  domain: delivery
  tags: cost ai-usage metrics tokens measurement
---

# Cost Data Audit

Checks a repository against eleven requirements for data that lets the cost of AI-assisted development be compared across projects, and reports what is present, partial or missing, with the evidence for each. The reference note carries the reasoning; this skill carries the procedure.

The requirements exist because one measured project (`ugcportal`, four releases) found that cost tracks review rounds rather than model tier or diff size, that resumed agents have a rising per-pass cost, that self-reported token totals double-count, and that the review policy producing the rounds was never recorded. Each check below looks for the field whose absence caused one of those problems.

**Read-only.** The detector never writes to the repository or the tracker. The skill ends with a proposal, not an edit. If the user wants the fields added, that is a separate, explicit change in the project's own tooling. Exempt from the Skill Post-Condition Rule on that basis.

## Requirement → check

| # | Requirement | What the detector measures | Judgement left to the agent |
|---|---|---|---|
| R1 | Join key from request to work item | Share of merged-PR branches containing a real tracker item ID | Whether sessions can inherit the ID (worktree per branch, or must be tagged per request) |
| R2 | Harness-measured tokens by component and model | Telemetry keys in settings or env; usage scripts; how many items carry self-reported `tokens_impl` | Whether the usage script reads transcripts (measured) or agent reports (self-reported) |
| R3 | Pass and round labels, fresh vs resumed | `tokens_qa_rN`, `tokens_impl_passes`, any fresh/resumed field | Whether the orchestrator could stamp fresh/resumed on each pass |
| R4 | Review policy as data | Review- or process-named docs carrying both `severity` and `round` terms | Cap, blocking severities, lenient band, reviewer identity, effective dates |
| R5 | Findings per round by severity and family | `findings_rN` fields; per-item `severity` field as a weaker signal | Whether the reviewer already writes a verdict the field can ride on |
| R6 | Covariates | Coverage of `model`, `model_effort`, `cc_type`, `cc_scope`, criteria, PR link | Whether the routing rule assigning tier is written down |
| R7 | Outcome | Fix-typed items, `discovered-from` links, revert commits | Whether a fix can be traced to the merged item that caused it |
| R8 | Human cost | Handback or manual-merge fields; doc mentions; derivable wall-clock | What the humans actually do that no field records |
| R9 | Controls tracked with cost | Items carrying `retro_source`, `audit`, `gate`, `control` markers | Which audits and gates run that have no item at all |
| R10 | Project context | Tracked lines, always-loaded prefix bytes and approximate tokens, `schema_version` | Stack, team size, orchestrator type, harness version |
| R11 | Versioned definitions | Definition, glossary, schema or metric files under `docs/` | Whether round, pass, finding and severity are defined anywhere |

The detector's field names are `ugcportal`'s. On a project with another tracker, pass `--items` with a JSON array of work items (each carrying a `metadata` object) and read the `metadata_fields` block in the `--json` output to see what the project does call these things before judging a "missing".

## Run it (paths relative to this skill's directory)

```bash
./detect.py <repo-root>
./detect.py --json <repo-root> > /tmp/cost-data-audit.json
./detect.py --items items.json <repo-root>
```

Python 3 standard library only. Uses `bd` if a `.beads/` directory exists and `gh` for merged-PR branch names, falling back to `git branch -r`. Exit 0 on a completed scan, 2 if the target is not a git repository.

Every evidence line prints its match count. A zero in the report is a counted zero. If a line reads `0 of 0`, the tracker was not detected and the row is `unknown`, not `missing`.

**Verified on 2026-10-15** against `ugcportal` at `e3eb5f2` (482 items): R1, R4 and R6 present; R2, R3, R5, R7, R8, R9 and R10 partial; R11 missing. Against this vault as a control (no tracker): nothing present, R1, R7 and R11 missing, the four tracker-dependent rows unknown, and R2 partial because the vault carries its own usage script. A detector that says the same thing about both repositories is broken; re-run both if the script changes.

## After the detector

The detector finds fields. The agent does three things it cannot.

1. **Translate.** Map the project's own vocabulary onto the eleven requirements. A tracker that stores `review_pass_3_tokens` satisfies R3 as well as `tokens_qa_r3` does. Read the `metadata_fields` block before calling anything missing.
2. **Price the gap.** For each missing or partial row, say what the project cannot answer without it, in one sentence, using the reference note's findings. "Without R5 you cannot test whether round-1 findings predict round 4+, which is the one hypothesis that would move the lever from sizing to pre-review."
3. **Propose the minimum.** One table: requirement, field or artefact to add, who writes it, when. The reference note's § Minimum schema is the ceiling; propose the smallest subset that closes the project's own gaps. Typical additions, in order of effort:
   - Branch name carries the item ID (R1), a naming rule.
   - `findings_rN="f1:3 f2:0 f3:1 f4:0 med:1 low:3"` written by the reviewer with its verdict (R5), one metadata write per round.
   - `agent_mode: fresh|resumed` stamped by the orchestrator per pass (R3).
   - A `docs/process/definitions.md` with a `schema_version`, defining round, pass, finding, severity, fresh, resumed, start and end (R11).
   - Telemetry export enabled in the harness settings so tokens come from the harness rather than the agent (R2). Confirm the harness's current mechanism against its documentation before naming an environment variable.
   - A `control: true` flag on items that are audits, gates or retrospectives (R9).

## Report

One file, `/tmp/cost-data-audit-<repo>.md` or wherever the user asks, with:

- a one-line verdict: how many of eleven present, partial, missing, unknown;
- the detector's table verbatim, including every match count;
- the translation notes, where the project's names differ;
- the proposal table;
- which of the three open questions in the reference note this project could answer once the gaps close.

Do not add a per-item rounds estimate to any proposal. No attribute known at dispatch predicted rounds on the measured project, and a guessed field is read as a measurement.

## Background

The eleven requirements come from a 2026 investigation of AI usage economics on one measured project (ugcportal, four releases). The detector encodes them so that other repositories can be audited the same way and compared with it.
