# SDLC guard hook

`guard.py` is a PreToolUse hook. VS Code (Local agent) discovers it through
`.github/hooks/hooks.json`. It is a demonstration guard, not complete
shell-security coverage.

## What it enforces

| Rule | Blocks |
|------|--------|
| R01 | recursive deletion of `/`, `~`, `$HOME`, `.`, `..`, the repo root, `.git`, a bare `*` (`rm -rf node_modules` is allowed) |
| R02 | `mkfs`, `dd of=/dev/...`, `chmod -R 777`, writes to `/dev/sd*` |
| R03 | `git reset --hard`, `git clean -f`, `git checkout -- .`, `git restore .`, `git branch -D main`, `filter-branch`, `rebase` on main/master |
| R04 | force push, `+refspec`, any push to main/master (`--force-with-lease` to a feature branch is allowed) |
| R05 | `--no-verify`, `core.hooksPath`, hook config changes, `curl \| sh`, `base64 -d \| sh`, `eval \| sh` |
| R06 | `orchestrator.py approve`, `reject`, `reopen` (humans only) |
| R07 | writes to the `protected` paths in `sdlc/phases.json` (reading is allowed) |
| R08 | writes to files owned by any phase that is not the ACTIVE one; if no phase is ACTIVE, all owned files |

If the payload is malformed, or `sdlc/phases.json` / `sdlc/state.json` cannot
be read, the guard fails closed for tools that could modify things.

## Test it by hand

From the repo root (a denial exits with code 2 and prints the reason):

```powershell
'{"tool_name":"run_in_terminal","tool_input":{"command":"git reset --hard"}}' | python hooks/guard.py; $LASTEXITCODE
'{"tool_name":"run_in_terminal","tool_input":{"command":"git status"}}' | python hooks/guard.py; $LASTEXITCODE
```

Run the automated tests: `python -m unittest discover -s tests -v`.

## Disable it temporarily (human only)

Agents must never do this. In your own session, either:

- turn off the `chat.useHooks` setting in VS Code, or
- rename `.github/hooks/hooks.json` to `hooks.json.off`.

Re-enable it afterwards. Disabling the hook removes the enforcement of R01-R08.
