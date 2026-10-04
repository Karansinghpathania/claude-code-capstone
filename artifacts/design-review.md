# Design Review

## Summary
The architecture is sound, small and well matched to the requirements and to docs/CONTRACT.md. It uses the stdlib only, has no network code, and writes only the contract file set (`todo/__init__.py`, `todo/app.py`, `todo/cli.py`, `tests/test_todo.py`). The `app.py` / `cli.py` split is justified by testability. Strict load validation, "save only after success" and atomic replace together address the data-loss concerns (NFR-005, FR-013). Every FR-001..FR-014 and NFR-001..NFR-009 maps to a component. The three interpretations (missing id vs nonexistent id, single quoted title for add, wrong-shape file is corrupt) were confirmed by the human and are not re-litigated here.

No High finding was found. The Medium findings concern uncaught Unicode errors that could produce a traceback (against NFR-004), and a gap between FR-002 and FR-004 for titles that contain newlines. The human has since decided these (see Human Decisions): control characters in titles are rejected, and F-01, F-03, F-04, -h and BOM handling are accepted. The verdict is APPROVE only on condition that the listed upstream requirements and architecture changes (Required upstream changes) are applied by the human before planning.

## Findings
| id | severity | area | finding | related FR/NFR ids | suggested change |
|----|----------|------|---------|--------------------|------------------|
| F-01 | Med | Error handling | `main` catches only `TodoError`. D3 maps `OSError`, `JSONDecodeError` and `UnicodeDecodeError` to `StorageError` inside the store. Encoding errors on the write path are not covered. A title containing lone surrogates (possible from argv via surrogateescape) makes `json.dumps(ensure_ascii=False)` followed by UTF-8 encoding raise `UnicodeEncodeError`. Printing a title the console cannot encode also raises it, and by then `add` has already saved. Either case gives a traceback and a wrong exit code (NFR-004, NFR-003). | FR-002, NFR-004, NFR-003, NFR-006 | In `save`, convert `UnicodeEncodeError` (and `TypeError`/`ValueError` from `json.dumps`) to `StorageError`. In `main`, catch `UnicodeEncodeError` around output and report a plain message on stderr with exit 1. Add tests for both. |
| F-02 | Med | Requirement gap | A title may contain newlines or control characters (the user quotes it, and FR-002 requires it to be stored unchanged). `list` would then print more than one line per task, which conflicts with FR-004 "one per line". ANSI escape sequences in titles would also be passed to the terminal unchanged. The design is silent on this. | FR-002, FR-004, NFR-006 | Ask the human (do not assume). Options are to reject control characters in titles, or to keep titles verbatim and document that `list` may span lines. Record the answer in the requirements, then add a test. |
| F-03 | Med | Data validation | `isinstance(x, int)` is true for `bool`, so `"id": true` or `"next_id": true` would pass the strict load (D7). The design also does not say whether an empty or whitespace-only stored `title` is valid. | FR-013, NFR-005 | State that load rejects `bool` for `id` and `next_id`, and requires `title` to be a `str`. Optionally reject titles that are empty after strip. Add corrupt-shape tests for these cases. |
| F-04 | Med | Testability | D8 reconfigures stdout/stderr "where reconfigurable". If this runs inside `main`, tests that capture output via `StringIO` or `redirect_stdout` either hit the missing-`reconfigure` path or have the interpreter streams altered as a side effect. | NFR-009, NFR-006 | Do the `reconfigure(encoding="utf-8")` call only under the `if __name__ == "__main__"` guard, or in a helper `main` does not call. Keep `main` free of global side effects. |
| F-05 | Low | Security / robustness | The not-found message echoes the raw user-supplied id (`task not found: <id>`), including any control or escape characters. | FR-011, NFR-004 | Echo `repr()` of the id, or truncate it. |
| F-06 | Low | Persistence | `tempfile.mkstemp` creates the temp file with mode 0600, so after `os.replace` `tasks.json` may change permissions. On Windows, `os.replace` can fail if another process holds the file open. fsync before replace is not specified. The temp file name and cleanup on failure are only partly described. | FR-012, NFR-005 | Say that the temp file is created in the same directory, flushed and fsynced, and removed in a `finally`. Treat a replace failure as `StorageError`. Note that the file mode may change. |
| F-07 | Low | Usability | The design does not say what `-h`, `--help` or `help` do. A hand-written parser would treat them as an unknown command (usage on stderr, exit 2), which is allowed by FR-014 but unfriendly. | FR-014, NFR-003 | Optionally treat `-h` and `--help` as usage on stdout with exit 0. Otherwise state that they are unknown commands. Either way, test it. |
| F-08 | Low | Spec precision | NFR-001 is covered by "Python 3.11+ features only", which is not testable. A UTF-8 BOM written by some Windows editors would make the file "corrupt" because of the strict `utf-8` decode. This is acceptable but should be a conscious choice. | NFR-001, FR-013 | Add a one-line statement of whether `utf-8-sig` is tolerated on read (suggest not, to keep behaviour simple). Optionally add a `sys.version_info` note in the plan. NFR-001 is verified by running under 3.11 or later. |
| F-09 | Low | Over-engineering | The `TaskStore` class plus three exception subclasses plus raw-id strings in the `app` API (`complete_task(store, raw_id: str)`) put CLI text parsing in the domain layer. This is small but slightly muddled. | NFR-009, NFR-008 | Acceptable as is. Optionally have `cli.py` call `parse_task_id` and pass `int` ids, so `app.py` operations take typed ids. |

## Human Decisions
Source: human, chat. Recorded as given.

- F-02: REJECT control characters. A title containing a newline, tab, escape or other control character is rejected like an empty title: clear error to stderr, exit 1, nothing created. Keeps "one task per line" (FR-004) and stops escape sequences reaching the terminal. (Note this extends FR-002 and needs a requirements update.)
- F-01 accepted (convert UnicodeEncodeError to StorageError in save; catch around output in main).
- F-03 accepted (reject bool as id/next_id; an empty stored title is corrupt).
- F-04 accepted (stdout reconfigure under the __main__ guard).
- F-05..F-09 optional: take the cheap ones (-h prints usage and exits 0; a BOM is treated as corrupt); note the rest as accepted risks.

## Finding dispositions
| id | disposition | note |
|----|-------------|------|
| F-01 | Accepted - change required | Architecture update (FR-002, NFR-003, NFR-004, NFR-006). |
| F-02 | Accepted - REJECT control characters | Requirements update and architecture update (FR-002, FR-004, NFR-006). |
| F-03 | Accepted - change required | Architecture update (FR-013, NFR-005). |
| F-04 | Accepted - change required | Architecture update (NFR-009, NFR-006). |
| F-05 | Accepted risk | Not changed. Largely reduced by F-02 only for titles; ids still echoed raw (FR-011, NFR-004). |
| F-06 | Accepted risk | Not changed (FR-012, NFR-005). |
| F-07 | Accepted - cheap fix | `-h` prints usage and exits 0 (FR-014, NFR-003). Architecture update. |
| F-08 | Accepted - BOM part only | A UTF-8 BOM is treated as corrupt (FR-013). Architecture states it. NFR-001 verification note is an accepted risk. |
| F-09 | Accepted risk | Not changed (NFR-008, NFR-009). |

## Required upstream changes
The human must reopen these phases before planning starts. This reviewer does not run reopen.

Requirements (reopen requirements):
- R-1: Add a new FR or rule: a title containing a newline, tab, escape or any other control character is rejected like an empty title, with a clear error on stderr, exit code 1, and no task created or file written. Cite FR-002 (extended) and FR-004 (one task per line).

Architecture (reopen architecture):
- A-1 (F-01): `save` converts `UnicodeEncodeError` (and `TypeError`/`ValueError` from `json.dumps`) to `StorageError`; `main` catches `UnicodeEncodeError` around output, prints a plain message to stderr and exits 1. (FR-002, NFR-003, NFR-004, NFR-006)
- A-2 (F-02): Title validation rejects control characters per R-1, before any save. (FR-002, FR-004)
- A-3 (F-03): Load rejects `bool` for `id` and `next_id`; an empty stored `title` is corrupt. (FR-013, NFR-005)
- A-4 (F-04): The stdout/stderr `reconfigure` call lives only under the `__main__` guard; `main` has no global side effects. (NFR-009, NFR-006)
- A-5 (F-07): `-h` prints usage and exits 0. (FR-014, NFR-003)
- A-6 (F-08): A UTF-8 BOM in `tasks.json` is treated as corrupt (strict `utf-8` decode). (FR-013)

## Risks
- Unhandled encoding errors can still leak a traceback or leave the data saved but the output failed (F-01).
- Title rendering conflicts with the "one per line" rule (F-02).
- Single large `tests/test_todo.py` (contract-fixed file set) must be organised by FR/NFR id to stay maintainable.
- Atomic replace behaves slightly differently on Windows (the primary platform here) than on POSIX (F-06).
- Hand-written argv parsing carries a risk of edge-case bugs (for example a title that begins with `-`, an empty-string id, extra arguments on `list`/`complete`). These need explicit tests.

## Alternatives considered and why rejected
1. `argparse` instead of a hand parser. Rejected by the design because `-1` would be read as an option and the usage exit code needs to be 2. This is reasonable. `argparse` exits with 2 on usage errors, so a custom subclass would be possible, but the negative-id handling and the human-confirmed "missing id = exit 2" split are simpler by hand. The cost is extra tests.
2. SQLite (`sqlite3`) instead of JSON. Rejected, which is correct: the human required `tasks.json`, and sqlite would add complexity with no benefit.
3. Derive the next id from `max(id) + 1` instead of storing a counter. Rejected, correctly: it would reuse the id after the highest task is deleted (FR-003).
4. Single-file module. Simpler, but the contract fixes `app.py` and `cli.py`; the split is also better for testability.
5. Write directly to `tasks.json` instead of temp plus replace. Rejected, correctly, for NFR-005. It is a small addition to the code.

## Security review
- No network, no `eval` or `pickle`, and no shell or subprocess calls. `json.load` is safe deserialisation, and strict validation after load prevents malformed data being trusted.
- File path is fixed (`tasks.json` in the cwd). There is no user-supplied path, so traversal is not a risk. A symlinked `tasks.json` would be replaced by a regular file on save (Low, noted under F-06).
- Terminal escape and control-character injection through titles and ids is a Low to Med concern (F-02, F-05).
- No secrets are handled.
- Uncaught encoding errors are the main robustness hole (F-01).

## Usability and accessibility review
- Messages are plain language, prefixed `Error:`, and go to stderr, so the meaning is not conveyed by colour. No colour is used.
- Exit codes are consistent: 0, 1 and 2 (NFR-003).
- Usage text is produced by `build_usage()`. The design does not say the usage text lists all commands with an example, including that multi-word titles must be quoted. This should be included. The `-h` behaviour is undefined (F-07).
- The "already done" and "already open" cases give a message on stdout with exit 0, as required.
- Silent success for complete, reopen and delete matches the human answer.

## Requirement coverage check
| Id | Result |
|----|--------|
| FR-001 | Covered (`add_task`, `cli`). See F-01 for the failure path. |
| FR-002 | Covered; see F-01, F-02. |
| FR-003 | Covered (persistent `next_id`). |
| FR-004 | Covered; see F-02. |
| FR-005 | Covered (`cli`). |
| FR-006 | Covered. |
| FR-007 | Covered. |
| FR-008 | Covered. |
| FR-009 | Covered. |
| FR-010 | Covered. |
| FR-011 | Covered; see F-05. |
| FR-012 | Covered; see F-06. |
| FR-013 | Covered; see F-03, F-08. |
| FR-014 | Covered; see F-07. |
| NFR-001 | Covered; see F-08. |
| NFR-002 | Covered. |
| NFR-003 | Covered; see F-01. |
| NFR-004 | Covered; see F-01, F-05. |
| NFR-005 | Covered; see F-03, F-06. |
| NFR-006 | Covered; see F-01, F-04. |
| NFR-007 | Covered. |
| NFR-008 | Covered; see F-09. |
| NFR-009 | Covered; see F-04. |

Approval is conditional on the upstream changes R-1 and A-1..A-6 being applied before planning. No High finding remains.

Verdict: APPROVE
