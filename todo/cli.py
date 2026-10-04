"""Command-line layer: parsing, output formatting, exit codes."""

import sys
from typing import TextIO

from todo import app

_ID_COMMANDS = ("complete", "reopen", "delete")


def build_usage() -> str:
    """Return the usage text."""
    return (
        "Usage: python -m todo.cli <command> [argument]\n"
        "\n"
        "Commands:\n"
        "  add <title>      Add a task. Quote multi-word titles.\n"
        "  list             List all tasks.\n"
        "  complete <id>    Mark a task done.\n"
        "  reopen <id>      Mark a task open again.\n"
        "  delete <id>      Remove a task.\n"
        "\n"
        "Example: python -m todo.cli add \"buy milk\"\n"
        "Tasks are stored in tasks.json in the current folder."
    )


def _write(stream: TextIO, text: str) -> None:
    """Write a line to stream; may raise UnicodeEncodeError."""
    stream.write(text + "\n")


def _write_error(text: str) -> None:
    """Write to stderr, escaping characters the stream cannot encode."""
    try:
        _write(sys.stderr, text)
    except UnicodeEncodeError:
        safe = text.encode("ascii", "backslashreplace").decode("ascii")
        _write(sys.stderr, safe)


def _usage_error() -> int:
    _write_error(build_usage())
    return 2


def _run(args: list[str]) -> int:
    if not args:
        return _usage_error()
    command, rest = args[0], args[1:]
    if command in ("-h", "--help"):
        _write(sys.stdout, build_usage())
        return 0
    if command == "add" and len(rest) == 1:
        title = app.normalize_title(rest[0])
        task = app.add_task(app.TaskStore(), title)
        _write(sys.stdout, f"Added: {task.id} [{task.status}] {task.title}")
        return 0
    if command == "list" and not rest:
        tasks = app.list_tasks(app.TaskStore())
        if tasks:
            text = "\n".join(f"{t.id} [{t.status}] {t.title}" for t in tasks)
        else:
            text = "No tasks."
        _write(sys.stdout, text)
        return 0
    if command in _ID_COMMANDS and len(rest) == 1:
        return _run_id_command(command, rest[0])
    return _usage_error()


def _run_id_command(command: str, raw_id: str) -> int:
    store = app.TaskStore()
    if command == "delete":
        app.delete_task(store, raw_id)
        return 0
    if command == "complete":
        changed = app.complete_task(store, raw_id)
        state = "done"
    else:
        changed = app.reopen_task(store, raw_id)
        state = "open"
    if not changed:
        task_id = app.parse_task_id(raw_id)
        _write(sys.stdout, f"Task {task_id} is already {state}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run one command and return the exit code (0, 1 or 2)."""
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        return _run(args)
    except app.TodoError as exc:
        _write_error(f"Error: {exc}")
        return 1
    except UnicodeEncodeError:
        _write_error(
            "Error: output contains characters this terminal cannot display."
        )
        return 1


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    sys.exit(main())
