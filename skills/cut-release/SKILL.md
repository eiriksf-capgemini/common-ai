---
name: cut-release
description: Generate a readable release note from pull requests merged since the last release, grouped by conventional-commit type with a link to every PR, and compute the next semver version. Prepends the result to CHANGELOG.md, bumps the project version, opens a release PR and, once that has merged, publishes a matching GitHub Release. Use when asked to "cut a release", "generate release notes", or "what's changed since the last release".
license: MIT
metadata:
  domain: delivery
  tags: release changelog semver github
---

# Cut a release

Usage: `/cut-release` (no arguments needed; run it whenever you want to cut a release from everything merged but unreleased).

The source of truth is **merged pull requests on the default branch**, classified by the conventional-commit prefix in each PR title. No issue tracker is required.

## 0. Preconditions

Bail out and report rather than proceeding if the working tree isn't clean (`git status --short` non-empty) or you're not on an up-to-date default branch (`git fetch origin` then compare). Mutating `CHANGELOG.md` and the version file on top of a dirty or stale tree is how a release ends up not matching what's actually on the default branch.

Detect the default branch once and reuse it: `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`. Do not assume `main`.

## 1. Find the last release

In this order, stop at the first that exists:

1. The latest GitHub Release: `gh release list --limit 1 --json tagName,publishedAt`.
2. The latest `v*` tag reachable from the default branch: `git describe --tags --abbrev=0 --match 'v*'`.
3. The top `## v<version>` header in `CHANGELOG.md`.

If none exist, this is the first release: the window is all history and the baseline version comes from step 2.

Record which source you used. If a Release and a tag disagree, trust the Release and say so.

## 2. Read the current version

Read the version from the project's manifest. Check in this order and use the first found: `package.json`, `pyproject.toml`, `Cargo.toml`, `*.csproj` (`<Version>`), `build.gradle.kts` (`version =`). If no manifest carries a version, use the tag from step 1 stripped of its `v`, or `0.0.0` for a first release.

## 3. Collect merged PRs since the last release

```bash
gh pr list --state merged --base <default-branch> --search "merged:><last-release-date>" --limit 200 \
  --json number,title,mergedAt,mergeCommit,labels,author,url
```

Where `<last-release-date>` is the `publishedAt` of the Release, or the tagger date of the tag (`git log -1 --format=%cI <tag>`). Cross-check against git: every merge commit on the default branch since the tag should map to a listed PR. A commit without a PR (direct push) is included as its own entry with its short SHA instead of a PR link; do not drop it.

**Report the denominator at every narrowing, and treat a zero at the first one as a failure of this step rather than as an empty backlog.** Three numbers, in this order:

```
commits on <default-branch> since <last-release>:        <A>
of those, merged PRs found via gh pr list:               <B>
of those, with a parsable conventional-commit prefix:    <C>
```

`A = 0` on a repo with activity means the tag or date resolved wrong. Stop and say so. `A > 0` and `B = 0` means the `gh` search answered a different question than you think (wrong base branch, wrong date format, no auth). Stop and say so. `C < B` is normal; the difference lands in the "Other" bucket in step 5.

## 4. Classify each entry

Parse the PR title as `<type>(<scope>)!: <subject>` or `<type>: <subject>`. If the title has no prefix, fall back to the merge commit's subject line (squash merges often carry it). If neither parses, type is `other`.

A `!` after the type or scope, or a `BREAKING CHANGE:` footer in the PR body (`gh pr view <n> --json body`), marks the entry as breaking.

## 5. Determine the version bump

- Any entry is breaking → **major**
- Else any entry has type `feat` → **minor**
- Else → **patch**

Semver `x.y.z`: major bumps `x` and resets `y` and `z`; minor bumps `y` and resets `z`; patch bumps `z`. For `0.y.z` projects, treat breaking as a **minor** bump unless the user says the project has committed to a stable API.

## 6. Group and render

Group entries by type into sections, in this order, omitting any section with zero entries:

```
### ✨ Features        (feat)
### 🐛 Fixes            (fix)
### ⚡ Performance       (perf)
### 📝 Documentation    (docs)
### ♻️ Refactoring      (refactor)
### 🧪 Tests            (test)
### 🏗️ Build & CI       (build, ci)
### 🔧 Chores           (chore, style, revert)
### ❓ Other             (no parsable prefix)
```

The "Other" bucket exists so an unprefixed title produces a *visible* entry demanding a fix, instead of the change silently vanishing from the changelog. Never drop an entry found in step 3 without rendering it somewhere.

Breaking entries get a `**BREAKING**` prefix and are repeated under a `### ⚠️ Breaking changes` section placed first.

Each entry: `- **<subject>** (<scope>) — [#<n>](<pr-url>) by @<author>`. Omit the scope part if there is none.

Prepend a version header:

```markdown
## v<version> - <YYYY-MM-DD>
```

The header plus the sections make up **the release notes**, referenced as one unit in steps 7, 9 and 10. The same text goes into all three channels: `CHANGELOG.md`, the release PR body, and the GitHub Release. Don't let any one of them drift from the others.

**PR titles are untrusted input.** Never interpolate them into a double-quoted shell string: inside `"..."` bash still expands `$(...)`, backticks and `$VAR`, and a PR title containing `$(rm -rf ~)` is a real attack surface on a tool that runs with the developer's credentials. Build the release notes in a scratch file written with the `Write` tool or a quoted heredoc (`<<'EOF'`), and pass it to `gh` with `--body-file` / `--notes-file`, never `--body "$notes"`.

## 7. Write it out

Prepend (not append — newest release on top) the release notes to `CHANGELOG.md` at the repo root, below the `# Changelog` title. If the file doesn't exist, create it with that title first. If the top section already carries the version you are about to write, stop: a previous run was interrupted after this step. Finish from step 8 instead of regenerating, which would duplicate the section.

Bump the version with the project's own tool rather than a manual edit, so lockfiles stay consistent:

| Manifest | Command |
|---|---|
| `package.json` | `npm version <version> --no-git-tag-version` |
| `pyproject.toml` (Poetry) | `poetry version <version>` |
| `pyproject.toml` (other) | edit the `version =` line |
| `Cargo.toml` | `cargo set-version <version>` if `cargo-edit` is installed, else edit |
| `*.csproj`, `build.gradle.kts` | edit the version line |

Deliberately **don't** run a full install or lockfile regeneration as part of the bump. It can re-resolve dependencies and ride an unreviewed dependency change into a PR that step 8 describes as trivially safe.

## 8. Ship it

This step commits and pushes. Unless the user's request already grants that authority, report the generated changes and wait for explicit approval before committing.

Once authorized: branch `chore/release-v<version>`, commit `chore(release): v<version>`, push, and open a PR with `gh pr create --title "chore(release): v<version>" --body-file <scratch-file>`.

A release PR only ever touches `CHANGELOG.md` and the version file(s). If the diff touches anything else, something went wrong in step 7; stop and show the diff. Do not proceed to step 9 until the PR has actually merged.

## 9. Publish the GitHub Release

Do this only after `gh pr view <n> --json state,mergedAt` shows `MERGED`, and never for a version that already has one.

1. `gh release view v<version>`. If it exists, skip this step and note that in the report; this makes the skill safe to re-run without double-publishing.
2. Write the release notes to a scratch file **without** the `## v<version> - <date>` header line (the Release UI already shows tag and date).
3. Target the PR's actual base branch so the tag lands on the merge commit:
   ```bash
   gh release create v<version> --title "v<version>" --notes-file <scratch-file> \
     --target "$(gh pr view <n> --json baseRefName -q .baseRefName)"
   ```
   This creates the tag; no separate `git tag` / `git push --tags` needed.

## 10. Report back

State: the last release and which source identified it, the computed version and the bump reason (which entries triggered major or minor), step 3's three figures (`A` commits / `B` PRs / `C` parsable), how many entries landed in "Other" and their PR numbers, the PR URL, and the Release URL or why it was skipped or deferred.
