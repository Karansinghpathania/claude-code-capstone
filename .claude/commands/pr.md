---
name: pr
description: "Kick off phase 8 (pr). Stage A: write PR artifacts. Stage B (after human says \"go\"): branch, commit, push and create pull request."
---

# /pr Command

## Phase 8: pr (Stage A)

STEP 1. Run `python orchestrator.py status`. If `pr` is not
ACTIVE, STOP, tell the human which phase is active, and do nothing else.

## Stage A Procedure (pr is ACTIVE)

Follow `.claude/skills/pr/SKILL.md` for templates and exact steps.

1. Confirm `artifacts/verify.md` has `Result: PASS`; if FAIL, STOP.
2. Write `artifacts/pr.md` with all seven headings.
3. Write `CHANGELOG.md` in Keep a Changelog format.
4. Check validation list; run `python orchestrator.py submit pr`.
5. STOP and print exactly:

Awaiting human approval. Run: python orchestrator.py approve pr --by <your-name>

Never run approve or start Stage B on your own.

## Stage B Procedure (all APPROVED, human said "go")

Run commands one at a time; stop at first error.

1. `git rev-parse --show-toplevel` and `git remote -v` (verify repo and origin).
2. `git switch -c sdlc/<slug>` (feature branch, lowercase, hyphens, <= 40 chars).
3. `git add -- artifacts todo tests/test_todo.py CHANGELOG.md sdlc/state.json sdlc/audit.log.jsonl`.
4. `git commit -m "feat: <summary>"` (conventional commit, no --no-verify).
5. `git push -u origin <branch>`.
6. `gh pr create --title "<title>" --body-file artifacts/pr.md`; print URL.

No --force, --no-verify, or push to main/master.
