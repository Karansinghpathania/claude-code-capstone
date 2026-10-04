"""Tests for the todo tool (FR-001..FR-014, NFR-001..NFR-009)."""

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path


class TempDirTestCase(unittest.TestCase):
    """Base class: runs each test in a fresh temporary directory (NFR-007)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "tasks.json"
        self._old_cwd = os.getcwd()
        os.chdir(self.dir)
        self.addCleanup(os.chdir, self._old_cwd)

    def read_bytes(self) -> bytes:
        return self.path.read_bytes()


def run_main(argv: list[str]) -> tuple[int, str, str]:
    """Run cli.main with captured streams; return (code, stdout, stderr)."""
    from todo import cli

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


class TestScaffold(TempDirTestCase):
    """T-01: package imports and temp dir helper work (NFR-009)."""

    def test_package_importable(self) -> None:
        import todo

        self.assertTrue(todo.__doc__)

    def test_temp_dir_is_used(self) -> None:
        self.assertEqual(Path.cwd().resolve(), self.dir.resolve())
        self.assertFalse(self.path.exists())


class TestFR002Title(TempDirTestCase):
    """FR-002, NFR-006: title trimming and validation."""

    def test_title_trimmed(self) -> None:
        from todo.app import normalize_title

        self.assertEqual(normalize_title("  buy milk  "), "buy milk")

    def test_empty_and_whitespace_rejected(self) -> None:
        from todo.app import ValidationError, normalize_title

        for raw in ("", "   ", " \t\n "):
            with self.assertRaises(ValidationError):
                normalize_title(raw)

    def test_long_title_accepted(self) -> None:
        from todo.app import normalize_title

        self.assertEqual(len(normalize_title("x" * 100000)), 100000)

    def test_unicode_title_unchanged(self) -> None:
        from todo.app import normalize_title

        text = "café ☕ 日本語"
        self.assertEqual(normalize_title(text), text)


class TestFR011ParseId(TempDirTestCase):
    """FR-011: id parsing."""

    def test_valid_id(self) -> None:
        from todo.app import parse_task_id

        self.assertEqual(parse_task_id("7"), 7)

    def test_invalid_ids_not_found(self) -> None:
        from todo.app import TaskNotFoundError, parse_task_id

        for raw in ("abc", "0", "-1", "", "1.5", "١"):
            with self.assertRaises(TaskNotFoundError):
                parse_task_id(raw)


class TestR1ControlChars(TempDirTestCase):
    """FR-002 (R-1, A-2), FR-004, NFR-006: control characters rejected."""

    def test_interior_control_chars_rejected(self) -> None:
        from todo.app import ValidationError, normalize_title

        for raw in ("a\nb", "a\tb", "a\x1b[31mb", "a\x00b", "a\x7fb"):
            with self.assertRaises(ValidationError):
                normalize_title(raw)

    def test_edge_whitespace_trimmed_first(self) -> None:
        from todo.app import normalize_title

        self.assertEqual(normalize_title("buy milk\n"), "buy milk")

    def test_non_cc_unicode_accepted(self) -> None:
        from todo.app import normalize_title

        text = "café ☕ 日本語 a b \U0001F468‍\U0001F469"
        self.assertEqual(normalize_title(text), text)


ONE_TASK = '[{"id": 1, "title": "a", "status": "open"}]'


def task_json(task_id: object, title: object, status: object) -> str:
    """Return a one-task JSON array with the given raw values."""
    import json

    item = {"id": task_id, "title": title, "status": status}
    return json.dumps([item])


def valid_json(next_id: int = 2, tasks: str = ONE_TASK) -> bytes:
    """Return a valid tasks.json payload as bytes."""
    return f'{{"next_id": {next_id}, "tasks": {tasks}}}'.encode("utf-8")


class TestFR012Store(TempDirTestCase):
    """FR-012, NFR-005, NFR-006: TaskStore load and save."""

    def test_missing_file_is_empty_list(self) -> None:
        from todo.app import TaskStore

        self.assertEqual(TaskStore(self.path).load(), ([], 1))

    def test_empty_file_is_empty_list(self) -> None:
        from todo.app import TaskStore

        for content in (b"", b"  \n\t "):
            self.path.write_bytes(content)
            self.assertEqual(TaskStore(self.path).load(), ([], 1))

    def test_roundtrip_unicode_and_no_ascii_escapes(self) -> None:
        """NFR-006: titles stored unchanged, not as \\u escapes."""
        from todo.app import Task, TaskStore

        store = TaskStore(self.path)
        title = "café ☕ 日本語"
        store.save([Task(1, title, "done")], 2)
        self.assertEqual(store.load(), ([Task(1, title, "done")], 2))
        self.assertIn(title, self.read_bytes().decode("utf-8"))
        self.assertNotIn(b"\\u", self.read_bytes())

    def test_next_id_stored_in_same_file(self) -> None:
        import json

        from todo.app import TaskStore

        TaskStore(self.path).save([], 5)
        self.assertEqual(json.loads(self.read_bytes())["next_id"], 5)

    def test_no_temp_file_left_after_save(self) -> None:
        """NFR-005."""
        from todo.app import Task, TaskStore

        TaskStore(self.path).save([Task(1, "a", "open")], 2)
        self.assertEqual([p.name for p in self.dir.iterdir()], ["tasks.json"])

    def test_default_path_is_tasks_json_in_cwd(self) -> None:
        from todo.app import Task, TaskStore

        TaskStore().save([Task(1, "a", "open")], 2)
        self.assertTrue(self.path.exists())


class CorruptMixin(TempDirTestCase):
    """Helper: assert that content is reported as corrupt and kept as is."""

    def assert_corrupt(self, content: bytes) -> None:
        from todo.app import StorageError, TaskStore

        self.path.write_bytes(content)
        with self.assertRaises(StorageError):
            TaskStore(self.path).load()
        self.assertEqual(self.read_bytes(), content)


class TestFR013Corrupt(CorruptMixin):
    """FR-013, NFR-005: corrupt data raises StorageError, file untouched."""

    def test_invalid_json(self) -> None:
        self.assert_corrupt(b"{not json")

    def test_invalid_utf8(self) -> None:
        self.assert_corrupt(b"\xff\xfe\x00")

    def test_wrong_shape(self) -> None:
        for content in (b"[]", b'{"tasks": []}', b'{"next_id": 1}',
                        b'{"next_id": 1, "tasks": {}}',
                        b'{"next_id": 1, "tasks": [1]}',
                        b'{"next_id": 0, "tasks": []}'):
            self.assert_corrupt(content)

    def test_duplicate_ids_corrupt(self) -> None:
        task = '{"id": 1, "title": "a", "status": "open"}'
        self.assert_corrupt(valid_json(5, f"[{task}, {task}]"))

    def test_bad_status_corrupt(self) -> None:
        self.assert_corrupt(valid_json(2, task_json(1, "a", "x")))

    def test_next_id_not_above_max_corrupt(self) -> None:
        self.assert_corrupt(valid_json(1))

    def test_unreadable_path_is_storage_error(self) -> None:
        """FR-013: a directory named tasks.json cannot be read."""
        from todo.app import StorageError, TaskStore

        self.path.mkdir()
        with self.assertRaises(StorageError):
            TaskStore(self.path).load()


class TestA3StrictLoad(CorruptMixin):
    """FR-013 (A-3), NFR-005: strict type checks on load."""

    def test_bool_task_id_corrupt(self) -> None:
        self.assert_corrupt(valid_json(5, task_json(True, "a", "open")))

    def test_bool_next_id_corrupt(self) -> None:
        self.assert_corrupt(b'{"next_id": true, "tasks": []}')

    def test_non_string_title_corrupt(self) -> None:
        self.assert_corrupt(valid_json(2, task_json(1, 5, "open")))

    def test_empty_stored_title_corrupt(self) -> None:
        self.assert_corrupt(valid_json(2, task_json(1, "", "open")))

    def test_whitespace_stored_title_corrupt(self) -> None:
        self.assert_corrupt(valid_json(2, task_json(1, "  ", "open")))


class TestA6Bom(TempDirTestCase):
    """FR-013 (A-6), NFR-005, NFR-006: a UTF-8 BOM is treated as corrupt."""

    def test_bom_file_is_corrupt_file_untouched(self) -> None:
        from todo.app import StorageError, TaskStore

        content = b"\xef\xbb\xbf" + valid_json()
        self.path.write_bytes(content)
        with self.assertRaises(StorageError):
            TaskStore(self.path).load()
        self.assertEqual(self.read_bytes(), content)


class TestA1SaveEncoding(TempDirTestCase):
    """NFR-004, NFR-005, NFR-006 (A-1): encoding errors on save."""

    def test_save_lone_surrogate_raises_storage_error(self) -> None:
        from todo.app import StorageError, Task, TaskStore

        content = valid_json()
        self.path.write_bytes(content)
        with self.assertRaises(StorageError):
            TaskStore(self.path).save([Task(1, "bad\ud800", "open")], 2)
        self.assertEqual(self.read_bytes(), content)
        self.assertEqual([p.name for p in self.dir.iterdir()], ["tasks.json"])

    def test_failed_replace_leaves_no_temp_file(self) -> None:
        """NFR-005: a failed replace removes the temp file."""
        from unittest import mock

        from todo.app import StorageError, Task, TaskStore

        content = valid_json()
        self.path.write_bytes(content)
        with mock.patch("todo.app.os.replace", side_effect=OSError("boom")):
            with self.assertRaises(StorageError):
                TaskStore(self.path).save([Task(1, "a", "open")], 2)
        self.assertEqual(self.read_bytes(), content)
        self.assertEqual([p.name for p in self.dir.iterdir()], ["tasks.json"])


class TestOperations(TempDirTestCase):
    """FR-001, FR-003, FR-004, FR-006..FR-012, NFR-005: app operations."""

    def setUp(self) -> None:
        super().setUp()
        from todo.app import TaskStore

        self.store = TaskStore(self.path)

    def test_first_id_is_1_and_open(self) -> None:
        """FR-001, FR-003."""
        from todo import app

        task = app.add_task(self.store, "  buy milk ")
        self.assertEqual(
            (task.id, task.title, task.status), (1, "buy milk", "open")
        )

    def test_id_not_reused_after_delete(self) -> None:
        """FR-003: 1,2,3 then delete 3 then add gives 4."""
        from todo import app

        for title in ("a", "b", "c"):
            app.add_task(self.store, title)
        app.delete_task(self.store, "3")
        self.assertEqual(app.add_task(self.store, "d").id, 4)

    def test_id_not_reused_after_delete_highest_and_restart(self) -> None:
        """FR-003, FR-012: a new TaskStore instance still never reuses ids."""
        from todo import app
        from todo.app import TaskStore

        app.add_task(self.store, "a")
        app.delete_task(self.store, "1")
        self.assertEqual(app.add_task(TaskStore(self.path), "b").id, 2)

    def test_duplicate_titles_get_unique_ids(self) -> None:
        """FR-001."""
        from todo import app

        first = app.add_task(self.store, "same")
        second = app.add_task(self.store, "same")
        self.assertNotEqual(first.id, second.id)

    def test_list_creation_order(self) -> None:
        """FR-004."""
        from todo import app

        for title in ("x", "y", "z"):
            app.add_task(self.store, title)
        titles = [t.title for t in app.list_tasks(self.store)]
        self.assertEqual(titles, ["x", "y", "z"])

    def test_list_does_not_write(self) -> None:
        """NFR-005."""
        from todo import app

        app.list_tasks(self.store)
        self.assertFalse(self.path.exists())

    def test_complete_reopen_persist(self) -> None:
        """FR-006, FR-008, FR-012."""
        from todo import app
        from todo.app import TaskStore

        app.add_task(self.store, "a")
        self.assertTrue(app.complete_task(self.store, "1"))
        self.assertEqual(TaskStore(self.path).load()[0][0].status, "done")
        self.assertTrue(app.reopen_task(self.store, "1"))
        self.assertEqual(TaskStore(self.path).load()[0][0].status, "open")

    def test_already_done_and_open_return_false_bytes_unchanged(self) -> None:
        """FR-007, FR-009, NFR-005."""
        from todo import app

        app.add_task(self.store, "a")
        before = self.read_bytes()
        self.assertFalse(app.reopen_task(self.store, "1"))
        self.assertEqual(self.read_bytes(), before)
        app.complete_task(self.store, "1")
        before = self.read_bytes()
        self.assertFalse(app.complete_task(self.store, "1"))
        self.assertEqual(self.read_bytes(), before)

    def test_delete_removes_task(self) -> None:
        """FR-010."""
        from todo import app

        app.add_task(self.store, "a")
        app.add_task(self.store, "b")
        app.delete_task(self.store, "1")
        self.assertEqual([t.id for t in app.list_tasks(self.store)], [2])

    def test_unknown_id_raises_bytes_unchanged(self) -> None:
        """FR-011, NFR-005."""
        from todo import app
        from todo.app import TaskNotFoundError

        app.add_task(self.store, "a")
        before = self.read_bytes()
        for func in (app.complete_task, app.reopen_task, app.delete_task):
            for raw in ("99", "abc", "0", "-1"):
                with self.assertRaises(TaskNotFoundError):
                    func(self.store, raw)
        self.assertEqual(self.read_bytes(), before)

    def test_invalid_title_creates_no_file(self) -> None:
        """FR-002, NFR-005."""
        from todo import app
        from todo.app import ValidationError

        for raw in ("", "  ", "a\nb"):
            with self.assertRaises(ValidationError):
                app.add_task(self.store, raw)
        self.assertFalse(self.path.exists())

    def test_invalid_title_checked_before_load(self) -> None:
        """FR-002 (D9): a bad title is rejected even if the file is corrupt."""
        from todo import app
        from todo.app import ValidationError

        self.path.write_bytes(b"{bad")
        with self.assertRaises(ValidationError):
            app.add_task(self.store, " ")


class TestFR014Usage(TempDirTestCase):
    """FR-014, NFR-003, NFR-004: usage errors exit 2 and change nothing."""

    BAD_ARGS = [
        [],
        ["frobnicate"],
        ["add"],
        ["add", "a", "b"],
        ["complete"],
        ["reopen"],
        ["delete"],
        ["complete", "1", "2"],
        ["reopen", "1", "2"],
        ["delete", "1", "2"],
        ["list", "extra"],
    ]

    def test_usage_errors_exit_2_stderr_only(self) -> None:
        for argv in self.BAD_ARGS:
            code, out, err = run_main(argv)
            self.assertEqual(code, 2, argv)
            self.assertEqual(out, "", argv)
            self.assertIn("Usage:", err, argv)
            self.assertIn("add <title>", err)
            self.assertIn("Quote", err)

    def test_usage_errors_change_no_data(self) -> None:
        for argv in self.BAD_ARGS:
            run_main(argv)
        self.assertFalse(self.path.exists())
        run_main(["add", "a"])
        before = self.read_bytes()
        for argv in self.BAD_ARGS:
            run_main(argv)
        self.assertEqual(self.read_bytes(), before)

    def test_usage_text_lists_commands_and_example(self) -> None:
        from todo import cli

        text = cli.build_usage()
        for word in ("add", "list", "complete", "reopen", "delete", "Example"):
            self.assertIn(word, text)

    def test_title_starting_with_dash_accepted(self) -> None:
        code, out, _ = run_main(["add", "-x fix"])
        self.assertEqual((code, out), (0, "Added: 1 [open] -x fix\n"))


class TestA5Help(TempDirTestCase):
    """FR-014, NFR-003 (A-5): -h and --help print usage and exit 0."""

    def test_help_flags(self) -> None:
        for flag in ("-h", "--help"):
            code, out, err = run_main([flag])
            self.assertEqual(code, 0)
            self.assertIn("Usage:", out)
            self.assertEqual(err, "")
        self.assertFalse(self.path.exists())


class TestCliCommands(TempDirTestCase):
    """FR-001, FR-004..FR-010, NFR-003: exact output and exit codes."""

    def test_add_prints_added_line(self) -> None:
        """FR-001."""
        self.assertEqual(
            run_main(["add", " buy milk "]),
            (0, "Added: 1 [open] buy milk\n", ""),
        )

    def test_list_format_and_order(self) -> None:
        """FR-004."""
        run_main(["add", "a"])
        run_main(["add", "b"])
        run_main(["complete", "1"])
        self.assertEqual(
            run_main(["list"]), (0, "1 [done] a\n2 [open] b\n", "")
        )

    def test_empty_list_message(self) -> None:
        """FR-005."""
        self.assertEqual(run_main(["list"]), (0, "No tasks.\n", ""))
        self.assertFalse(self.path.exists())

    def test_complete_silent(self) -> None:
        """FR-006."""
        run_main(["add", "a"])
        self.assertEqual(run_main(["complete", "1"]), (0, "", ""))

    def test_complete_already_done(self) -> None:
        """FR-007."""
        run_main(["add", "a"])
        run_main(["complete", "1"])
        before = self.read_bytes()
        self.assertEqual(
            run_main(["complete", "1"]),
            (0, "Task 1 is already done.\n", ""),
        )
        self.assertEqual(self.read_bytes(), before)

    def test_reopen_silent(self) -> None:
        """FR-008."""
        run_main(["add", "a"])
        run_main(["complete", "1"])
        self.assertEqual(run_main(["reopen", "1"]), (0, "", ""))
        self.assertIn("1 [open] a", run_main(["list"])[1])

    def test_reopen_already_open(self) -> None:
        """FR-009."""
        run_main(["add", "a"])
        before = self.read_bytes()
        self.assertEqual(
            run_main(["reopen", "1"]),
            (0, "Task 1 is already open.\n", ""),
        )
        self.assertEqual(self.read_bytes(), before)

    def test_delete_silent_and_removed(self) -> None:
        """FR-010."""
        run_main(["add", "a"])
        self.assertEqual(run_main(["delete", "1"]), (0, "", ""))
        self.assertEqual(run_main(["list"])[1], "No tasks.\n")

    def test_persistence_across_runs(self) -> None:
        """FR-012, FR-003: ids never reused across separate main calls."""
        run_main(["add", "a"])
        run_main(["delete", "1"])
        self.assertEqual(run_main(["add", "b"])[1], "Added: 2 [open] b\n")

    def test_file_is_utf8_json_in_cwd(self) -> None:
        """FR-012, NFR-006."""
        run_main(["add", "café"])
        self.assertIn("café", self.read_bytes().decode("utf-8"))


class TestCliErrors(TempDirTestCase):
    """FR-002, FR-011, FR-013, NFR-003, NFR-004, NFR-005: error mapping."""

    def assert_error(self, argv: list[str]) -> str:
        code, out, err = run_main(argv)
        self.assertEqual(code, 1, argv)
        self.assertEqual(out, "", argv)
        self.assertTrue(err.startswith("Error: "), err)
        self.assertNotIn("Traceback", err)
        return err

    def test_bad_titles_exit_1_no_file(self) -> None:
        """FR-002, R-1: empty, whitespace and control-character titles."""
        for title in ("", "   ", "a\nb", "a\tb", "a\x1b[0mb", "a\x00b"):
            self.assert_error(["add", title])
            self.assertFalse(self.path.exists(), repr(title))

    def test_control_char_rejection_keeps_existing_file(self) -> None:
        """FR-002 (R-1), NFR-005."""
        run_main(["add", "a"])
        before = self.read_bytes()
        self.assert_error(["add", "x\ny"])
        self.assertEqual(self.read_bytes(), before)

    def test_bad_ids_same_not_found_error(self) -> None:
        """FR-011, NFR-005."""
        run_main(["add", "a"])
        before = self.read_bytes()
        for command in ("complete", "reopen", "delete"):
            for raw in ("99", "abc", "0", "-1", ""):
                err = self.assert_error([command, raw])
                self.assertIn("task not found", err)
        self.assertEqual(self.read_bytes(), before)

    def test_corrupt_file_exit_1_untouched(self) -> None:
        """FR-013, NFR-005."""
        content = b"{broken"
        self.path.write_bytes(content)
        for argv in (["list"], ["add", "a"], ["complete", "1"],
                     ["reopen", "1"], ["delete", "1"]):
            self.assert_error(argv)
        self.assertEqual(self.read_bytes(), content)

    def test_bom_file_exit_1_untouched(self) -> None:
        """FR-013 (A-6)."""
        content = b"\xef\xbb\xbf" + valid_json()
        self.path.write_bytes(content)
        self.assert_error(["list"])
        self.assertEqual(self.read_bytes(), content)

    def test_unreadable_file_exit_1(self) -> None:
        """FR-013: tasks.json is a directory."""
        self.path.mkdir()
        self.assert_error(["list"])

    def test_surrogate_title_exit_1_no_traceback(self) -> None:
        """NFR-004, NFR-003 (A-1)."""
        err = self.assert_error(["add", "bad\ud800"])
        self.assertIn("UTF-8", err)
        self.assertFalse(self.path.exists())

    def test_unencodable_stdout_exit_1_plain_stderr(self) -> None:
        """NFR-004, NFR-003 (A-1): stdout that cannot encode the title."""
        from todo import cli

        ascii_out = io.TextIOWrapper(io.BytesIO(), encoding="ascii")
        err = io.StringIO()
        with contextlib.redirect_stdout(ascii_out):
            with contextlib.redirect_stderr(err):
                code = cli.main(["add", "café"])
        self.assertEqual(code, 1)
        self.assertTrue(err.getvalue().startswith("Error: "))
        self.assertNotIn("Traceback", err.getvalue())

    def test_errors_are_plain_language_on_stderr_only(self) -> None:
        """NFR-004."""
        err = self.assert_error(["add", " "])
        self.assertIn("title must not be empty", err)


class TestNFR006Unicode(TempDirTestCase):
    """NFR-006: Unicode survives storage and display."""

    def test_unicode_roundtrip_through_file_and_output(self) -> None:
        title = "café ☕ 日本語"
        self.assertEqual(
            run_main(["add", title])[1], f"Added: 1 [open] {title}\n"
        )
        self.assertEqual(run_main(["list"])[1], f"1 [open] {title}\n")
        self.assertNotIn(b"\\u", self.read_bytes())


class TestA4NoGlobalSideEffects(TempDirTestCase):
    """NFR-006, NFR-009, FR-014 (A-4): main does not touch the streams."""

    def test_main_works_with_plain_stringio_streams(self) -> None:
        from todo import cli

        out, err = io.StringIO(), io.StringIO()
        old = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out, err
        try:
            code = cli.main(["list"])
        finally:
            sys.stdout, sys.stderr = old
        self.assertEqual((code, out.getvalue()), (0, "No tasks.\n"))

    def test_main_does_not_alter_stream_encoding(self) -> None:
        from todo import cli

        out = io.TextIOWrapper(io.BytesIO(), encoding="ascii")
        err = io.TextIOWrapper(io.BytesIO(), encoding="latin-1")
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            cli.main(["list"])
            cli.main([])
        self.assertEqual(out.encoding, "ascii")
        self.assertEqual(err.encoding, "latin-1")

    def test_python_dash_m_runs_in_empty_dir(self) -> None:
        """FR-005, NFR-006: manual check from the plan, automated."""
        import subprocess

        repo = Path(__file__).resolve().parent.parent
        env = dict(os.environ, PYTHONPATH=str(repo))
        result = subprocess.run(
            [sys.executable, "-m", "todo.cli", "list"],
            cwd=self.dir, env=env, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "No tasks.")


SOURCE_FILES = [
    Path(__file__).resolve().parent.parent / "todo" / name
    for name in ("__init__.py", "app.py", "cli.py")
]


def imported_modules(path: Path) -> set[str]:
    """Return top-level module names imported by a source file."""
    import ast

    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                names.add(node.module.split(".")[0])
    return names


class TestNFRQuality(unittest.TestCase):
    """NFR-001, NFR-002, NFR-007, NFR-008, NFR-009: static checks."""

    def test_python_version_at_least_3_11(self) -> None:
        """NFR-001."""
        self.assertGreaterEqual(sys.version_info[:2], (3, 11))

    def test_only_stdlib_imports(self) -> None:
        """NFR-002."""
        here = Path(__file__).resolve()
        for path in [*SOURCE_FILES, here]:
            for name in imported_modules(path):
                self.assertTrue(
                    name in sys.stdlib_module_names or name == "todo",
                    f"{path.name} imports {name}",
                )

    def test_no_network_modules_imported(self) -> None:
        """NFR-007."""
        banned = {
            "socket", "urllib", "http", "ssl", "requests", "ftplib", "smtplib",
        }
        for path in SOURCE_FILES:
            self.assertFalse(imported_modules(path) & banned, path.name)

    def test_no_bare_except(self) -> None:
        """NFR-008."""
        import ast

        for path in [*SOURCE_FILES, Path(__file__).resolve()]:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    self.assertIsNotNone(
                        node.type, f"bare except in {path.name}"
                    )

    def test_functions_have_type_hints(self) -> None:
        """NFR-008."""
        import ast

        for path in [*SOURCE_FILES, Path(__file__).resolve()]:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    where = f"{path.name}:{node.name}"
                    self.assertIsNotNone(node.returns, where)
                    args = node.args
                    every = [*args.posonlyargs, *args.args, *args.kwonlyargs]
                    for arg in every:
                        if arg.arg in ("self", "cls"):
                            continue
                        self.assertIsNotNone(
                            arg.annotation, f"{where}:{arg.arg}"
                        )


if __name__ == "__main__":
    unittest.main()
