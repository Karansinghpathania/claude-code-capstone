---
name: pr
description: Templates and exact steps for the pr phase - artifacts/pr.md, a Keep-a-Changelog CHANGELOG.md, and the safe git/gh sequence for Stage B. Use when the pr agent prepares or raises the pull request.
user-invocable: false
---

# Skill: pr (HOW)

The **pr agent** decides the stage and what it may write. This skill holds
the templates and the exact command sequence.

## Procedure, Stage A (pr ACTIVE: documents only)
1. Confirm `artifacts/verify.md` ends with `Result: PASS`; if FAIL, STOP.
2. Fill `artifacts/pr.md` from the template below. Copy test evidence from
   `artifacts/verify.md` (or re-run and paste the real output).
3. Write `CHANGELOG.md` in the format below.
4. Check the validation list, submit, STOP for human approval.

## Procedure, Stage B (pr APPROVED and the human said "go")
Run one command at a time; stop at the first error.
1. `git rev-parse --show-toplevel` (must be this project) and
   `git remote -v` (must show `origin`); `git branch --show-current`.
2. `git switch -c sdlc/<slug>`: slug from the story title, lowercase,
   hyphens, at most 40 characters.
3. `git add -- artifacts todo tests/test_todo.py CHANGELOG.md sdlc/state.json
   sdlc/audit.log.jsonl`, then `git diff --cached --name-only` and confirm
   only those paths appear. Unstage extras with `git restore --staged
   <path>`.
4. `git commit -m "feat: <summary>"` (conventional commit; no
   `--no-verify`).
5. `git push -u origin sdlc/<slug>`.
6. `gh pr create --title "<title>" --body-file artifacts/pr.md`; print the
   PR URL.

## Safety rules
- Feature branch only; never push to main or master.
- No `--force`, `-f`, `+refspec`; no `--no-verify`; no history rewrite.
- Stage only pipeline outputs; never `git add -A` or `git add .`.
- No secrets, `.env` files or tokens in the diff.
- No git write command until the human says "go".

## On failure
STOP. Report the exact command and its error output. Do not retry with
other flags, do not work around hooks, do not delete branches. The human
decides (for example, adding a remote or authenticating `gh`).

## Template: artifacts/pr.md
```
# Pull Request
## Summary
## What changed          (file list with one line each)
## Traceability          (FR-001 -> evidence in verify.md, ... every id)
## Test evidence         (real output)
## Risks
## Rollback              (git revert <commit>; no history rewrite)
## Reviewer checklist
- [ ] Every requirement id has evidence
- [ ] Tests pass locally
- [ ] No unrelated files in the diff
```

## Template: CHANGELOG.md (Keep a Changelog)
```
# Changelog
All notable changes to this project are documented in this file.
The format is based on Keep a Changelog (https://keepachangelog.com).

## [Unreleased]
### Added
- <what was added, one line per user-visible capability>
### Changed
### Fixed
```

## Validation checklist
- [ ] `Result: PASS` seen in `artifacts/verify.md`.
- [ ] Every FR/NFR id appears in pr.md Traceability with its evidence.
- [ ] Test evidence is real output; CHANGELOG describes this change.
- [ ] Stage B: only after "go"; branch is not main or master; staged diff
      contains only pipeline outputs.

## Stop condition
Stage A ends after submit, at the human approval gate. Stage B ends after
the PR URL is printed, or at the first failing command. This skill never
approves, forces, or starts any other phase.
