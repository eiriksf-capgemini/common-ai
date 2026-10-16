---
name: github-app-agent-identity
description: Give coding agents their own GitHub identity via a GitHub App, so bot-authored commits, PRs and reviews are attributed to <app>[bot] rather than the human's account, and an automated reviewer is a different principal from the PR author. Ships a dependency-free token helper (gh-app-token.mjs) that mints one-hour installation tokens and prints the git/gh env to eval. Use when setting up agent-driven PR flows on a new repo, when a review pipeline reports "author equals reviewer", when a bot cannot approve its own PR, or when the user says "separate identity for agents", "bot account for Claude", "agents should not commit as me", "GitHub App token for agents".
license: MIT
metadata:
  domain: delivery
  tags: github github-app identity agents security
---

# GitHub App identity for coding agents

Gives subagents a second GitHub principal, `<app-slug>[bot]`, by minting short-lived installation tokens from a GitHub App you own. The agent pushes and opens PRs as the bot; the human login stays on the reviewing side.

**This skill mutates external state** (creates a GitHub App, pushes a probe commit) and ends with a post-condition check: observe the PR author on GitHub, not the tool's exit code.

## Why a GitHub App rather than a second user or a PAT

A second user account costs a seat on paid orgs, needs its own 2FA, and its PAT is a long-lived secret with the whole account's reach. A GitHub App has no seat, is installed on exactly the repos you select with exactly the permissions you tick, and its installation tokens expire after one hour. The bot login carries a `[bot]` suffix, so `gh pr view --json author` and the commits API tell the two principals apart without parsing. The one thing an app token cannot do is call `GET /user`; it returns 403, so any script that resolves "who am I" that way must run as the human, which is the division of labour this skill wants anyway.

## Steps

### 1. Create and install the app (human, in the browser)

GitHub Settings → Developer settings → GitHub Apps → New GitHub App. Settings that matter:

- **Name**: becomes the slug and the bot login, `<slug>[bot]`. Pick something that reads well in a PR author column.
- **Webhook**: untick Active. No URL needed.
- **Repository permissions**: Contents read and write, Pull requests read and write, Issues read and write, Metadata read (forced). Leave Workflows unset unless agents must edit `.github/workflows/`; without it a bot push touching workflows is rejected, which works as a guard.
- **Where can this app be installed**: Only on this account.

After creating: note the **Client ID** (`Iv23li...`, not a secret) and **App ID**. Generate a private key; the `.pem` downloads once. Then Install App → choose the account → Only select repositories → pick the repo. The **installation id** is the number in the resulting URL `.../settings/installations/<id>`.

### 2. Store the key and the config, both gitignored

```bash
mv ~/Downloads/<slug>.*.private-key.pem ./<slug>.pem && chmod 600 ./<slug>.pem
grep -qx '\*.pem' .gitignore || echo '*.pem' >> .gitignore
grep -qx '.gh-app-identity.json' .gitignore || echo '.gh-app-identity.json' >> .gitignore
cat > .gh-app-identity.json <<JSON
{ "clientId": "<client id>", "installationId": "<installation id>", "privateKeyPath": "./<slug>.pem" }
JSON
git ls-files -z | tr '\0' '\n' | grep -Ei '\.pem$|gh-app-identity' && echo "TRACKED SECRET, stop" || echo "nothing tracked"
```

The last line proves the match count before believing the zero: it must print `nothing tracked`, and a `.pem` ever appearing in `git ls-files` is a stop.

### 3. Drop the helper into the repo

Copy `gh-app-token.mjs` from this skill directory to `scripts/gh-app-token.mjs` (or wherever the repo keeps tooling). This repo already carries a copy at `scripts/gh-app-token.mjs` for its own pull requests. Node 18+, no dependencies. Three modes:

| Command | Prints | Use |
|---|---|---|
| `node scripts/gh-app-token.mjs` | the token only | piping into `GH_TOKEN=...` |
| `node scripts/gh-app-token.mjs --env` | `export` lines for `GH_TOKEN`, `GITHUB_TOKEN`, `GIT_AUTHOR_*`, `GIT_COMMITTER_*`, a shell-scoped credential helper, `# expires` | `eval "$(node scripts/gh-app-token.mjs --env)"` at the start of an agent's shell |
| `node scripts/gh-app-token.mjs --check` | bot login, user id, commit email, repos reachable; the token is minted and discarded | step 4, and whenever auth looks wrong |

Unknown arguments exit 1 rather than falling through to the token-printing default, so a typo of `--check` cannot print a live token. The config file is found in the current directory or the nearest parent, and a relative `privateKeyPath` resolves against the file's own directory, so the helper works from any directory inside the repo. Everything spliced into an `export` line is allowlisted first (`[A-Za-z0-9._-]` for the token, `<slug>[bot]` for the login, digits for the id, ISO-8601 for the expiry). A value that fails the allowlist exits 1 with nothing on stdout, so the `eval` is safe against a hostile or malformed API response. Error paths redact the token from any message before printing.

### 4. Verify the identity before wiring anything

```bash
node scripts/gh-app-token.mjs --check
```

Expect your repo in `repositories:` and the login you chose. Then prove attribution end to end with a probe push on a throwaway branch:

```bash
eval "$(node scripts/gh-app-token.mjs --env)"
git switch -c probe/bot-identity && git commit --allow-empty -m "chore: probe bot identity"
git push https://github.com/<owner>/<repo>.git HEAD:probe/bot-identity
gh api repos/<owner>/<repo>/commits/$(git rev-parse HEAD) -q '.author.login, .committer.login'
git push https://github.com/<owner>/<repo>.git --delete probe/bot-identity
```

Both lines must print `<slug>[bot]`. The push URL is HTTPS on purpose: an SSH remote authenticates with the human's key and ignores the token, so a push to `origin` over SSH silently lands as the human. The `--env` output also resets git's credential-helper list for github.com before adding its own, so a global helper such as osxkeychain or Git Credential Manager holding the human's HTTPS credentials cannot answer first. If the repo has a pre-push hook that runs the test suite, run the probe from a checkout that has `node_modules`; the hook fails locally before GitHub sees anything.

### 5. Wire the agents

- **Implementer / worker that pushes and opens PRs**: run `eval "$(node scripts/gh-app-token.mjs --env)"` before the first `git push` or `gh pr create`, and push to the HTTPS URL. Re-run the eval if a session passes the `# expires` time; a 401 on push near the end of a long run means the token expired.
- **Reviewer**: stays on the human `gh` login. Do not export the bot env in the reviewing shell. A bot cannot approve its own PR, and `gh api user` returns 403 under an installation token, so a reviewer running as the bot fails with a visible error.
- **Any "who am I" check** in review tooling should exit with an error when `gh api user` returns nothing; an empty login would otherwise match no marker and report every chain as forged.
- Record the mapping (client id, installation id, bot login, user id, where the PEM lives, what is and is not granted) in the repo's agent memory so the next session does not rediscover it.

### 6. Post-condition

After the first real bot-authored PR, observe the artifact, not the tool's exit code:

```bash
gh pr view <n> --json author -q '.author.login'      # <slug>[bot]  (gh may print the login with or without the suffix; record what it actually printed)
gh api repos/<owner>/<repo>/pulls/<n>/commits -q '.[].author.login' | sort -u
```

Report the observed login verbatim. If either prints the human login, the wiring is incomplete; the usual cause is a push over SSH.

## Pitfalls met in practice

| Symptom | Cause | Fix |
|---|---|---|
| `GitHub returned a token with unexpected characters` on every run | Allowlist written against a synthetic `ghs_` + base62 fixture; real tokens are ~383 chars with two `.` | Allowlist admits `.` (already in this helper). Test fixtures must copy the observed shape of real tokens. |
| `gh api user` → 403 `Resource not accessible by integration` | Expected for installation tokens | Not a broken token. Resolve identity on the human side. |
| Push succeeds but commits show the human as author | SSH remote, or `GIT_AUTHOR_*` not exported | Push to the HTTPS URL with the exported env. |
| Push rejected touching `.github/workflows/` | App lacks Workflows write | Intended guard; a human pushes workflow changes. |
| `eval` of `--env` clobbers an existing `GIT_CONFIG_COUNT` | Caller already uses env-config | The helper detects this and prints a comment and omits the helper lines; push with `x-access-token:$GH_TOKEN@` basic auth in that shell. |
| Pre-push hook fails from a bare worktree | Hook runs lint/test/build in the pushing worktree | Push from a checkout with dependencies installed. |

## Limits worth stating

The separation is organisational. Any process on the same machine can read the PEM and mint a bot token, so a misbehaving reviewer could still forge a chain. What this buys is that the *accidental* case, two roles sharing one login because nobody set up a second one, no longer happens, and that a review tool can tell author from reviewer with one field. Tokens last one hour and nothing refreshes them. The bot's reach is exactly the installation's permissions; granting more is a human action in GitHub settings, never something the helper does.
