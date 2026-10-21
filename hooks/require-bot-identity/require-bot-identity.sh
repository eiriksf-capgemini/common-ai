#!/bin/sh
# Claude Code PreToolUse hook (matcher: Bash).
# Blocks `git push`, `gh pr create` and `gh pr merge` that would run as the human login in a
# repository that has a GitHub App bot identity (.gh-app-identity.json at the repo root, or at
# the main checkout's root when running from a worktree). The command must mint the token in the
# same shell call and push over HTTPS; SSH remotes ignore GH_TOKEN and land as the human.
# Exit 0 = allow, exit 2 = block (stderr is shown to the agent). Needs jq and git.
set -u
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0
[ -n "$cmd" ] || exit 0

printf '%s' "$cmd" | grep -Eq '(^|[^[:alnum:]_-])(git[[:space:]]+(-[^[:space:]]+([[:space:]]+[^-][^[:space:]]*)?[[:space:]]+)*push|gh[[:space:]]+pr[[:space:]]+(create|merge))([^[:alnum:]_-]|$)' || exit 0

cwd=$(printf '%s' "$input" | jq -r '.cwd // ""' 2>/dev/null)
[ -n "$cwd" ] && [ -d "$cwd" ] || cwd=$PWD

find_identity() {
  d=$1
  while [ -n "$d" ] && [ "$d" != "/" ]; do
    [ -f "$d/.gh-app-identity.json" ] && { printf '%s' "$d/.gh-app-identity.json"; return 0; }
    d=$(dirname "$d")
  done
  return 1
}

identity=$(find_identity "$cwd") || {
  common=$(git -C "$cwd" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || exit 0
  identity=$(find_identity "$(dirname "$common")") || exit 0
}

if ! printf '%s' "$cmd" | grep -q 'gh-app-token.mjs --env'; then
  cat >&2 <<MSG
Blocked by require-bot-identity: this repository has a bot identity ($identity) and the command would push or open a PR as the human login.
Start the SAME command with:  eval "\$(node scripts/gh-app-token.mjs --env)"   (shell state does not persist between tool calls)
and push over HTTPS:          git push https://github.com/<owner>/<repo>.git HEAD:<branch>
From a worktree add:          gh pr create --head <branch>
Then verify:                  gh pr view <n> --json author -q .author.login   -> app/<bot-slug>
MSG
  exit 2
fi

if printf '%s' "$cmd" | grep -Eq '(^|[^[:alnum:]_-])git[[:space:]]+(-[^[:space:]]+([[:space:]]+[^-][^[:space:]]*)?[[:space:]]+)*push' && ! printf '%s' "$cmd" | grep -q 'https://github.com/'; then
  cat >&2 <<MSG
Blocked by require-bot-identity: the token is minted but the push goes to a remote name, which usually means SSH, and SSH ignores GH_TOKEN (the push would be attributed to the human).
Push to the HTTPS URL instead:  git push https://github.com/<owner>/<repo>.git HEAD:<branch>
MSG
  exit 2
fi
exit 0
