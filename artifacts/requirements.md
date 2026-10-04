# Requirements

## Source
`user_story.md` (Todo List), plus `docs/CONTRACT.md` and the human's answers recorded under Open Questions.

Quoted lines:
- "As a user, I want to manage a simple list of tasks from the command line so that I can keep track of what I need to do."
- "The tool is a small Python command-line application."
- "Task titles are free text entered by the user."

## Functional Requirements

### FR-001 Add a task
The system shall create a new task from a provided title, with a unique id and status "open".
- Given a non-empty title, when I add it, then a task exists with status "open" and an id not used by any other task, now or previously.
- The system prints `Added: <id> [open] <title>` and exits 0.
- Duplicate titles are allowed; ids remain unique.

### FR-002 Title validation
The system shall trim leading and trailing whitespace from a title and reject an empty or whitespace-only title.
- Given a title of `"  buy milk  "`, the stored title is `buy milk`.
- Given an empty or whitespace-only title, a clear error is written to stderr, no task is created, and the exit code is 1.
- There is no maximum title length.
- Titles may contain any Unicode characters and are stored and displayed unchanged.

### FR-003 Task ids
The system shall assign sequential positive integer ids starting at 1, and shall never reuse an id, even after the task is deleted.
- Given an empty list, the first task added gets id 1.
- Given tasks 1, 2, 3 and task 3 is deleted, the next task added gets id 4.
- Given the highest-id task has been deleted and the program is restarted, the next id is still never one previously issued.

### FR-004 List tasks
The system shall list every task in creation order, one per line, as `<id> [open|done] <title>`.
- Given tasks exist, each task appears exactly once, ordered by creation, with its id, status and title.
- Exit code is 0.

### FR-005 Empty list
The system shall print `No tasks.` when no tasks exist.
- Given no tasks, listing prints `No tasks.` and exits 0.

### FR-006 Complete a task
The system shall set the status of an open task to "done" when completed by id.
- Given an open task, when I complete it by id, its status becomes "done", nothing is printed, and exit code is 0.

### FR-007 Complete an already-done task
The system shall report that a task is already done, and change nothing, when asked to complete a done task.
- Given a done task, completing it prints a message saying it is already done, leaves the data unchanged, and exits 0.

### FR-008 Reopen a task
The system shall set the status of a done task to "open" when reopened by id.
- Given a done task, when I reopen it by id, its status becomes "open", nothing is printed, and exit code is 0.

### FR-009 Reopen an already-open task
The system shall report that a task is already open, and change nothing, when asked to reopen an open task.
- Given an open task, reopening it prints a message saying it is already open, leaves the data unchanged, and exits 0.

### FR-010 Delete a task
The system shall remove a task by id.
- Given an existing task, when I delete it by id, it no longer appears in the list, nothing is printed, and exit code is 0.

### FR-011 Unknown or invalid id
The system shall treat a missing, non-numeric, zero or negative id the same way for complete, reopen and delete: write a clear "not found" error to stderr, change nothing, and exit 1.
- Given an id that does not exist (for example 99), the command errors, nothing changes, and exit code is 1.
- Given `abc`, `0` or `-1` as the id, the command gives the same "not found" error, nothing changes, and exit code is 1.

### FR-012 Persistence
The system shall persist tasks between runs in a file named `tasks.json` in the current working directory, encoded as UTF-8 JSON, together with a next-id counter.
- Given a task added in one run, a later run lists it.
- Given a task completed, reopened or deleted in one run, a later run reflects that change.
- The next-id counter is stored in the same file.
- A missing or empty `tasks.json` means an empty list.

### FR-013 Unreadable stored data
The system shall report a clear error and leave the stored file untouched when `tasks.json` is corrupt or unreadable.
- Given a `tasks.json` that is not valid JSON or cannot be read, any command writes a clear error to stderr, exits 1, and does not modify the file.

### FR-014 Usage errors
The system shall print usage and exit 2 when arguments are wrong or missing, or when the command is unknown.
- Given no command, an unknown command, or a command missing its required argument (for example add without a title, complete without an id), usage is printed and the exit code is 2.
- No task data is changed.

## Non-Functional Requirements

### NFR-001 Runtime
The system shall run on Python 3.11 or later.

### NFR-002 Standard library only
The system shall use only the Python standard library, with no third-party packages, and its tests shall use `unittest` only.

### NFR-003 Exit codes and streams
The system shall exit 0 on success and on the "already done" / "already open" cases, exit 1 on errors (unknown id, invalid input, storage error) with the message on stderr, and exit 2 on usage errors.

### NFR-004 Error clarity
Every error message shall state what went wrong in plain language, shall not expose a stack trace to the user, and shall be written to stderr.

### NFR-005 Data safety
A failed or rejected command shall leave `tasks.json` unchanged. Corrupt or unreadable data shall never be overwritten.

### NFR-006 Unicode
The system shall read and write task titles as UTF-8 and preserve any Unicode text unchanged.

### NFR-007 No network
The application shall make no network calls.

### NFR-008 Code quality
The code shall follow PEP 8, have type hints on all function signatures, and catch only specific exceptions (no bare `except:`).

### NFR-009 Testability
Every FR shall be verifiable by an automated `unittest` test run via `python -m unittest discover -s tests -v`, and the code shall pass `python -m compileall -q .`.

## Constraints
- Small Python command-line application (user_story.md).
- Python 3.11+, standard library only, `unittest` only (docs/CONTRACT.md).
- Tasks stored in `tasks.json` in the current folder, UTF-8 JSON (human answer to Q1).
- Concurrent runs are out of scope (human).
- Requirements use IDs FR-### and NFR-###, and later artifacts must cite them (docs/CONTRACT.md).

## Assumptions
None

## Open Questions
- [x] Q1: Persistence. Each command-line call is a separate process. Should tasks survive between runs, so a task added now is still listed later? Or is the list in memory only for a single run?
  A: Yes. Tasks persist between runs, saved in tasks.json in the current folder (UTF-8 JSON).
- [x] Q2: Task ids. What form should a "unique id" take, for example sequential integers starting at 1? After a task is deleted, may its id be reused, or must ids never be reused?
  A: Sequential positive integers starting at 1. Ids are never reused, even after a delete (store a next-id counter in the file).
- [x] Q3: Invalid titles. What should happen if the title is empty or only whitespace? Is there a maximum length? Should leading and trailing whitespace be trimmed?
  A: Empty or whitespace-only title: reject with a clear error and create nothing. Trim leading and trailing whitespace. No maximum length.
- [x] Q4: Invalid id input. What should happen if the id given to complete, reopen or delete isn't a valid id, such as "abc" or "-1"? Should it be the same "clear error and nothing changes" as a missing id?
  A: Yes. A non-numeric, zero or negative id gets the same clear "not found" error as a missing id, and nothing changes.
- [x] Q5: Exit codes. Should error cases (unknown id, invalid input) make the tool exit with a non-zero code, with the message on stderr? Or should it exit 0 with only a message? Should the "already done" and "already open" cases also exit 0?
  A: Errors (unknown id, invalid input, storage error) exit 1 with the message on stderr. Success and the "already done" / "already open" cases exit 0. Wrong or missing arguments and unknown commands print usage and exit 2.
- [x] Q6: Confirmations. Should complete, reopen and delete print a confirmation on success?
  A: done, reopen and delete print nothing on success (exit 0). add prints "Added: <id> [open] <title>", list prints "<id> [open|done] <title>" per line, and an empty list prints "No tasks."
- [x] Q7: Unreadable stored data. If the stored task data is corrupt or unreadable, should the tool report an error and leave the data untouched, or start with an empty list?
  A: If the stored data is corrupt or unreadable: report a clear error (exit 1) and leave the file untouched. A missing or empty file means an empty list.
- [x] Q8: Duplicate titles. Are two tasks with the same title allowed?
  A: Duplicate titles are allowed; ids stay unique.
- [x] Additional human notes: Concurrent runs are out of scope, and titles may contain any Unicode (UTF-8).
