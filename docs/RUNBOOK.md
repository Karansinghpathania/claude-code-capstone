# Reviewer demo runbook

A step-by-step script for running the whole pipeline live. Each step gives
what to run or type, what you should see, and what to point out to the
audience. Overview and diagrams: [README.md](../README.md). Rules:
[docs/CONTRACT.md](CONTRACT.md).

Conventions: commands starting with `python` run in the repository root.
"Terminal A" is the terminal you keep for yourself; every `approve`, `reject`
and `reopen` is typed there by a human, never in the Claude Code session.
"Chat" steps are typed into Claude Code (terminal CLI, Desktop app or VS Code
extension) started in this folder. Examples use PowerShell; on macOS or Linux
use `python3` and the matching shell syntax.

## Before you start

- Python 3.11+, Claude Code installed (`claude --version`), and Claude Code
  started with this folder as its working directory (`claude` in the
  repository root).
- For step 11 only: this folder is its own git repository (`git rev-parse --show-toplevel`
  prints this folder), `git remote -v` lists `origin`, and `gh auth status`
  succeeds. The `pr` agent refuses to push otherwise.
- The hook wired in `.claude/settings.json` active (see
  [hooks/README.md](../hooks/README.md)); the permission `deny` rules in the
  same file are the first layer and the hook is the second.
- Read `user_story.md` once so you can answer the clarifying questions.

## Step 1. Show a clean repository

Run:

```
python orchestrator.py status
Get-ChildItem artifacts -Force
Test-Path todo
python -m unittest discover -s tests -v
python tools/audit_repo.py
```

Expected: `requirements` ACTIVE, the other seven LOCKED, `approvalStatus:
NOT_SUBMITTED`; `artifacts` contains only `.gitkeep`; `Test-Path todo` prints
`False`; all tests pass; the audit prints PASS for every line and ends with
`0 failed`. The audit is only meaningful before the live run: it reports FAIL
once artifacts exist, by design.

Point out: nothing was pre-generated. The orchestrator, hook and tests already
exist and are tested; the agents will produce everything else live.

## Step 2. Run /requirements

Type in the Claude Code main chat: `/requirements`. This phase runs in the
main conversation, not as a subagent, so you can answer its questions.

Expected: Claude runs `python orchestrator.py status`, reads
`user_story.md` and asks numbered clarifying questions, then waits. Typical
topics: duplicate titles, empty titles, whether tasks persist between runs,
how ids are assigned after a delete, exact messages. Answer every question in
chat. It then writes `artifacts/requirements.md`, runs
`python orchestrator.py submit requirements` and prints:

```
Awaiting human approval. Run: python orchestrator.py approve requirements --by <your-name>
```

Point out: the agent asked instead of guessing, and each answer is recorded
in the artifact. Show the FR-/NFR- ids. Run `python orchestrator.py status` in
Terminal A: `AWAITING_APPROVAL`, `approvalStatus: PENDING_HUMAN_APPROVAL`,
`allowedFiles: []` (the agent can no longer write).

## Step 3. Approve in a separate terminal

Read `artifacts/requirements.md` first. In Terminal A (not the agent's
terminal) run:

```
python orchestrator.py approve requirements --by <your-name>
```

Type `requirements` when asked "Type the phase id to confirm:".

Expected: `'requirements' approved by <your-name>; 'architecture' is ACTIVE`.

Point out: approval needs an interactive terminal and a typed confirmation, so
an agent cannot do it. The submit-time hashes were checked: if the file had
changed after submit, approve would have refused.

## Step 4. Ask the orchestrator what is next

Run:

```
python orchestrator.py next
```

Expected:

```
ACTIVE phase: architecture
Run prompt: /architecture (.claude/commands/architecture.md)
Must produce: artifacts/architecture.md
Then run: python orchestrator.py submit architecture
```

Point out: the state machine tells the human what to do next. Repeat this
after every approval.

## Step 5. Architecture

Chat: `/architecture` (it hands the work to the subagent in
`.claude/agents/architecture.md`). Review `artifacts/architecture.md`, then in
Terminal A:
`python orchestrator.py approve architecture --by <your-name>` and type
`architecture`. Run `python orchestrator.py next`.

Expected: a design that cites FR-/NFR- ids; the agent stops with the
awaiting-approval line.

Point out: it cannot start design-review by itself, and only
`artifacts/architecture.md` was written (the hook blocks any other phase's file).

## Step 6. Design review (and the REVISE path)

Chat: `/design-review`. A different agent reads the design adversarially and
writes `artifacts/design-review.md`. Its last line is `Verdict: APPROVE` or
`Verdict: REVISE`; submit refuses without it.

If the verdict is APPROVE: approve with
`python orchestrator.py approve design-review --by <your-name>` and continue.

If the verdict is REVISE (High findings or uncovered requirements), the human
chooses:
1. Simple, when the review itself is wrong or incomplete:
   `python orchestrator.py reject design-review --reason "<text>"`, then
   confirm by typing `design-review`. The same phase is ACTIVE again and the
   reason is logged.
2. Typical, when the design must change: `reopen` the architecture phase.
   Reopen refuses while later phases still own files on disk, so first move
   the review out of the way (keep it to quote the findings):
   ```
   Move-Item artifacts\design-review.md $env:TEMP\design-review.v1.md
   python orchestrator.py reopen architecture --reason "<why>"
   ```
   Type `architecture`. Architecture is ACTIVE again and the later phases are
   LOCKED. Run `/architecture`, paste the findings into the chat, then submit,
   approve, and run `/design-review` again.

Point out: independent reviewer, explicit verdict, and a controlled loop back.
Nothing moves forward or backward without the human.

## Step 7. Planning

Chat: `/planning`; review `artifacts/implementation-plan.md`; approve
`planning`; run `python orchestrator.py next`.

Point out: tasks (T-01, T-02, ...) map to FR-/NFR- ids, and the plan is what
the implementer is bound to.

## Step 8. Implementation

Chat: `/implementation`. This is the only phase that writes code: `todo/__init__.py`,
`todo/app.py`, `todo/cli.py` and `tests/test_todo.py`. Expected: the agent runs
`python -m compileall -q .` and `python -m unittest discover -s tests -v` and shows
the real output, then reports task id to files to FR/NFR ids and submits.

Before approving, run in Terminal A:

```
python -m compileall -q .
python -m unittest discover -s tests -v
```

Point out: submit only checks that the four owned files exist and are
non-empty, so the human must run the tests and read the code. The agent could not
edit the earlier artifacts or the orchestrator.

## Step 9. Review

Chat: `/review`; review `artifacts/review.md`; approve `review`.

Point out: the reviewer must mention every FR/NFR id (enforced at submit) and
reports findings instead of fixing the code.

## Step 10. Verify

Chat: `/verify`. Expected: for every FR and NFR a command, real pasted output
and PASS or FAIL in `artifacts/verify.md`, ending with `Result: PASS` or
`Result: FAIL`.

If it says FAIL, do not approve: use
`python orchestrator.py reject verify --reason "<text>"` or reopen an earlier
phase as in step 6.

Point out: evidence, not claims. The artifact needs a fenced code block and
every id, or submit refuses.

## Step 11. Pull request (Stage A, approve, then "go")

Chat: `/pr`. Stage A writes `artifacts/pr.md` and `CHANGELOG.md` and submits.
Review them, then in Terminal A:

```
python orchestrator.py approve pr --by <your-name>
python orchestrator.py status
```

Type `pr`. Expected: `Pipeline complete`, `approvalStatus: COMPLETE`,
`currentPhase: None`.

Stage B: run `/pr` again (or continue the chat). The agent asks for an explicit
"go". Type `go`. It checks the git setup, creates a branch `sdlc/<slug>`, stages
only the pipeline outputs, makes a conventional commit, pushes the branch and runs
`gh pr create --body-file artifacts/pr.md`. Open the printed pull request URL.

Point out: the PR body is `artifacts/pr.md` with a requirement-to-evidence
traceability table. No force push, no push to main, and nothing happens without
"go". If a git or `gh` command fails, the agent stops and reports the error.

## Step 12. Show a blocked transition

Run:

```
python orchestrator.py submit architecture
```

At the end of the demo, expected (exit code 1):

```
RULE VIOLATION: submit needs ACTIVE but 'architecture' is APPROVED. Run `python orchestrator.py next` to see what is allowed
```

The LOCKED form is more striking. Right after step 1, while `requirements` is
ACTIVE, the same command prints `... but 'architecture' is LOCKED ...`.

Point out: every refusal says which rule failed and what to do, and the refusal
is written to `sdlc/audit.log.jsonl`.

## Step 13. Show the guard blocking commands

Run a deterministic demo with the guard directly. A dangerous command
(PowerShell; on bash use `echo '...' | python3 hooks/guard.py; echo $?`):

```
'{"tool_name":"Bash","tool_input":{"command":"git reset --hard"}}' | python hooks/guard.py; $LASTEXITCODE
```

Expected: nothing on stdout, "BLOCKED by SDLC guard [R03]" with Blocked, Rule,
Why and Instead lines on stderr, then `2`. In Claude Code, exit code 2 blocks
the tool call and the stderr text is shown to Claude as the reason.

An agent trying to approve (rule R06):

```
'{"tool_name":"Bash","tool_input":{"command":"python orchestrator.py approve pr --by me"}}' | python hooks/guard.py; $LASTEXITCODE
```

Expected: "BLOCKED by SDLC guard [R06]", then `2`.

A write to a file the phase does not own (rule R08):

```
'{"tool_name":"Write","tool_input":{"file_path":"artifacts/architecture.md","content":"x"}}' | python hooks/guard.py; $LASTEXITCODE
```

Expected: "BLOCKED by SDLC guard [R08]", then `2`.

A harmless command is allowed (no output, `0`):

```
'{"tool_name":"Bash","tool_input":{"command":"git status"}}' | python hooks/guard.py; $LASTEXITCODE
```

Optional live variant: ask Claude in chat to run `python orchestrator.py approve pr --by me`.
The permission `deny` rule in `.claude/settings.json` refuses it first (layer
one); if that rule were missing, the hook denies it (layer two); and without
either, the orchestrator still refuses because there is no interactive
terminal. A model may also decline on its own, which is why the payload demo
above is the reliable one.

Point out: the hook is deterministic and runs before the tool call, so it works
even if the model is persuaded. Its matcher covers `Bash`, `PowerShell`,
`Edit`, `Write`, `MultiEdit` and `NotebookEdit`. It is also demo-grade (see
README limitations).

## Step 14. Show tamper detection

Run in Terminal A, as the human. This edits an approved artifact, so copy it
first:

```
Copy-Item artifacts\requirements.md $env:TEMP\requirements.md.bak
Add-Content artifacts\requirements.md "tampered"
python orchestrator.py check
```

Expected (exit code 1):

```
RULE VIOLATION: check failed:
  - APPROVED phase 'requirements' file changed since approval: artifacts/requirements.md. Remove future-phase files, restore changed or missing files from git
```

Restore it and check again:

```
Copy-Item $env:TEMP\requirements.md.bak artifacts\requirements.md -Force
python orchestrator.py check
```

Expected: `all checks passed`.

Point out: every approved artifact is pinned by its SHA-256 hash from submit time.
The same hash check stops `approve` if a file is edited between submit and approval.

## Troubleshooting

| Symptom | Likely cause and fix |
|---------|----------------------|
| `/requirements` is not offered | Claude Code was not started in this folder, so `.claude/commands/` was not loaded. Quit, run `claude` in the repository root, and type `/` to list the commands. |
| Agent says the phase is not ACTIVE | Run `python orchestrator.py status`; start the prompt of the ACTIVE phase (`python orchestrator.py next` names it). |
| `submit` refuses with "traceability checks failed" | Read the listed problems: missing FR ids, unchecked `- [ ]` open questions, an undefined id, a missing `Verdict:` line, or a missing code block. The agent must fix the artifact and resubmit. |
| `approve` says "files changed since submit" | A file changed after submit. Run `python orchestrator.py reject <phase> --reason "<text>"`, have the agent fix it, then resubmit. |
| "must be run by a human in an interactive terminal" | You are in a non-interactive shell (an agent terminal, a pipe, a task). Open a normal terminal and retry. |
| "sdlc/state.json is invalid" | The state file is corrupt or out of order. Restore it from git, or, only if you intend to start over, follow "Reset to clean state" below. |
| The hook blocks something legitimate | Read the BLOCKED message: it names the rule and the files the current phase may write. If the guard is wrong, a human does the action in Terminal A. To disable the hook for debugging, see [hooks/README.md](../hooks/README.md). |
| `reopen` refuses: "later phases still have files on disk" | Move or delete the files it lists (see step 6), then retry. |
| Stage B stops with a git error | Check `git rev-parse --show-toplevel` (must be this folder), `git remote -v` (needs `origin`), and `gh auth status`. The agent will not work around errors. |
| `python` not found | Use `python3` (macOS/Linux) or the `py -3` launcher (Windows). |
| An agent changed something it should not have | Run `python orchestrator.py check` and `git status`; restore from git or from a copy. |

## Reset to clean state

Do this yourself, in your own terminal, never through an agent. Every step is
non-destructive to the pipeline's code and history: you delete only the
generated files, one by one, and the audit log is left alone.

1. Optional: archive the audit log by copying it (the original stays):
   ```
   Copy-Item sdlc\audit.log.jsonl $HOME\audit-archive.jsonl
   ```
   The log is append-only and a human should keep or archive it. Do not delete it.
2. If you are on a `sdlc/<slug>` branch, switch back to your default branch
   first so you are not deleting files that belong to the PR branch.
3. Delete the generated artifacts and code manually, in Explorer or by name.
   Keep `artifacts/.gitkeep`:
   ```
   Remove-Item artifacts\requirements.md, artifacts\architecture.md, artifacts\design-review.md, artifacts\implementation-plan.md, artifacts\review.md, artifacts\verify.md, artifacts\pr.md -ErrorAction SilentlyContinue
   Remove-Item todo -Recurse -ErrorAction SilentlyContinue
   Remove-Item tests\test_todo.py, CHANGELOG.md -ErrorAction SilentlyContinue
   ```
4. Delete only `sdlc/state.json`, then re-create it:
   ```
   Remove-Item sdlc\state.json
   python orchestrator.py status
   ```
   `status` re-initialises the state with `requirements` ACTIVE and the others
   LOCKED. Do not touch `sdlc/phases.json` or `sdlc/audit.log.jsonl`.
5. Confirm:
   ```
   python orchestrator.py check
   Get-ChildItem artifacts -Force
   Test-Path todo
   ```
   Expected: `all checks passed`, only `.gitkeep` in `artifacts`, `False`.

## Using your own story

1. Replace the contents of `user_story.md` with your story (a human does
   this, not an agent). Include acceptance criteria; the requirements agent
   will ask about anything ambiguous.
2. Follow "Reset to clean state" above.
3. Run `/requirements` and continue from step 2.

The phases, orchestrator and hook work for any story. The one
example-specific part is the code file list of the implementation phase
(`todo/__init__.py`, `todo/app.py`, `todo/cli.py`, `tests/test_todo.py`). If
your story needs different code files, a human must change:
- the `owns` list of the implementation phase in `sdlc/phases.json`;
- the "Allowed files" section of `.claude/agents/implementation.md`
  (`tests/test_config.py` checks that it matches `sdlc/phases.json`);
- the other agent and command files that mention `todo/` as the code folder
  (search `.claude/agents` and `.claude/commands` for `todo/`). They are
  instructions only, so a stale mention does not break the orchestrator, but it
  will mislead the agent.
