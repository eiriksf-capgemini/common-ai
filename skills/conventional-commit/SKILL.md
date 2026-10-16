---
name: conventional-commit
description: Generate conventional commit messages with project-relevant scopes and breaking-change format
license: MIT
metadata:
  domain: general
  tags: git commit conventional-commits changelog
---

# Conventional Commit Skill

Generate commit messages following the Conventional Commits specification, with example scopes and breaking-change format.

## Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

## Types

| Type | Usage |
|---|---|
| `feat` | New functionality |
| `fix` | Bug fix |
| `docs` | Documentation-only changes |
| `style` | Formatting, semicolons, etc. (no code change) |
| `refactor` | Code that neither fixes a bug nor adds a feature |
| `perf` | Performance changes |
| `test` | Adding or fixing tests |
| `build` | Build system or dependency changes |
| `ci` | CI configuration changes |
| `chore` | Other changes that don't affect code |

## Example scopes

```
feat(orders): add support for partial refunds
fix(auth): fix token validation for the OIDC client
docs(api): update OpenAPI spec for the orders endpoint
refactor(repository): use CTE for better readability
test(controller): add integration test with MockOAuth2Server
build(deps): upgrade Spring Boot to 3.4.1
ci(deploy): add prod deploy step
perf(db): add index on customer_id
chore(deploy): update resource limits
```

## Breaking Changes

```
feat(api)!: change response format for the orders endpoint

BREAKING CHANGE: The `orderDate` field has been renamed to `createdAt`.
Consumers must update their parsing.
```

## Rules

- First line: max 72 characters
- Use imperative form: "add", not "added" or "adds"
- Don't end with a period
- Use Norwegian or English consistently within the project
- Reference Jira/GitHub issue in footer: `Closes #123` or `Refs PROJ-1234`

## Examples

```bash
# Simple feature
git commit -m "feat(application): add validation of national identity number"

# Bugfix with reference
git commit -m "fix(auth): handle expired refresh token

The refresh token was not renewed upon expiration, which caused
users to be logged out without warning.

Fixes #456"

# Dependency update
git commit -m "build(deps): upgrade postgresql driver to 42.7.4"

# Breaking change
git commit -m "feat(api)!: remove deprecated /api/v1/order endpoint

BREAKING CHANGE: /api/v1/order has been removed. Use /api/v2/order."
```

## Analyzing Staged Changes

To generate a commit message, analyze staged changes:

```bash
git diff --cached --stat        # Overview of changed files
git diff --cached               # Detailed diff
```

Based on the diff:
1. Identify **type** (feat/fix/refactor/etc.)
2. Identify **scope** (which module/domain)
3. Write short, precise description
4. Add body if the change needs explanation
5. Add `BREAKING CHANGE` footer if the API changes
