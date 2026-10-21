## Git identity for agents

- Never push commits or open pull requests as the human login. In any repository that has a `.gh-app-identity.json` (at the repo root, or at the main checkout when working from a worktree), mint the GitHub App token **in the same shell call** as the commit, push or `gh pr create`: `eval "$(node scripts/gh-app-token.mjs --env)"`. Shell state does not survive between tool calls.
- Push over HTTPS (`git push https://github.com/<owner>/<repo>.git HEAD:<branch>`); SSH remotes ignore the token. From a worktree, `gh pr create --head <branch>`. Use `--force`, not `--force-with-lease`, when force-pushing to a URL.
- After opening a PR, verify `gh pr view <n> --json author -q .author.login` prints `app/<bot-slug>`. A human author means the step failed: close and re-open.
- If the app is not installed on the repository (`node scripts/gh-app-token.mjs --check` lists the repos it can reach), stop and say so instead of pushing as the human. `gh api user` returning 403 under the token is expected.
