# Pull Request

## Summary
Adds a command-line todo list (`python -m todo.cli add|list|complete|reopen|delete`) backed by `tasks.json` in the current folder. Python standard library only, tests with `unittest`. Covers FR-001..FR-014 and NFR-001..NFR-009. It also implements the design-review decisions R-1 (folded into FR-002: control characters in a title are rejected) and A-1..A-6 (see Traceability and Risks). `artifacts/verify.md` ends with `Result: PASS`, and `artifacts/review.md` has Verdict APPROVE with no Blocker or Major finding.

Known deviation: `artifacts/requirements.md` and `artifacts/architecture.md` do NOT reflect R-1 and A-1..A-6. The code follows `artifacts/design-review.md`. The human chose to proceed with this recorded deviation (review finding R-01).

## What changed
- `todo/__init__.py`: package marker.
- `todo/app.py`: domain layer (errors, `Task`, title and id validation, `TaskStore` strict load and atomic save, add/list/complete/reopen/delete).
- `todo/cli.py`: hand-written argument parser, output formats, `Error:` mapping, exit codes 0/1/2, `-h`/`--help`.
- `tests/test_todo.py`: unittest suite for every FR/NFR and for R-1 and A-1..A-6.
- `artifacts/*.md`: pipeline artifacts (requirements, architecture, design-review, implementation-plan, review, verify, pr).
- `CHANGELOG.md`: Keep a Changelog entry for this change.
- `sdlc/state.json`, `sdlc/audit.log.jsonl`: pipeline state and audit log (staged by Stage B only).

## Traceability
Evidence is in `artifacts/verify.md` (per-id sections and results table); the code and test locations are in `artifacts/review.md`.

| Id | Requirement | Evidence in verify.md | Result |
|----|-------------|-----------------------|--------|
| FR-001 | add task, unique ids, duplicates allowed | CLI transcript: ids 1, 2, 3, duplicate `buy milk`, exit 0 | PASS |
| FR-002 | title trimmed; empty/whitespace rejected; Unicode kept (extended by R-1) | `Added: 1 [open] buy milk`; `Error: title must not be empty.` exit 1; `TestR1ControlChars` | PASS |
| FR-003 | ids never reused | "restart id" section: add d gives id 4 after deleting 3; `next_id` 5 in file | PASS |
| FR-004 | list in creation order, `<id> [open\|done] <title>` | list output, exit 0 | PASS |
| FR-005 | empty list prints `No tasks.` | first transcript command | PASS |
| FR-006 | complete an open task silently | `complete 1` no output, exit 0 | PASS |
| FR-007 | complete a done task: message, exit 0 | `Task 1 is already done.` exit 0 | PASS |
| FR-008 | reopen a done task silently | `reopen 1` no output, exit 0 | PASS |
| FR-009 | reopen an open task: message, exit 0 | `Task 1 is already open.` exit 0 | PASS |
| FR-010 | delete a task silently | `delete 3` no output, exit 0, absent from list | PASS |
| FR-011 | unknown or invalid id: not found, exit 1 | 12 invocations with 99/abc/0/-1, all exit 1 | PASS |
| FR-012 | persistence in `tasks.json` (UTF-8 JSON with `next_id`) | `--- file` block; `--- empty` block; no `tasks.json` in repo root | PASS |
| FR-013 | corrupt file: error, exit 1, file untouched | `--- corrupt` block, `cmp` unchanged, BOM unchanged | PASS |
| FR-014 | usage errors: usage on stderr, exit 2 | no command, `bogus`, `add`, `complete` all exit 2 | PASS |
| NFR-001 | Python 3.11+ | `Python 3.13.0`; version test ok | PASS |
| NFR-002 | standard library only, unittest | import listing; `test_only_stdlib_imports` | PASS |
| NFR-003 | exit codes 0/1/2 | CLI transcript exit codes; `-h` exits 0 | PASS |
| NFR-004 | plain-language errors on stderr, no traceback | one-line `Error: ...` messages; error tests in suite | PASS |
| NFR-005 | data never lost on failure | `cmp` unchanged; `test_failed_replace_leaves_no_temp_file` | PASS |
| NFR-006 | Unicode preserved | `héllo 世界 😀` round trip; `TestNFR006Unicode` | PASS |
| NFR-007 | no network calls | grep exit 1; `test_no_network_modules_imported` | PASS |
| NFR-008 | PEP 8 hints, no bare except | grep exit 1; `test_no_bare_except`, `test_functions_have_type_hints` | PASS |
| NFR-009 | tests and compile pass | `Ran 167 tests ... OK`; compileall exit 0; `all checks passed` | PASS |
| R-1 | control characters in titles rejected (folded into FR-002) | tab and newline give `Error: title must not contain control characters.` exit 1; `TestR1ControlChars` | PASS |
| A-1 | encode errors become `StorageError` / plain exit 1 | `TestA1SaveEncoding`, CLI encode tests in suite | PASS |
| A-2 | control chars rejected before any save | R-1 run; `test_control_char_rejection_keeps_existing_file` | PASS |
| A-3 | strict load: bool ids and empty stored title are corrupt | `--- bool` block; `TestA3StrictLoad` | PASS |
| A-4 | no global side effects in `main` (reconfigure under `__main__`) | `TestA4NoGlobalSideEffects` | PASS |
| A-5 | `-h` prints usage, exit 0 | `[exit=0]` with usage; `TestA5Help` | PASS |
| A-6 | UTF-8 BOM is corrupt | `Unexpected UTF-8 BOM ...` exit 1, `unchanged BOM`; `TestA6Bom` | PASS |

## Test evidence
Real output copied from `artifacts/verify.md`, and the suite re-run during this phase (`python -m unittest discover -s tests`, tail: `Ran 167 tests in 3.789s` / `OK`).

```
$ python -m unittest discover -s tests -v
...
test_temp_dir_is_used (test_todo.TestScaffold.test_temp_dir_is_used) ... ok

----------------------------------------------------------------------
Ran 167 tests in 3.536s

OK
$ python -m compileall -q .
compile exit=0
$ python orchestrator.py check
all checks passed
check exit=0
```

Sample CLI output (empty temporary directory):
```
$ todo add   buy milk  
Added: 1 [open] buy milk
[exit=0]
$ todo complete 1
Task 1 is already done.
[exit=0]
$ todo complete 99
Error: task not found: 99.
[exit=1]
$ todo add a	b
Error: title must not contain control characters.
[exit=1]
```

## Risks
Known deviation and accepted risks, stated as recorded in the approved artifacts:
- Deviation (review R-01): `requirements.md` FR-002 has no control-character rule (R-1), and `architecture.md` lacks A-1..A-6 and still carries the superseded D8. The code follows `design-review.md`. Human to reopen those artifacts or keep this as an accepted deviation.
- Stale docs (review R-02): `hooks/README.md` still describes the old VS Code / `.github/hooks/hooks.json` hook and the `chat.useHooks` setting; the repo now uses `.claude/settings.json`. It is not part of the todo change and was not updated.
- Minor review findings left open (no code change): R-03 `add` saves before printing, so a print failure gives exit 1 with the task already saved; R-04 load does not reject control characters in a hand-edited stored title; R-05 not-found message echoes the raw id (accepted risk F-05); R-06 the fallback stderr write in `_write_error` is not guarded against `OSError`; R-07 only Unicode category `Cc` is rejected (U+2028/U+2029 accepted); R-08, R-09, R-10 are nits (double normalisation, test names differ from the plan, missing docstrings).
- Other accepted risks from design-review: F-06 (temp-file mode and Windows `os.replace` behaviour), F-09 (raw-id strings in the `app` API), NFR-001 verification note.
- Some A-1 and long-title (FR-002) evidence relies on named tests passing in the full-suite run rather than a separate pasted line (verify.md notes).

## Rollback
`git revert <commit>` of the merge or feature commit. No history rewrite. The change adds new files (`todo/`, `tests/test_todo.py`, artifacts, `CHANGELOG.md`) and does not alter existing application data; a `tasks.json` created by users can simply be deleted.

## Reviewer checklist
- [ ] Every requirement id (FR-001..FR-014, NFR-001..NFR-009) has evidence
- [ ] R-1 and A-1..A-6 are understood as implemented but absent from requirements.md and architecture.md
- [ ] Tests pass locally (`python -m unittest discover -s tests -v`, `python -m compileall -q .`)
- [ ] No unrelated files in the diff (no `tasks.json`, no secrets)
- [ ] Stale `hooks/README.md` follow-up is acknowledged
