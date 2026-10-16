---
name: github-actions-hardening-audit
description: First-pass security audit of a repo's GitHub Actions workflows against a five-item hardening baseline — SHA-pinned actions, explicit permissions, per-job timeouts, deploy concurrency groups, and the pull_request_target ban. Read-only; produces a findings report scoped to those five items rather than a full linter dump. Use when starting on a new engagement's CI, reviewing a client repo's workflows, or when the user says "audit the workflows", "check our GitHub Actions security", "are our actions pinned", "harden this CI".
license: MIT
metadata:
  domain: security
  tags: github-actions ci security audit
---

# GitHub Actions Hardening Audit

Audits `.github/workflows/` against a five-item hardening baseline and reports five named findings a platform team can act on.

The scoping is the point. `zizmor` has forty-odd audit rules; dumping all of them on a client at first contact buries the five cheap wins under noise you then have to defend. This skill runs zizmor, adds the one baseline check zizmor has no rule for, and reports against the five baseline items only — with the full output kept as an appendix for anyone who wants it.

**Read-only.** It never edits workflows, never pushes, never opens a PR. If the user wants the SHA-pins applied, that is `zizmor --fix` run deliberately by them, not this skill.

## The baseline

| # | Check | Why it matters |
|---|---|---|
| 1 | SHA-pin every `uses:`, never a bare tag | A tag can be moved to malicious code; a commit SHA cannot |
| 2 | Explicit `permissions:` per job, never `write-all` | Limits what a compromised step can do with `GITHUB_TOKEN` |
| 3 | `timeout-minutes` on every job | A hung job burns minutes and blocks queues until the 6-hour default |
| 4 | `concurrency:` on deploy workflows | Two deploys of the same environment racing each other is how prod ends up in an unknown state |
| 5 | Ban `pull_request_target` + head-ref checkout | Runs untrusted fork code with write token and secrets |

## Two things a default `zizmor .` run misses

Both verified against zizmor 1.30.1 on 2026-09-24. They are the reason this skill is more than a wrapper.

1. **`timeout-minutes` has no zizmor audit at all.** Nothing in the rule set covers baseline item 3. `check_timeouts.py` in this skill directory does it.
2. **`concurrency-limits` does not fire at the default `regular` persona.** Baseline item 4 is silently skipped unless you pass `--persona=pedantic`. Confirmed by running both personas over the same repo: `regular` returned three rule types, `pedantic` returned the same three plus `concurrency-limits`.

So a naive `zizmor .` covers three of the five baseline items, not five.

## Baseline item → zizmor rule

| # | Baseline check | Covered by | Persona |
|---|---|---|---|
| 1 | SHA-pin every `uses:`, never a bare tag | `unpinned-uses`, `stale-action-refs`, `ref-version-mismatch`, `impostor-commit` | `regular` |
| 2 | Explicit `permissions:` per job, never `write-all` | `excessive-permissions`, `undocumented-permissions` | `regular` |
| 3 | `timeout-minutes` on every job | **`check_timeouts.py`** (no zizmor rule exists) | — |
| 4 | `concurrency:` on deploy workflows | `concurrency-limits` | **`pedantic` only** |
| 5 | Ban `pull_request_target` + head-ref checkout | `dangerous-triggers`, `ref-confusion`, `template-injection` | `regular` |

Since zizmor v1.20.0 the `unpinned-uses` default is blanket hash-pinning for *all* actions, including `actions/*`. That matches the baseline. If a repo ships its own `zizmor.yml` it can weaken that policy — check for one before trusting a clean item-1 result.

## Run it

**Preflight.** `zizmor --version`. If absent: `brew install zizmor` (also `uv tool install zizmor`, `pipx install zizmor`, `cargo install --locked zizmor`). Confirm before installing anything on a machine that isn't the user's own.

**Online vs offline.** zizmor runs offline unless a token is present, and the offline mode skips the audits that need the GitHub API. Prefer online:

```bash
zizmor --gh-token "$(gh auth token)" --persona=pedantic --format=json-v1 <target>
```

Fall back to `--offline` when there is no token, and say so in the report — a clean item-1 result offline is weaker than one online.

`<target>` can be a local directory, a single workflow file, or an `owner/repo` slug (audits the default branch HEAD; append `@ref` to pin). The slug form means you can audit a client repo without cloning it.

**The timeout check** (paths relative to this skill's directory):

```bash
./check_timeouts.py <target>        # human-readable
./check_timeouts.py --json <target> # machine-readable
```

Takes a repo root (it finds `.github/workflows/` itself), a workflows directory, or individual files. Dependency-free — no PyYAML, because client machines are not yours to install into. Exit 0 = all jobs covered, 1 = at least one job missing, 2 = nothing scanned.

It reports jobs that call a reusable workflow (`jobs.<id>.uses`) separately rather than as findings: that job is a thin caller and the timeout belongs in the called workflow's own jobs. Say this in the report rather than counting them as failures.

**Reading the JSON.** `--format=json-v1` uses **0-based** line numbers in its `row` key, while `--format=plain` and SARIF are 1-based. Add 1 when citing a line, or the report points one line above every finding.

zizmor's exit code encodes severity, not success: 0 = no findings, 11/12/13/14 = findings with highest severity informational/low/medium/high, and 1/2/3 = actual errors. Do not treat non-zero as a crash.

## Report

One markdown file, e.g. `ci-hardening-audit-YYYY-MM-DD.md` in the repo's `docs/` or wherever the engagement keeps findings.

Lead with the count against the five items — "3 of 5 baseline items have findings" — then a section per item that has them, each finding as `path:line` plus a one-line remediation. Items that pass get one line each saying so; a clean item is a result, and the client should see which of the five they already have.

Two things the report must state plainly, because both change how much the clean results are worth: whether the run was online or offline, and whether the repo ships a `zizmor.yml` that narrows any of the rules above.

End with an `## Appendix — full zizmor output` section holding everything outside the five items. It is often where the genuinely interesting finding is (`template-injection` and `artipacked` both show up regularly on repos that pass all five), but it is not what this audit promises, so it goes below the line.

## Related

- [zizmor documentation](https://docs.zizmor.sh) — full audit rule reference.
- [GitHub: Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions) — the upstream guidance the baseline distils.
