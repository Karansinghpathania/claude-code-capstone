# Implementation Plan

## Sources and decisions
- Inputs: `artifacts/requirements.md`, `artifacts/architecture.md`, `artifacts/design-review.md` (all approved), `docs/CONTRACT.md`.
- Human decision (source: human, chat): plan from the three approved artifacts plus `design-review.md`; include R-1 and A-1..A-6 from `design-review.md` as explicit tasks; fold R-1 into FR-002 (control-character titles rejected like an empty title: stderr error, exit 1, nothing created); no new requirement id.
- Design-review finding dispositions used (source: `design-review.md`, Human Decisions): F-01, F-02, F-03, F-04, F-07 (-h), F-08 (BOM only) accepted; F-05, F-06, F-09 accepted risks (no task).
- Every task also follows CLAUDE.md: PEP 8, type hints on all signatures, no bare `except:`, stdlib only, `unittest` only. After each task run `python -m unittest discover -s tests -v`; before submit run `python -m compileall -q .`.
- Tests are written alongside the code they cover, inside `tests/test_todo.py`, organised in `unittest.TestCase` classes named by FR/NFR id.

## Ordered tasks

### T-01 Package marker and test scaffold
- Goal: create the importable package and an empty-but-runnable test module with temp-directory helpers.
- Files touched: `todo/__init__.py` (marker, optional `__version__` only), `tests/test_todo.py` (imports, temp-dir `setUp`/`tearDown` helper, helper to run `main` with captured stdout/stderr).
- FR/NFR ids: NFR-001, NFR-002, NFR-007, NFR-008, NFR-009.
- Done-when: `python -m unittest discover -s tests -v` runs and exits 0; `python -m compileall -q .` exits 0.

### T-02 Errors, Task model, title trim, id parsing
- Goal: add `Task`, `TodoError`, `ValidationError`, `TaskNotFoundError`, `StorageError`, `normalize_title` (strip whitespace, reject empty) and `parse_task_id` (ASCII digits, value >= 1, else `TaskNotFoundError`), per architecture D5, D9.
- Files touched: `todo/app.py`, `tests/test_todo.py`.
- FR/NFR ids: FR-002, FR-011, NFR-004, NFR-008.
- Done-when: tests pass showing `"  buy milk  "` becomes `buy milk`; empty and whitespace-only raise `ValidationError`; `abc`, `0`, `-1`, `""` and `99`-style ids are handled as `TaskNotFoundError` (99 is checked in T-08); Unicode text is unchanged by `normalize_title`.

### T-03 R-1 / A-2: reject control characters in titles (source: design-review.md R-1, A-2, finding F-02)
- Goal: extend `normalize_title` so that, after trimming, a title containing any control character (Unicode category `Cc`, for example newline, tab, ESC, DEL) raises `ValidationError` with a plain-language message, exactly like an empty title. Validation happens before the store is loaded or saved. Printable and non-Cc Unicode (emoji, accented text, non-ASCII spaces) stays accepted and unchanged. No new requirement id; this is part of FR-002.
- Files touched: `todo/app.py`, `tests/test_todo.py`.
- FR/NFR ids: FR-002, FR-004 (one task per line), NFR-006, NFR-004.
- Done-when: tests pass for an interior newline, tab, ESC sequence and NUL each rejected; via `main`, `add` of such a title prints an error on stderr, returns 1, and creates no `tasks.json` and changes none (the CLI part is re-checked in T-10); a Unicode title such as `café ☕ 日本語` is accepted unchanged.

### T-04 TaskStore load and save (basic persistence)
- Goal: add `TaskStore` with `load() -> tuple[list[Task], int]` and `save(tasks, next_id) -> None`. Missing, empty or whitespace-only file gives `([], 1)`. Strict schema check on load (JSON object with `next_id` and `tasks`; types; status in {open, done}; duplicate ids; `next_id` greater than every id) raising `StorageError` for corrupt data, `OSError` or `UnicodeDecodeError` also mapped to `StorageError`. Save writes UTF-8 with `ensure_ascii=False` to a temp file in the same directory, then `os.replace`; temp file removed on failure; save is never called on read paths.
- Files touched: `todo/app.py`, `tests/test_todo.py`.
- FR/NFR ids: FR-012, FR-013, NFR-005, NFR-006, NFR-007.
- Done-when: tests pass for round-trip of Unicode titles, missing file, empty file, invalid JSON, wrong shape, duplicate ids, bad status, `next_id` not above max id; corrupt files keep identical bytes after a failed load; no leftover temp files in the directory after save or failed save.

### T-05 A-3: strict load rejects bool ids and empty stored titles (source: design-review.md A-3, finding F-03)
- Goal: in `load`, reject `bool` for task `id` and for `next_id` (`isinstance` int check must exclude `bool`), require `title` to be `str`, and treat a stored title that is empty after strip as corrupt.
- Files touched: `todo/app.py`, `tests/test_todo.py`.
- FR/NFR ids: FR-013, NFR-005.
- Done-when: tests pass where `{"id": true}`, `{"next_id": true}`, a non-string title, an empty title and a whitespace-only stored title each raise `StorageError` and leave the file bytes unchanged.

### T-06 A-6: UTF-8 BOM is treated as corrupt (source: design-review.md A-6, finding F-08)
- Goal: keep strict `utf-8` decoding on load (no `utf-8-sig`), so a file starting with a BOM is reported as corrupt.
- Files touched: `todo/app.py`, `tests/test_todo.py`.
- FR/NFR ids: FR-013, NFR-005, NFR-006.
- Done-when: a test writes a BOM-prefixed otherwise valid file; `load` raises `StorageError`; via `main` (after T-10) it exits 1 with the file bytes unchanged.

### T-07 A-1 (save part): encoding errors become StorageError (source: design-review.md A-1, finding F-01)
- Goal: in `save`, convert `UnicodeEncodeError` and `TypeError`/`ValueError` raised while serialising or encoding into `StorageError` with a plain message, with the original file untouched and no temp file left.
- Files touched: `todo/app.py`, `tests/test_todo.py`.
- FR/NFR ids: FR-002, NFR-003, NFR-004, NFR-005, NFR-006.
- Done-when: a test saves a task whose title contains a lone surrogate (for example the character U+D800) and asserts `StorageError`, the pre-existing file bytes unchanged, and no stray temp file.

### T-08 Command operations
- Goal: add `add_task`, `list_tasks`, `complete_task` (returns True if changed, False if already done), `reopen_task` (mirror), `delete_task`. New task takes `next_id`, then the counter is stored as `next_id + 1`; delete never decrements. Operations save only after success in memory and never on no-op or read. Title is normalised before the store is loaded.
- Files touched: `todo/app.py`, `tests/test_todo.py`.
- FR/NFR ids: FR-001, FR-002, FR-003, FR-004, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, NFR-005.
- Done-when: tests pass for first id 1; ids 1,2,3 then delete 3 then add gives 4; delete highest then new `TaskStore` instance (restart) still gives a never-issued id; duplicate titles get distinct ids; creation-order list; complete/reopen flip status and persist; already-done and already-open return False and leave the file bytes unchanged; delete removes the task; unknown id 99 raises `TaskNotFoundError` and leaves bytes unchanged.

### T-09 CLI parsing, usage and exit 2, with A-5 (source: design-review.md A-5, finding F-07)
- Goal: hand-written argv parsing in `main(argv: list[str] | None = None) -> int` and `build_usage() -> str`. No command, unknown command, `add` without or with extra arguments, `complete`/`reopen`/`delete` without an id or with extra arguments, and extra arguments on `list` print usage to stderr and return 2 without touching the store. A-5: `-h` (and `--help`) prints usage to stdout and returns 0. Usage text lists all commands with an example and says multi-word titles must be quoted. `-1` as an id is read as an id (not an option); a title starting with `-` is accepted as the title for `add`.
- Files touched: `todo/cli.py`, `tests/test_todo.py`.
- FR/NFR ids: FR-014, NFR-003, NFR-004, NFR-008.
- Done-when: tests pass asserting return 2, usage on stderr, empty stdout and unchanged/absent `tasks.json` for each usage-error case; `-h` and `--help` return 0 with usage on stdout and empty stderr; `main(["complete", "-1"])` returns 1 (not 2).

### T-10 CLI output, error mapping and A-1 (output part) (source: design-review.md A-1, finding F-01)
- Goal: wire `main` to the operations. `add` prints `Added: <id> [open] <title>`; `list` prints `<id> [open|done] <title>` per line or `No tasks.`; `complete`/`reopen`/`delete` print nothing on success; already-done/already-open print `Task <id> is already done.` / `Task <id> is already open.` on stdout with 0. `TodoError` is caught, written to stderr as `Error: <message>`, return 1, no traceback. A-1: `main` catches `UnicodeEncodeError` raised while writing output, writes a plain message to stderr and returns 1. `main` calls no `reconfigure` and has no global side effects (see T-11).
- Files touched: `todo/cli.py`, `tests/test_todo.py`.
- FR/NFR ids: FR-001, FR-002, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, NFR-003, NFR-004, NFR-005, NFR-006.
- Done-when: tests pass for exact stdout text and return code of each command; empty and whitespace-only titles and control-character titles (R-1) give stderr error, return 1, no file created; ids `abc`, `0`, `-1`, `99` give the same not-found error, return 1, file bytes unchanged; corrupt file gives return 1, `Error:` on stderr with no `Traceback` text, file bytes unchanged; a stdout stream that cannot encode the title (a test double with ASCII encoding) makes `main` return 1 with a plain stderr message and no traceback.

### T-11 A-4: stream reconfigure only under the `__main__` guard (source: design-review.md A-4, finding F-04)
- Goal: add the `if __name__ == "__main__"` guard that, before calling `sys.exit(main())`, reconfigures stdout and stderr to UTF-8 where supported. `main` itself performs no reconfigure and mutates no global state, so tests that capture output are unaffected.
- Files touched: `todo/cli.py`, `tests/test_todo.py`.
- FR/NFR ids: NFR-006, NFR-009, FR-014.
- Done-when: a test replaces `sys.stdout`/`sys.stderr` with plain `io.StringIO` objects (no `reconfigure` attribute) and `main` runs without error; a test asserts the streams' encodings are not altered by calling `main`; manual check `python -m todo.cli list` in an empty temp directory prints `No tasks.` and exits 0.

### T-12 Final quality gates
- Goal: confirm the whole suite and static gates, and review for PEP 8, type hints, no bare `except:`, no network or non-stdlib imports.
- Files touched: `todo/__init__.py`, `todo/app.py`, `todo/cli.py`, `tests/test_todo.py` (fixes only, if a gate fails).
- FR/NFR ids: NFR-001, NFR-002, NFR-007, NFR-008, NFR-009.
- Done-when: `python -m unittest discover -s tests -v` exits 0 with all tests listed passing; `python -m compileall -q .` exits 0 with no output; `python --version` shows 3.11 or later; the import-scan tests (see Test plan) pass.

## File-level change list
| File | Changes |
|------|---------|
| `todo/__init__.py` | New. Package marker, optionally `__version__`. No logic (T-01). |
| `todo/app.py` | New. `Task`; `TodoError`, `ValidationError`, `TaskNotFoundError`, `StorageError`; `normalize_title` with control-character rejection (T-02, T-03); `parse_task_id` (T-02); `TaskStore.load` with strict shape, bool, empty-title and BOM-as-corrupt checks (T-04, T-05, T-06); `TaskStore.save` atomic write with encoding errors to `StorageError` (T-04, T-07); `add_task`, `list_tasks`, `complete_task`, `reopen_task`, `delete_task` (T-08). Never prints, never exits. |
| `todo/cli.py` | New. `build_usage`; `main` with hand-written parsing, `-h`, usage exit 2, output formatting, `TodoError` and `UnicodeEncodeError` mapping to stderr and exit 1 (T-09, T-10); `__main__` guard with stream reconfigure and `sys.exit(main())` (T-11). |
| `tests/test_todo.py` | New. `unittest` classes per FR/NFR, temp directories, output-capture helper; tests listed in the Test plan. |

## Test plan
All tests are in `tests/test_todo.py`, run with `python -m unittest discover -s tests -v`. Names are class.method; each class is named for the ids it covers.

| Id | Test name(s) or manual check |
|----|------------------------------|
| FR-001 | `TestFR001Add.test_add_creates_open_task_with_id`, `test_add_prints_added_line_exit_0`, `test_duplicate_titles_get_unique_ids` |
| FR-002 | `TestFR002Title.test_title_trimmed`, `test_empty_title_rejected_exit_1_no_file`, `test_whitespace_title_rejected`, `test_long_title_accepted`, `test_unicode_title_unchanged` |
| FR-002 (R-1, A-2) | `TestR1ControlChars.test_newline_title_rejected`, `test_tab_inside_title_rejected`, `test_escape_sequence_title_rejected`, `test_control_char_rejected_via_main_exit_1_stderr_no_file`, `test_control_char_rejection_leaves_existing_file_unchanged`, `test_non_cc_unicode_accepted` |
| FR-003 | `TestFR003Ids.test_first_id_is_1`, `test_id_not_reused_after_delete`, `test_id_not_reused_after_delete_highest_and_restart` |
| FR-004 | `TestFR004List.test_list_creation_order_format`, `test_list_exit_0`, `test_list_one_line_per_task` |
| FR-005 | `TestFR005EmptyList.test_no_tasks_message_exit_0` |
| FR-006 | `TestFR006Complete.test_complete_open_task_silent_exit_0` |
| FR-007 | `TestFR007CompleteDone.test_already_done_message_no_change_exit_0` |
| FR-008 | `TestFR008Reopen.test_reopen_done_task_silent_exit_0` |
| FR-009 | `TestFR009ReopenOpen.test_already_open_message_no_change_exit_0` |
| FR-010 | `TestFR010Delete.test_delete_removes_task_silent_exit_0` |
| FR-011 | `TestFR011BadId.test_unknown_id_99_exit_1_no_change`, `test_abc_zero_negative_same_not_found_error`, `test_bad_id_for_complete_reopen_delete` |
| FR-012 | `TestFR012Persistence.test_add_visible_in_later_run`, `test_complete_reopen_delete_persist`, `test_next_id_stored_in_same_file`, `test_missing_file_is_empty_list`, `test_empty_file_is_empty_list`, `test_file_is_utf8_json_in_cwd` |
| FR-013 | `TestFR013Corrupt.test_invalid_json_exit_1_file_untouched`, `test_wrong_shape_is_corrupt`, `test_duplicate_ids_corrupt`, `test_unreadable_file_exit_1` |
| FR-013 (A-3) | `TestA3StrictLoad.test_bool_task_id_corrupt`, `test_bool_next_id_corrupt`, `test_non_string_title_corrupt`, `test_empty_stored_title_corrupt`, `test_whitespace_stored_title_corrupt` |
| FR-013 (A-6) | `TestA6Bom.test_bom_file_is_corrupt_exit_1_file_untouched` |
| FR-014 | `TestFR014Usage.test_no_command_exit_2`, `test_unknown_command_exit_2`, `test_add_without_title_exit_2`, `test_complete_without_id_exit_2`, `test_extra_arguments_exit_2`, `test_usage_errors_change_no_data` |
| FR-014 / NFR-003 (A-5) | `TestA5Help.test_dash_h_prints_usage_stdout_exit_0`, `test_double_dash_help_exit_0` |
| NFR-001 | Manual check `python --version` expecting 3.11 or later; `TestNFR001.test_python_version_at_least_3_11` (`sys.version_info`) |
| NFR-002 | `TestNFR002.test_only_stdlib_imports` (scan `todo/*.py` and test imports against `sys.stdlib_module_names` plus the `todo` package) |
| NFR-003 | `TestNFR003ExitCodes.test_success_and_already_cases_exit_0`, `test_errors_exit_1_message_on_stderr`, `test_usage_exit_2` |
| NFR-004 | `TestNFR004ErrorClarity.test_errors_on_stderr_not_stdout`, `test_no_traceback_in_any_error`, `test_error_messages_are_plain_language` |
| NFR-004 / NFR-003 (A-1) | `TestA1EncodingErrors.test_save_lone_surrogate_raises_storage_error_file_untouched`, `test_main_surrogate_title_exit_1_no_traceback`, `test_main_unencodable_stdout_exit_1_plain_stderr` |
| NFR-005 | `TestNFR005DataSafety.test_rejected_commands_leave_file_bytes_identical`, `test_corrupt_file_never_overwritten`, `test_no_temp_file_left_behind` |
| NFR-006 | `TestNFR006Unicode.test_unicode_roundtrip_through_file_and_output`, `test_file_written_without_ascii_escapes` |
| NFR-006 / NFR-009 (A-4) | `TestA4NoGlobalSideEffects.test_main_works_with_plain_stringio_streams`, `test_main_does_not_alter_stream_encoding`; manual check `python -m todo.cli list` in an empty temp directory expecting `No tasks.` and exit 0 |
| NFR-007 | `TestNFR007NoNetwork.test_no_network_modules_imported` (scan sources for `socket`, `urllib`, `http`, `ssl`, `requests`) |
| NFR-008 | Manual check `python -m compileall -q .` (no output, exit 0); `TestNFR008Quality.test_no_bare_except`, `test_functions_have_type_hints` (scan source with `ast`) |
| NFR-009 | Manual checks `python -m unittest discover -s tests -v` (exit 0) and `python -m compileall -q .` (exit 0); this plan maps every FR to a test |

## Known deviations
- `artifacts/requirements.md` and `artifacts/architecture.md` do not yet reflect R-1 and A-1..A-6. `artifacts/design-review.md` is the authority for them. The human chose to proceed without reopening those phases (source: human, chat).
- R-1 is folded into FR-002 by this plan only; no new requirement id exists. The requirements file still lists FR-002 without the control-character rule.
- Plan-level interpretations of R-1 (flagged for the human, not decided by this plan beyond the literal wording): "control character" is taken as Unicode category `Cc` only, so printable Unicode, emoji joiners and non-ASCII spaces remain accepted (FR-002 and NFR-006 say any Unicode is stored unchanged); and trimming happens first, so a title with only a leading or trailing newline or tab (for example `"buy milk\n"`) is trimmed and accepted, while one with an interior control character is rejected.
- Architecture D8 ("reconfigure where reconfigurable") is superseded by A-4: reconfigure only under the `__main__` guard.
- Architecture error table is silent on the messages for control-character titles and encoding errors; the implementation uses plain-language messages starting with `Error:` (NFR-004).
- Accepted risks, no task (source: `design-review.md`): F-05 (raw id echoed in not-found message), F-06 (temp-file mode, Windows replace behaviour, fsync), F-09 (raw-id strings in the `app` API), and the NFR-001 verification note of F-08.

## Rollback notes
Use `git revert` of the task's commit (no history rewrite, no force push). Where a task has no separate commit, the file-level steps below apply. Later tasks depend on earlier ones, so revert in reverse order.
| Task | Rollback |
|------|----------|
| T-01 | Delete `todo/__init__.py` and `tests/test_todo.py` (or `git revert` the commit). |
| T-02 | `git revert`; removes the exceptions, `Task`, `normalize_title`, `parse_task_id` and their tests. Revert T-03 onward first. |
| T-03 | `git revert`; `normalize_title` goes back to trim-and-reject-empty only, and the R-1 tests are removed together with it. |
| T-04 | `git revert`; removes `TaskStore`. No data files are created outside temp directories, so no cleanup beyond deleting any stray `tasks.json` made by manual runs. |
| T-05 | `git revert`; load returns to the T-04 checks. |
| T-06 | `git revert`; no data impact. |
| T-07 | `git revert`; save returns to T-04 behaviour. |
| T-08 | `git revert`; removes the operations and their tests. Revert T-09 and T-10 first. |
| T-09 | `git revert`, or delete `todo/cli.py` if it was introduced here. |
| T-10 | `git revert`; CLI returns to the T-09 usage-only state. |
| T-11 | `git revert`; removes the `__main__` guard only. |
| T-12 | `git revert` the fix commit if one exists; otherwise nothing to undo. |
Manual runs of the CLI create `tasks.json` in the working directory; delete that file if a manual check was run in the repository root (use a temporary directory to avoid this).
