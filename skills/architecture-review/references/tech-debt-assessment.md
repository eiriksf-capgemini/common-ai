# Technical-debt assessment

Optional companion to an ADR about modernisation or refactoring. Produces a prioritised
debt table with a recommended action per item.

## Identification

| Area | Questions |
|---|---|
| Dependencies | Outdated dependencies with known vulnerabilities? Unsupported runtime versions? |
| Architecture | Modules with unclear responsibility or tight coupling? Two ways of doing the same thing? |
| Code | Duplicated logic, oversized files, missing abstractions where the same change hits many places? |
| Tests | Low coverage in critical business logic? Missing integration or contract tests? |
| Infrastructure | Outdated base images, missing observability, slow or flaky CI/CD, manual steps? |
| Documentation | Missing ADRs for important decisions? Stale runbooks or READMEs? |
| Security | Outdated auth mechanism? Personal data in logs? Over-broad roles or network paths? |
| Cost | Resources running idle? Oversized instances? Standing cost without an owner? |

## Prioritisation

```
Priority = Severity × Frequency × Blast radius

Severity (1-3):      1 annoying but manageable · 2 noticeably slows development · 3 blocks features or is a security/cost risk
Frequency (1-3):     1 rarely (yearly) · 2 regularly (monthly) · 3 often (weekly or daily)
Blast radius (1-3):  1 one component · 2 several components in one service · 3 across services/teams
```

## Output

```markdown
| # | Debt item | Sev. | Freq. | Radius | Priority | Recommended action |
|---|-----------|------|-------|--------|----------|--------------------|
| D1 | Outdated auth library with CVE | 3 | 3 | 2 | 18 | Upgrade to the current major; add Dependabot |
| D2 | No tests around pricing calculation | 2 | 3 | 1 | 6 | Add characterisation tests before refactoring |
| D3 | Duplicated validation logic in three services | 1 | 2 | 2 | 4 | Extract to a shared module |
```

Deliverable: the table sorted by priority, each row with an owner and a recommended action.
