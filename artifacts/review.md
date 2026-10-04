# Code Review

## Summary
Re-review after the human rejection. The earlier review (finding R-01, 85 full-suite failures) is stale and superseded by this file. All findings below were re-derived against the current code.

Evidence (real output, run during this review):
- `python -m compileall -q .` -> no output, exit code 0.
- `python -m unittest tests.test_todo` -> `Ran 77 tests in 0.577s` / `OK`.
- `python -m unittest discover -s tests -v` -> `Ran 167 tests in 3.733s` / `OK`. Full suite passes; the infrastructure tests (test_guard, test_config, test_e2e_pipeline, test_orchestrator) no longer fail.
- `python orchestrator.py check` -> `all checks passed` (exit 0).
- `python orchestrator.py status` -> phase 6 `review` ACTIVE, NOT_SUBMITTED.

`todo/app.py` and `todo/cli.py` implement FR-001..FR-014 and the design-review items R-1 and A-1..A-6 correctly. Checks done: PEP 8 style, type hints on all signatures, only specific exceptions, stdlib-only imports, no network, no secrets, atomic save with temp-file cleanup, validate-before-load, save only on change. The tests are meaningful (exact stdout/stderr/exit codes, byte-identical file checks, corrupt-file cases, encoding errors) and none are skipped. They use temp directories and do not touch real user data. No Blocker or Major finding remains. The open items are Minor or Nit, mostly accepted risks and documentation drift.

## Findings
| id | severity | file:line | finding | FR/NFR ids | recommendation |
|----|----------|-----------|---------|------------|----------------|
| R-01 | Minor | artifacts/requirements.md:19-24, artifacts/architecture.md:89 (D-table) | `requirements.md` FR-002 still has no control-character rule (R-1), and `architecture.md` still lacks A-1..A-6 (control-char validation, bool/empty-title load checks, encoding errors to `StorageError`, reconfigure only under `__main__`, `-h` exits 0, BOM is corrupt). It still carries the superseded D8 ("reconfigure where reconfigurable"). The plan records this as a known deviation (human chose to proceed). Code follows `design-review.md`, so the approved artifacts and the code disagree. | FR-002, FR-004, FR-013, FR-014, NFR-003, NFR-004, NFR-006 | Human to reopen requirements/architecture and fold in R-1 and A-1..A-6, or keep recording it as an accepted deviation. |
| R-02 | Minor | hooks/README.md:3-4, 38-39 | Still describes the VS Code (Local agent) hook discovered through `.github/hooks/hooks.json` and the `chat.useHooks` setting. The repo now uses the Claude Code layout (`.claude/settings.json`). Out of scope for `todo/`, but documentation is stale. | (none; docs) | Update the file to the Claude Code hook layout. It is outside the review phase's allowed files, so this is a human or later-phase task. |
| R-03 | Minor | todo/cli.py:56-57 and todo/app.py:171-178 | `add` saves first and prints afterwards. If printing fails (`UnicodeEncodeError` on a non-UTF-8 console), exit is 1 but the task is already persisted (design-review F-01 noted this). Behaviour is tested (`test_unencodable_stdout_exit_1_plain_stderr`) but the "data saved while exit 1" state is not asserted or documented. | FR-001, NFR-003, NFR-005, NFR-006 | Accept and document, or print the line before the save is committed. |
| R-04 | Minor | todo/app.py:120 (`_validate`) | Load does not reject control characters in a stored title (for example `"a\nb"` in a hand-edited file), so `list` can print more than one line per task and pass escape sequences to the terminal. This conflicts with FR-004 "one per line" and is inconsistent with R-1 on write. Not covered by A-3. | FR-004, FR-013, NFR-004 | Treat control characters in a stored title as corrupt, or sanitise on output. Add a test. |
| R-05 | Minor | todo/app.py:56, 190 | Not-found message echoes the raw user-supplied id (`task not found: <raw>.`) including control or escape characters. This is accepted risk F-05 in `design-review.md` and in the plan. | FR-011, NFR-004 | Echo `repr(raw)` or truncate. No action needed if the risk stays accepted. |
| R-06 | Minor | todo/cli.py:33-39 (`_write_error`) | The fallback write to stderr in the `except UnicodeEncodeError` branch is not guarded. A failing second write (closed or broken stderr, `OSError`) would propagate as a traceback. The first write is guarded only for encoding errors. | NFR-004, NFR-003 | Wrap the fallback in `except (OSError, ValueError)` and still return the intended exit code. |
| R-07 | Minor | todo/app.py:45 | Rejection uses Unicode category `Cc` only. U+2028/U+2029 (Zl/Zp, line/paragraph separators) are accepted, and these can break a line in some terminals. This matches the plan's documented interpretation (Cc only; `strip()` trims edges), so it is a note, not a defect. | FR-002, FR-004, NFR-006 | Human to confirm that Cc-only is intended. Optionally also reject Zl/Zp. |
| R-08 | Nit | todo/cli.py:55 and todo/app.py:173 | For `add`, the title is normalised twice (`normalize_title` in `cli`, then again inside `add_task`). Harmless because it is idempotent, but redundant. | FR-002 | Drop the call in `cli.py`; `add_task` already validates before loading. |
| R-09 | Nit | tests/test_todo.py (whole file) | Test class and method names differ from the plan's Test plan (for example `TestFR002Title.test_empty_and_whitespace_rejected` vs `test_empty_title_rejected_exit_1_no_file`; `TestOperations`, `TestCliCommands` and `TestCliErrors` group several FRs). Every FR is covered and cited in docstrings, so the content matches even though the names do not. | all FR | Update the plan's test names, or accept. |
| R-10 | Nit | todo/app.py:68-71, 186-190 | `_corrupt` and `_find` lack docstrings. Type hints are present. | NFR-008 | Optional docstrings. |

## Traceability matrix
| Id | Code location | Test(s) in tests/test_todo.py |
|----|---------------|-------------------------------|
| FR-001 | app.py:171-178 `add_task`; cli.py:54-58 | `TestOperations.test_first_id_is_1_and_open`, `test_duplicate_titles_get_unique_ids`; `TestCliCommands.test_add_prints_added_line` |
| FR-002 | app.py:40-47 `normalize_title`; app.py:173 | `TestFR002Title.*`; `TestR1ControlChars.*`; `TestOperations.test_invalid_title_creates_no_file`, `test_invalid_title_checked_before_load`; `TestCliErrors.test_bad_titles_exit_1_no_file`, `test_control_char_rejection_keeps_existing_file`, `test_surrogate_title_exit_1_no_traceback` |
| FR-003 | app.py:171-178, 214-220 (`next_id` counter) | `TestOperations.test_id_not_reused_after_delete`, `test_id_not_reused_after_delete_highest_and_restart`; `TestCliCommands.test_persistence_across_runs` |
| FR-004 | cli.py:59-66; app.py:181-183 | `TestOperations.test_list_creation_order`; `TestCliCommands.test_list_format_and_order` |
| FR-005 | cli.py:63-65 | `TestCliCommands.test_empty_list_message`; `TestA4NoGlobalSideEffects.test_python_dash_m_runs_in_empty_dir` |
| FR-006 | app.py:193-206 | `TestOperations.test_complete_reopen_persist`; `TestCliCommands.test_complete_silent` |
| FR-007 | app.py:197-198; cli.py:83-85 | `TestOperations.test_already_done_and_open_return_false_bytes_unchanged`; `TestCliCommands.test_complete_already_done` |
| FR-008 | app.py:209-211 | `TestOperations.test_complete_reopen_persist`; `TestCliCommands.test_reopen_silent` |
| FR-009 | app.py:197-198; cli.py:83-85 | `TestOperations.test_already_done_and_open_return_false_bytes_unchanged`; `TestCliCommands.test_reopen_already_open` |
| FR-010 | app.py:214-220 | `TestOperations.test_delete_removes_task`; `TestCliCommands.test_delete_silent_and_removed` |
| FR-011 | app.py:50-56 `parse_task_id`; app.py:186-190 `_find` | `TestFR011ParseId.*`; `TestOperations.test_unknown_id_raises_bytes_unchanged`; `TestCliErrors.test_bad_ids_same_not_found_error` |
| FR-012 | app.py:74-168 `TaskStore`; DEFAULT_FILE app.py:59 | `TestFR012Store.*`; `TestCliCommands.test_persistence_across_runs`, `test_file_is_utf8_json_in_cwd` |
| FR-013 | app.py:82-130 `load`/`_validate` | `TestFR013Corrupt.*`; `TestA3StrictLoad.*`; `TestA6Bom.*`; `TestCliErrors.test_corrupt_file_exit_1_untouched`, `test_bom_file_exit_1_untouched`, `test_unreadable_file_exit_1` |
| FR-014 | cli.py:42-69 `_run`/`_usage_error`; cli.py:11-25 `build_usage` | `TestFR014Usage.*`; `TestA5Help.test_help_flags` |
| NFR-001 | whole code base (3.11 syntax, e.g. `X | Y` hints) | `TestNFRQuality.test_python_version_at_least_3_11` |
| NFR-002 | app.py:6-12; cli.py:3-6 | `TestNFRQuality.test_only_stdlib_imports` |
| NFR-003 | cli.py:89-101 `main`; cli.py:42-44 | `TestFR014Usage`, `TestA5Help`, `TestCliCommands`, `TestCliErrors.assert_error` |
| NFR-004 | cli.py:33-39, 94-101; app.py error classes | `TestCliErrors.*` (no `Traceback`, `Error:` prefix on stderr, stdout empty), `test_errors_are_plain_language_on_stderr_only`, `test_unencodable_stdout_exit_1_plain_stderr` |
| NFR-005 | app.py:132-168 atomic save; app.py:197-198 (no save on no-op); app.py:173 (validate first) | `TestFR012Store.test_no_temp_file_left_after_save`; `TestA1SaveEncoding.*`; `TestOperations.test_list_does_not_write`, `test_unknown_id_raises_bytes_unchanged`; `CorruptMixin.assert_corrupt` users |
| NFR-006 | app.py:87, 142-143 (UTF-8, `ensure_ascii=False`); cli.py:104-108 | `TestFR012Store.test_roundtrip_unicode_and_no_ascii_escapes`; `TestNFR006Unicode.*`; `TestFR002Title.test_unicode_title_unchanged`; `TestR1ControlChars.test_non_cc_unicode_accepted` |
| NFR-007 | no network imports in `todo/` | `TestNFRQuality.test_no_network_modules_imported` |
| NFR-008 | all `todo/*.py` | `TestNFRQuality.test_no_bare_except`, `test_functions_have_type_hints`; `compileall` (exit 0) |
| NFR-009 | tests/test_todo.py; every FR above has a test | `python -m unittest discover -s tests -v` -> 167 tests OK; `compileall` exit 0 |

Design-review items: R-1/A-2 (app.py:45-46, `TestR1ControlChars`, `TestCliErrors.test_bad_titles_exit_1_no_file`); A-1 (app.py:144-148, cli.py:97-101, `TestA1SaveEncoding`, `TestCliErrors.test_surrogate_title_exit_1_no_traceback`, `test_unencodable_stdout_exit_1_plain_stderr`); A-3 (app.py:63-65, 106, 118-121, `TestA3StrictLoad`); A-4 (cli.py:104-108, `TestA4NoGlobalSideEffects`); A-5 (cli.py:51-53, `TestA5Help`); A-6 (app.py:87, `TestA6Bom`, `test_bom_file_exit_1_untouched`).

## Plan adherence
| Task | Status | Note |
|------|--------|------|
| T-01 | done | `todo/__init__.py` exists; scaffold and temp-dir helpers in tests. |
| T-02 | done | Errors, `Task`, `normalize_title`, `parse_task_id`. |
| T-03 | done | Cc rejection after trim, before load; Cc-only interpretation as documented in the plan (see R-07). |
| T-04 | done | `TaskStore` load/save, strict schema, atomic write. |
| T-05 | done | bool, non-string and empty stored title rejected. |
| T-06 | done | Strict `utf-8` decode; BOM is corrupt. |
| T-07 | done | `UnicodeEncodeError`/`TypeError`/`ValueError` become `StorageError`; no temp file left. |
| T-08 | done | Operations; saves only on change; title validated before load. |
| T-09 | done | Hand-written parser, usage on stderr with exit 2, `-h`/`--help` exit 0. |
| T-10 | done | Output formats, `Error:` mapping, `UnicodeEncodeError` handling (but see R-03, R-06). |
| T-11 | done | Reconfigure only under `__main__` guard; verified by tests and a subprocess run. |
| T-12 | done | compileall exit 0; full suite 167 OK; static-check tests pass; Python version test passes. Test names differ from the plan (R-09), so the status is done rather than deviated for content. |

Known deviations carried from the plan: R-01 (requirements/architecture not updated for R-1 and A-1..A-6), accepted risks F-05, F-06 and F-09.

Verdict: APPROVE
