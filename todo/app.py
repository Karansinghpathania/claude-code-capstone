"""Domain model, validation, storage and command operations.

This module never prints and never calls ``sys.exit``.
"""

import contextlib
import json
import os
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Task:
    """One task; status is ``"open"`` or ``"done"``."""

    id: int
    title: str
    status: str


class TodoError(Exception):
    """Base class for expected, user-facing errors."""


class ValidationError(TodoError):
    """Invalid title."""


class TaskNotFoundError(TodoError):
    """Task id absent, non-numeric, zero or negative."""


class StorageError(TodoError):
    """tasks.json unreadable, corrupt, or not writable."""


def normalize_title(raw: str) -> str:
    """Trim whitespace; reject empty titles and control characters."""
    title = raw.strip()
    if not title:
        raise ValidationError("title must not be empty.")
    if any(unicodedata.category(ch) == "Cc" for ch in title):
        raise ValidationError("title must not contain control characters.")
    return title


def parse_task_id(raw: str) -> int:
    """Convert text to a positive int or raise TaskNotFoundError."""
    if raw.isascii() and raw.isdigit():
        value = int(raw)
        if value >= 1:
            return value
    raise TaskNotFoundError(f"task not found: {raw}.")


DEFAULT_FILE = "tasks.json"
_STATUSES = ("open", "done")


def _is_int(value: object) -> bool:
    """True for real ints only (bool is excluded)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _corrupt(reason: str) -> StorageError:
    return StorageError(
        f"cannot read {DEFAULT_FILE}: {reason}. The file was not changed."
    )


class TaskStore:
    """Loads and saves the task data file."""

    def __init__(self, path: Path | str | None = None) -> None:
        if path is None:
            path = Path.cwd() / DEFAULT_FILE
        self.path = Path(path)

    def load(self) -> tuple[list[Task], int]:
        """Return (tasks, next_id); raise StorageError if unusable."""
        if not self.path.exists():
            return [], 1
        try:
            text = self.path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _corrupt(f"not valid UTF-8 ({exc.reason})") from exc
        except OSError as exc:
            raise _corrupt(exc.strerror or "file cannot be read") from exc
        if not text.strip():
            return [], 1
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise _corrupt(f"not valid JSON ({exc})") from exc
        return self._validate(data)

    @staticmethod
    def _validate(data: object) -> tuple[list[Task], int]:
        if not isinstance(data, dict):
            raise _corrupt("unexpected structure")
        next_id = data.get("next_id")
        raw_tasks = data.get("tasks")
        if not _is_int(next_id) or next_id < 1:
            raise _corrupt("invalid next_id")
        if not isinstance(raw_tasks, list):
            raise _corrupt("invalid task list")
        tasks: list[Task] = []
        seen: set[int] = set()
        for item in raw_tasks:
            if not isinstance(item, dict):
                raise _corrupt("invalid task entry")
            task_id = item.get("id")
            title = item.get("title")
            status = item.get("status")
            if not _is_int(task_id) or task_id < 1:
                raise _corrupt("invalid task id")
            if not isinstance(title, str) or not title.strip():
                raise _corrupt("invalid task title")
            if status not in _STATUSES:
                raise _corrupt("invalid task status")
            if task_id in seen:
                raise _corrupt("duplicate task id")
            if task_id >= next_id:
                raise _corrupt("next_id is not above every task id")
            seen.add(task_id)
            tasks.append(Task(task_id, title, status))
        return tasks, next_id

    def save(self, tasks: list[Task], next_id: int) -> None:
        """Atomically write the data file as UTF-8 JSON."""
        payload = {
            "next_id": next_id,
            "tasks": [
                {"id": t.id, "title": t.title, "status": t.status}
                for t in tasks
            ],
        }
        try:
            text = json.dumps(payload, ensure_ascii=False, indent=2)
            data = text.encode("utf-8")
        except (UnicodeEncodeError, TypeError, ValueError) as exc:
            raise StorageError(
                f"cannot write {DEFAULT_FILE}: "
                "a title cannot be encoded as UTF-8."
            ) from exc
        tmp_name: str | None = None
        try:
            fd, tmp_name = tempfile.mkstemp(
                dir=self.path.parent, prefix=".tasks-", suffix=".tmp"
            )
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
            tmp_name = None
        except OSError as exc:
            raise StorageError(
                f"cannot write {DEFAULT_FILE}: "
                f"{exc.strerror or 'write failed'}."
            ) from exc
        finally:
            if tmp_name is not None:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_name)


def add_task(store: TaskStore, title: str) -> Task:
    """Create and persist an open task; the title is validated first."""
    clean = normalize_title(title)
    tasks, next_id = store.load()
    task = Task(next_id, clean, "open")
    tasks.append(task)
    store.save(tasks, next_id + 1)
    return task


def list_tasks(store: TaskStore) -> list[Task]:
    """Return tasks in creation order; never saves."""
    return store.load()[0]


def _find(tasks: list[Task], task_id: int, raw_id: str) -> Task:
    for task in tasks:
        if task.id == task_id:
            return task
    raise TaskNotFoundError(f"task not found: {raw_id}.")


def _set_status(store: TaskStore, raw_id: str, status: str) -> bool:
    task_id = parse_task_id(raw_id)
    tasks, next_id = store.load()
    task = _find(tasks, task_id, raw_id)
    if task.status == status:
        return False
    task.status = status
    store.save(tasks, next_id)
    return True


def complete_task(store: TaskStore, raw_id: str) -> bool:
    """Mark a task done; False if it already was."""
    return _set_status(store, raw_id, "done")


def reopen_task(store: TaskStore, raw_id: str) -> bool:
    """Mark a task open; False if it already was."""
    return _set_status(store, raw_id, "open")


def delete_task(store: TaskStore, raw_id: str) -> None:
    """Remove a task; the id counter is never decremented."""
    task_id = parse_task_id(raw_id)
    tasks, next_id = store.load()
    task = _find(tasks, task_id, raw_id)
    tasks.remove(task)
    store.save(tasks, next_id)
