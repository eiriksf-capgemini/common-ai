# require-bot-identity

Claude Code `PreToolUse` hook that blocks `git push`, `gh pr create` and `gh pr merge` when they would
run as the human login in a repository that has a GitHub App bot identity (see
[skills/github-app-agent-identity](../../skills/github-app-agent-identity/SKILL.md)). The command must
contain the token eval and push over HTTPS; otherwise the tool call is refused with instructions.

| File | What |
|---|---|
| `require-bot-identity.sh` | the hook; reads the tool call JSON on stdin, exit 2 blocks |
| `require-bot-identity.hook.json` | the `hooks` fragment for `~/.claude/settings.json` (or a project `.claude/settings.json`) |
| `global-claude-md-snippet.md` | the same rule in words, for `~/.claude/CLAUDE.md`, so it also applies where the hook has no trigger file |

Detection: `.gh-app-identity.json` in the working directory or a parent, or at the main checkout's root
when the command runs in a `git worktree`. Repositories without that file are untouched. Needs `jq`.

## Install (user scope)

```sh
mkdir -p ~/.claude/hooks
cp hooks/require-bot-identity/require-bot-identity.sh ~/.claude/hooks/ && chmod +x ~/.claude/hooks/require-bot-identity.sh
# merge the hook into settings.json (keeps everything else; appends to an existing PreToolUse list)
jq -s '.[0] * {hooks: ((.[0].hooks // {}) * {PreToolUse: ((.[0].hooks.PreToolUse // []) + .[1].hooks.PreToolUse)})}' \
  ~/.claude/settings.json hooks/require-bot-identity/require-bot-identity.hook.json > ~/.claude/settings.json.new \
  && mv ~/.claude/settings.json.new ~/.claude/settings.json
cat hooks/require-bot-identity/global-claude-md-snippet.md >> ~/.claude/CLAUDE.md
```

Restart the Claude Code session; hooks are read at start.

## Test

```sh
cd <repo with .gh-app-identity.json>
printf '{"tool_input":{"command":"git push origin HEAD"}}' | sh ~/.claude/hooks/require-bot-identity.sh; echo "exit $?"   # 2
printf '{"tool_input":{"command":"eval \\"$(node scripts/gh-app-token.mjs --env)\\" && git push https://github.com/o/r.git HEAD:b"}}' \
  | sh ~/.claude/hooks/require-bot-identity.sh; echo "exit $?"                                                                     # 0
```

## Limits

The hook inspects the command text, not the process environment: a token exported in an earlier tool
call is invisible to it and would be blocked (re-run the eval; it is cheap). It does not verify the PR
author after the fact; the agent instruction in the snippet does.
