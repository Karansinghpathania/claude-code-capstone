# Verification

All checks below were run fresh in this session (phase verify ACTIVE). CLI checks ran with `PYTHONPATH` set to the repo and the working directory set to an empty temporary directory in the scratchpad, so no `tasks.json` was written to the repo root. Each transcript line `$ todo <args>` means `python -m todo.cli <args>`; `[exit=N]` is the real exit code.

## Environment
```
Python 3.13.0
```

## Whole-suite checks
```
$ python -m unittest discover -s tests -v   (full output saved to scratchpad; tail shown)
exit=0
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
In the verbose run, 165 lines end in `ok`; the remaining two are test-docstring lines whose `ok` is on the following line (for example the test_unknown_phase_is_usage_error line, which printed an expected `USAGE ERROR` message before its `ok`). The run reports `Ran 167 tests ... OK` and exit 0, with no FAIL or ERROR result lines.

## Checks

### CLI transcript in an empty temporary directory (used by FR-001..FR-014, NFR-003..NFR-006)
```
$ todo list
No tasks.
[exit=0]
$ todo add   buy milk  
Added: 1 [open] buy milk
[exit=0]
$ todo add buy milk
Added: 2 [open] buy milk
[exit=0]
$ todo add héllo 世界 😀
Added: 3 [open] héllo 世界 😀
[exit=0]
$ todo list
1 [open] buy milk
2 [open] buy milk
3 [open] héllo 世界 😀
[exit=0]
$ todo add    
Error: title must not be empty.
[exit=1]
$ todo add 
Error: title must not be empty.
[exit=1]
$ todo add a	b
Error: title must not contain control characters.
[exit=1]
$ todo add a
b
Error: title must not contain control characters.
[exit=1]
$ todo complete 1
[exit=0]
$ todo complete 1
Task 1 is already done.
[exit=0]
$ todo reopen 1
[exit=0]
$ todo reopen 1
Task 1 is already open.
[exit=0]
$ todo delete 3
[exit=0]
$ todo add after delete
Added: 4 [open] after delete
[exit=0]
$ todo list
1 [open] buy milk
2 [open] buy milk
4 [open] after delete
[exit=0]
$ todo complete 99
Error: task not found: 99.
[exit=1]
$ todo reopen 99
Error: task not found: 99.
[exit=1]
$ todo delete 99
Error: task not found: 99.
[exit=1]
$ todo complete abc
Error: task not found: abc.
[exit=1]
$ todo reopen abc
Error: task not found: abc.
[exit=1]
$ todo delete abc
Error: task not found: abc.
[exit=1]
$ todo complete 0
Error: task not found: 0.
[exit=1]
$ todo reopen 0
Error: task not found: 0.
[exit=1]
$ todo delete 0
Error: task not found: 0.
[exit=1]
$ todo complete -1
Error: task not found: -1.
[exit=1]
$ todo reopen -1
Error: task not found: -1.
[exit=1]
$ todo delete -1
Error: task not found: -1.
[exit=1]
$ todo complete
Usage: python -m todo.cli <command> [argument]

Commands:
  add <title>      Add a task. Quote multi-word titles.
  list             List all tasks.
  complete <id>    Mark a task done.
  reopen <id>      Mark a task open again.
  delete <id>      Remove a task.

Example: python -m todo.cli add "buy milk"
Tasks are stored in tasks.json in the current folder.
[exit=2]
$ todo 
[same usage text as above]
[exit=2]
$ todo bogus
[same usage text as above]
[exit=2]
$ todo add
[same usage text as above]
[exit=2]
$ todo -h
[same usage text as above]
[exit=0]
--- file
{
  "next_id": 5,
  "tasks": [
    {
      "id": 1,
      "title": "buy milk",
      "status": "open"
    },
    {
      "id": 2,
      "title": "buy milk",
      "status": "open"
    },
    {
      "id": 4,
      "title": "after delete",
      "status": "open"
    }
  ]
}
--- corrupt
$ todo list
Error: cannot read tasks.json: not valid JSON (Expecting property name enclosed in double quotes: line 1 column 2 (char 1)). The file was not changed.
[exit=1]
$ todo add x
Error: cannot read tasks.json: not valid JSON (Expecting property name enclosed in double quotes: line 1 column 2 (char 1)). The file was not changed.
[exit=1]
unchanged
$ todo list
Error: cannot read tasks.json: not valid JSON (Unexpected UTF-8 BOM (decode using utf-8-sig): line 1 column 1 (char 0)). The file was not changed.
[exit=1]
unchanged BOM
--- empty
$ todo list
No tasks.
[exit=0]
--- bool
$ todo list
Error: cannot read tasks.json: invalid next_id. The file was not changed.
[exit=1]
$ todo list
Error: cannot read tasks.json: invalid task title. The file was not changed.
[exit=1]
--- restart id
$ todo add a
Added: 1 [open] a
[exit=0]
$ todo add b
Added: 2 [open] b
[exit=0]
$ todo add c
Added: 3 [open] c
[exit=0]
$ todo delete 3
[exit=0]
$ todo add d
Added: 4 [open] d
[exit=0]
$ todo list
1 [open] a
2 [open] b
4 [open] d
[exit=0]
```
(The `unchanged` lines come from `cmp tasks.json before.bin` after each corrupt-file command. Each separate `python -m todo.cli` call is a separate process, so the later calls show persistence across runs.)

### NFR / A-item manual and test checks
```
$ grep -nE "^\s*(import|from) " todo/*.py
todo/app.py:6:import contextlib
todo/app.py:7:import json
todo/app.py:8:import os
todo/app.py:9:import tempfile
todo/app.py:10:import unicodedata
todo/app.py:11:from dataclasses import dataclass
todo/app.py:12:from pathlib import Path
todo/cli.py:3:import sys
todo/cli.py:4:from typing import TextIO
todo/cli.py:6:from todo import app
--- bare except grep
grep exit=1
--- network grep
grep exit=1
--- tests
test_functions_have_type_hints (tests.test_todo.TestNFRQuality.test_functions_have_type_hints)
NFR-008. ... ok
test_no_bare_except (tests.test_todo.TestNFRQuality.test_no_bare_except)
NFR-008. ... ok
test_no_network_modules_imported (tests.test_todo.TestNFRQuality.test_no_network_modules_imported)
NFR-007. ... ok
test_only_stdlib_imports (tests.test_todo.TestNFRQuality.test_only_stdlib_imports)
NFR-002. ... ok
test_python_version_at_least_3_11 (tests.test_todo.TestNFRQuality.test_python_version_at_least_3_11)
NFR-001. ... ok
test_failed_replace_leaves_no_temp_file (tests.test_todo.TestA1SaveEncoding.test_failed_replace_leaves_no_temp_file)
NFR-005: a failed replace removes the temp file. ... ok
test_save_lone_surrogate_raises_storage_error (tests.test_todo.TestA1SaveEncoding.test_save_lone_surrogate_raises_storage_error) ... ok
test_bool_next_id_corrupt (tests.test_todo.TestA3StrictLoad.test_bool_next_id_corrupt) ... ok
test_bool_task_id_corrupt (tests.test_todo.TestA3StrictLoad.test_bool_task_id_corrupt) ... ok
test_empty_stored_title_corrupt (tests.test_todo.TestA3StrictLoad.test_empty_stored_title_corrupt) ... ok
test_non_string_title_corrupt (tests.test_todo.TestA3StrictLoad.test_non_string_title_corrupt) ... ok
test_whitespace_stored_title_corrupt (tests.test_todo.TestA3StrictLoad.test_whitespace_stored_title_corrupt) ... ok
test_main_does_not_alter_stream_encoding (tests.test_todo.TestA4NoGlobalSideEffects.test_main_does_not_alter_stream_encoding) ... ok
test_main_works_with_plain_stringio_streams (tests.test_todo.TestA4NoGlobalSideEffects.test_main_works_with_plain_stringio_streams) ... ok
test_python_dash_m_runs_in_empty_dir (tests.test_todo.TestA4NoGlobalSideEffects.test_python_dash_m_runs_in_empty_dir)
FR-005, NFR-006: manual check from the plan, automated. ... ok
test_help_flags (tests.test_todo.TestA5Help.test_help_flags) ... ok
test_bom_file_is_corrupt_file_untouched (tests.test_todo.TestA6Bom.test_bom_file_is_corrupt_file_untouched) ... ok
test_edge_whitespace_trimmed_first (tests.test_todo.TestR1ControlChars.test_edge_whitespace_trimmed_first) ... ok
test_interior_control_chars_rejected (tests.test_todo.TestR1ControlChars.test_interior_control_chars_rejected) ... ok
test_non_cc_unicode_accepted (tests.test_todo.TestR1ControlChars.test_non_cc_unicode_accepted) ... ok

----------------------------------------------------------------------
Ran 20 tests in 0.316s

OK
```

### Per-id check definitions, expectations and verdicts
Expectations were defined before running; the evidence is in the blocks above.

### FR-001
- Check: CLI `add "buy milk"` twice and a Unicode add. Expected: `Added: <id> [open] <title>`, unique ids, duplicates allowed, exit 0.
- Evidence: CLI transcript (ids 1, 2, 3 with duplicate titles `buy milk`, exit 0 each).
- Result: PASS

### FR-002
- Check: CLI `add "  buy milk  "`, `add ""`, `add "   "`, control-char titles (R-1), Unicode title. Expected: stored title trimmed to `buy milk`; empty or whitespace-only gives stderr error and exit 1; Unicode unchanged.
- Evidence: CLI transcript (`Added: 1 [open] buy milk`; `Error: title must not be empty.` exit 1; Unicode `héllo 世界 😀` unchanged). Tests `TestR1ControlChars` pass. Long title: `tests.test_todo.TestFR002Title.test_long_title_accepted` is in the full suite (OK).
- Result: PASS

### FR-003
- Check: CLI add a, b, c, delete 3, add d. Expected: ids 1, 2, 3, then 4 (not reused), also across separate processes.
- Evidence: "restart id" section (`Added: 4 [open] d`); `next_id` 5 in the JSON file after the earlier sequence.
- Result: PASS

### FR-004
- Check: CLI `list` with several tasks. Expected: creation order, `<id> [open|done] <title>`, exit 0.
- Evidence: list output `1 [open] buy milk` / `2 ...` / `3 ...` / `4 ...`, exit 0.
- Result: PASS

### FR-005
- Check: CLI `list` in an empty directory. Expected: `No tasks.`, exit 0.
- Evidence: first transcript command.
- Result: PASS

### FR-006
- Check: CLI `complete 1` on an open task. Expected: no output, exit 0.
- Evidence: `$ todo complete 1` printed nothing, `[exit=0]`.
- Result: PASS

### FR-007
- Check: CLI `complete 1` again. Expected: "already done" message, exit 0, no change.
- Evidence: `Task 1 is already done.` `[exit=0]`; the test `test_already_done_and_open_return_false_bytes_unchanged` is in the suite (OK).
- Result: PASS

### FR-008
- Check: CLI `reopen 1` on a done task. Expected: no output, exit 0.
- Evidence: `$ todo reopen 1` printed nothing, `[exit=0]`.
- Result: PASS

### FR-009
- Check: CLI `reopen 1` again. Expected: "already open" message, exit 0.
- Evidence: `Task 1 is already open.` `[exit=0]`.
- Result: PASS

### FR-010
- Check: CLI `delete 3` then `list`. Expected: no output, exit 0, task absent.
- Evidence: `delete 3` printed nothing, exit 0; later list has no id 3.
- Result: PASS

### FR-011
- Check: CLI complete/reopen/delete with `99`, `abc`, `0`, `-1`. Expected: `task not found` on stderr, exit 1, nothing changed.
- Evidence: all 12 invocations printed `Error: task not found: <id>.` and exit 1; the later list was unchanged.
- Result: PASS

### FR-012
- Check: sequential separate-process CLI runs; inspect `tasks.json`; empty file. Expected: state persists in `tasks.json` (UTF-8 JSON with `next_id`); empty file gives an empty list.
- Evidence: `--- file` block shows `next_id` and tasks; `--- empty` gave `No tasks.`; no `tasks.json` in the repo root (`ls: cannot access 'tasks.json'`).
- Result: PASS

### FR-013
- Check: corrupt JSON file, BOM file. Expected: stderr error, exit 1, file byte-identical (`cmp`).
- Evidence: `--- corrupt` block (exit 1 for `list` and `add x`, `unchanged`, `unchanged BOM`).
- Result: PASS

### FR-014
- Check: CLI with no command, `bogus`, `add` with no title, `complete` with no id. Expected: usage on stderr, exit 2, no data change.
- Evidence: each printed usage and `[exit=2]`.
- Result: PASS

### NFR-001
- Check: `python --version` and `TestNFRQuality.test_python_version_at_least_3_11`. Expected: 3.11 or later.
- Evidence: `Python 3.13.0`; test ok.
- Result: PASS

### NFR-002
- Check: import listing and `test_only_stdlib_imports`. Expected: only standard library modules; tests use `unittest`.
- Evidence: imports are contextlib, json, os, tempfile, unicodedata, dataclasses, pathlib, sys, typing; test ok; `tests/test_todo.py` imports only stdlib modules including `unittest`.
- Result: PASS

### NFR-003
- Check: CLI exit codes. Expected: 0 on success and already done/open, 1 on errors with stderr message, 2 on usage.
- Evidence: CLI transcript exit codes 0 / 1 / 2 as expected. Also `-h` exits 0 (A-5).
- Result: PASS

### NFR-004
- Check: error messages in transcript; `test_errors_are_plain_language_on_stderr_only` and `test_surrogate_title_exit_1_no_traceback` in the suite. Expected: plain language, no stack trace, on stderr.
- Evidence: all error lines are one-line `Error: ...` messages; no traceback appears; full suite OK.
- Result: PASS

### NFR-005
- Check: corrupt/BOM files compared with `cmp` after failing commands; test `test_failed_replace_leaves_no_temp_file`. Expected: file unchanged.
- Evidence: `unchanged`, `unchanged BOM`; test ok.
- Result: PASS

### NFR-006
- Check: CLI Unicode title round trip and `TestNFR006Unicode` (in the suite). Expected: unchanged UTF-8 preserved.
- Evidence: `héllo 世界 😀` in add and list output; the full suite is OK.
- Result: PASS

### NFR-007
- Check: grep for network modules in `todo/*.py` and `test_no_network_modules_imported`. Expected: no matches.
- Evidence: `grep exit=1` (no matches); test ok.
- Result: PASS

### NFR-008
- Check: grep for bare `except:` and `test_no_bare_except`, `test_functions_have_type_hints`. Expected: none found; hints present.
- Evidence: `grep exit=1` (no matches); both tests ok.
- Result: PASS

### NFR-009
- Check: `python -m unittest discover -s tests -v` and `python -m compileall -q .`. Expected: all tests OK, compile exit 0.
- Evidence: `Ran 167 tests ... OK`, exit 0; `compile exit=0`; `orchestrator.py check` printed `all checks passed`.
- Result: PASS

### R-1 (folded into FR-002)
- Check: CLI `add` with tab and newline in the title; `TestR1ControlChars`. Expected: rejected like an empty title, exit 1, no task created.
- Evidence: both gave `Error: title must not contain control characters.` `[exit=1]`; three tests ok.
- Result: PASS

### A-1
- Check: `test_save_lone_surrogate_raises_storage_error`, `test_surrogate_title_exit_1_no_traceback`, `test_unencodable_stdout_exit_1_plain_stderr`. Expected: encode errors become StorageError or a plain exit 1.
- Evidence: `TestA1SaveEncoding` tests ok; the CLI-level tests are in the full suite (OK, exit 0).
- Result: PASS

### A-2
- Check: control characters rejected before any save (R-1 CLI run and `test_control_char_rejection_keeps_existing_file`). Expected: rejected, file untouched.
- Evidence: R-1 transcript; full suite OK.
- Result: PASS

### A-3
- Check: `tasks.json` with `next_id: true`, and with an empty stored title. Expected: corrupt error exit 1, file untouched; `TestA3StrictLoad`.
- Evidence: `--- bool` block (`invalid next_id`, `invalid task title`, exit 1); five tests ok.
- Result: PASS

### A-4
- Check: `TestA4NoGlobalSideEffects`. Expected: main does not alter stream encoding.
- Evidence: three tests ok in the listing above.
- Result: PASS

### A-5
- Check: `todo -h`; `TestA5Help.test_help_flags`. Expected: usage printed, exit 0.
- Evidence: `[exit=0]` with usage text; test ok.
- Result: PASS

### A-6
- Check: BOM `tasks.json`; `TestA6Bom`. Expected: corrupt error, exit 1, file untouched.
- Evidence: `Unexpected UTF-8 BOM ...` `[exit=1]`, `unchanged BOM`; test ok.
- Result: PASS

## Results table
| id | check | PASS/FAIL |
|----|-------|-----------|
| FR-001 | CLI add, unique ids, duplicates | PASS |
| FR-002 | CLI trim, empty, whitespace, Unicode; TestR1ControlChars | PASS |
| FR-003 | CLI add/delete/add id never reused | PASS |
| FR-004 | CLI list order and format | PASS |
| FR-005 | CLI list on empty dir prints `No tasks.` | PASS |
| FR-006 | CLI complete open task | PASS |
| FR-007 | CLI complete done task | PASS |
| FR-008 | CLI reopen done task | PASS |
| FR-009 | CLI reopen open task | PASS |
| FR-010 | CLI delete | PASS |
| FR-011 | CLI 99/abc/0/-1 on complete/reopen/delete | PASS |
| FR-012 | persistence across processes, tasks.json | PASS |
| FR-013 | corrupt/BOM file untouched, exit 1 | PASS |
| FR-014 | usage errors exit 2 | PASS |
| NFR-001 | python --version; version test | PASS |
| NFR-002 | import listing; test_only_stdlib_imports | PASS |
| NFR-003 | exit codes 0/1/2 | PASS |
| NFR-004 | plain stderr messages, no traceback | PASS |
| NFR-005 | files unchanged after failure (cmp) | PASS |
| NFR-006 | Unicode round trip | PASS |
| NFR-007 | grep network, test_no_network_modules_imported | PASS |
| NFR-008 | grep bare except, hint test | PASS |
| NFR-009 | unittest discover + compileall | PASS |
| R-1 | control-char CLI + TestR1ControlChars | PASS |
| A-1 | TestA1SaveEncoding + CLI encode tests | PASS |
| A-2 | control chars rejected before save | PASS |
| A-3 | strict load (bool, empty title) | PASS |
| A-4 | TestA4NoGlobalSideEffects | PASS |
| A-5 | `-h` exits 0 | PASS |
| A-6 | BOM treated as corrupt | PASS |

## Failures and notes
No failures. `git status --short` after the CLI runs showed no new stray files in the repo (only the pre-existing modified and untracked entries; no `tasks.json` in the repo root; the home-directory permission warnings are unrelated to the repo). Some A-1 and FR-002 (long title) evidence relies on the named tests passing inside the full-suite run (167 tests OK) rather than a separate pasted line. No code or other file was changed.

Result: PASS
