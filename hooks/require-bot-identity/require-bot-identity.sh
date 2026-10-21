#!/bin/sh
# Claude Code PreToolUse hook (matcher: Bash).
# Blocks `git push`, `gh pr create` and `gh pr merge` that would run as the human login in a
# repository that has a GitHub App bot identity (.gh-app-identity.json at the repo root, or at
# the main checkout's root when running from a worktree). The command must mint the token in the
# same shell call, before the push, and push over HTTPS; SSH remotes ignore GH_TOKEN.
# Exit 0 = allow, exit 2 = block (stderr is shown to the agent). Needs jq and git.
set -u
input=$(cat)
[ -n "$input" ] || exit 0

# Cheap pre-filter on the raw JSON, so a machine without jq fails closed only for relevant calls.
printf '%s' "$input" | grep -Eq 'push|pr[[:space:]]+(create|merge)' || exit 0
if ! command -v jq >/dev/null 2>&1; then
  echo "require-bot-identity: jq is not installed, so the command cannot be inspected. Install jq (brew install jq) or remove the hook from ~/.claude/settings.json." >&2
  exit 2
fi
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null) || { echo "require-bot-identity: cannot parse the hook input" >&2; exit 2; }
[ -n "$cmd" ] || exit 0

# Command-word detection runs on the text with quoted strings removed, so a commit message or an
# echo that mentions "git push" does not trigger it. Option values (-C dir, -c k=v, -R o/r) are skipped.
OPT='(-[^[:space:]]+([[:space:]]+[^-[:space:]][^[:space:]]*)?[[:space:]]+)*'
GIT_PUSH="(^|[^[:alnum:]_./-])git[[:space:]]+${OPT}push([^[:alnum:]_-]|\$)"
GH_PR="(^|[^[:alnum:]_./-])gh[[:space:]]+${OPT}pr[[:space:]]+(create|merge)([^[:alnum:]_-]|\$)"
strip() { printf '%s' "$1" | sed -e 's/"[^"]*"//g' -e "s/'[^']*'//g"; }
bare=$(strip "$cmd")
printf '%s' "$bare" | grep -Eq "$GIT_PUSH|$GH_PR" || exit 0

# Where does the command run? The hook's cwd, adjusted for a leading `cd <dir> &&`.
cwd=$(printf '%s' "$input" | jq -r '.cwd // ""' 2>/dev/null)
[ -n "$cwd" ] && [ -d "$cwd" ] || cwd=$PWD
cdt=$(printf '%s' "$cmd" | sed -nE 's/^[[:space:]]*cd[[:space:]]+("([^"]*)"|([^[:space:];&|]+)).*$/\2\3/p')
case "$cdt" in "~") cdt=$HOME ;; "~/"*) cdt=$HOME/${cdt#\~/} ;; esac
if [ -n "$cdt" ]; then
  newcwd=$(cd "$cwd" 2>/dev/null && cd "$cdt" 2>/dev/null && pwd) && cwd=$newcwd
fi

find_identity() {
  d=$1
  while [ -n "$d" ] && [ "$d" != "/" ]; do
    [ -f "$d/.gh-app-identity.json" ] && { printf '%s' "$d/.gh-app-identity.json"; return 0; }
    d=$(dirname "$d")
  done
  return 1
}
identity=$(find_identity "$cwd") || {
  common=$(git -C "$cwd" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) \
    || common=$(cd "$cwd" 2>/dev/null && git rev-parse --git-common-dir 2>/dev/null) || exit 0
  [ -n "$common" ] || exit 0
  case "$common" in /*) ;; *) common=$cwd/$common ;; esac
  identity=$(find_identity "$(cd "$(dirname "$common")" 2>/dev/null && pwd)") || exit 0
}

# The token must be minted by an eval of the helper, in this command, before the first push/PR word.
EVAL='eval[[:space:]]+"\$\(([^)]*&&[[:space:]]*)?node[[:space:]]+[^)]*gh-app-token\.mjs[[:space:]]+--env\)"'
evalpos=$(printf '%s' "$cmd" | grep -obE "$EVAL" | head -1 | cut -d: -f1)
trigpos=$(printf '%s' "$cmd" | grep -obE "$GIT_PUSH|$GH_PR" | head -1 | cut -d: -f1)
if [ -z "$evalpos" ] || { [ -n "$trigpos" ] && [ "$evalpos" -gt "$trigpos" ]; }; then
  cat >&2 <<MSG
Blocked by require-bot-identity: this repository has a bot identity ($identity) and the command would push or open a PR as the human login.
Start the SAME command with:  eval "\$(node scripts/gh-app-token.mjs --env)"   (shell state does not persist between tool calls; the eval must come before the push)
and push over HTTPS:          git push https://github.com/<owner>/<repo>.git HEAD:<branch>
From a worktree add:          gh pr create --head <branch>
Then verify:                  gh pr view <n> --json author -q .author.login   -> app/<bot-slug>
MSG
  exit 2
fi

# Every push segment must name an HTTPS URL; a remote name is usually SSH, which ignores the token.
bad=$(printf '%s\n' "$cmd" | awk '{gsub(/&&|\|\||[;|]/,"\n"); print}' | while IFS= read -r seg; do
  if printf '%s' "$(strip "$seg")" | grep -Eq "$GIT_PUSH" && ! printf '%s' "$seg" | grep -Eq 'https://[^[:space:]"'"'"']+'; then echo bad; fi
done)
if [ -n "$bad" ]; then
  cat >&2 <<MSG
Blocked by require-bot-identity: the token is minted but a push goes to a remote name, which usually means SSH, and SSH ignores GH_TOKEN (the push would be attributed to the human).
Push to the HTTPS URL instead:  git push https://github.com/<owner>/<repo>.git HEAD:<branch>
MSG
  exit 2
fi
exit 0
