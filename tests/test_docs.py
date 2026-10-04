"""Checks that README.md and docs/RUNBOOK.md only reference things that exist.

Scans inline `code` spans for repo paths (.py/.md/.json/.yml) and for
`python ...` commands, plus fenced code blocks for `python ...` commands, and
Markdown links. Generated outputs that do not exist before a live pipeline
run are skipped (see GENERATED).
"""
from __future__ import annotations

import contextlib
import fnmatch
import io
import json
import re
import shlex
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import orchestrator as orc  # noqa: E402

DOCS = ["README.md", "docs/RUNBOOK.md"]
GENERATED = ["artifacts/*.md", "todo/*", "tests/test_todo.py",
             "CHANGELOG.md", "sdlc/state.json", "sdlc/audit.log.jsonl"]
PHASES = json.loads((REPO / "sdlc" / "phases.json").read_text("utf-8"))
IDS = [p["id"] for p in PHASES["phases"]]
PATH_RE = re.compile(r"^[\w./-]+\.(?:py|md|json|yml)$")  # no * or <
CMD_RE = re.compile(r"(?:^\s*|[|;]\s*)(python3?\s[^|;]*)")
PLACEHOLDER = "PLACEHOLDER"


def generated(path: str) -> bool:
    return any(fnmatch.fnmatch(path, g) for g in GENERATED)


def read(doc: str) -> str:
    return (REPO / doc).read_text(encoding="utf-8")


def parts(text: str) -> tuple[list[str], list[str]]:
    """Return (inline code spans, fenced-block lines)."""
    spans: list[str] = []
    fenced: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif in_fence:
            fenced.append(line)
        else:
            spans += re.findall(r"`([^`\n]+)`", line)
    return spans, fenced


def paths_in(doc: str) -> list[str]:
    spans, _ = parts(read(doc))
    return [s for s in spans if PATH_RE.match(s)]


def commands_in(doc: str) -> list[str]:
    spans, fenced = parts(read(doc))
    found: list[str] = []
    for line in spans + fenced:
        found += [m.strip() for m in CMD_RE.findall(line)]
    return found


def tree_paths(doc: str) -> list[str]:
    """Paths drawn in the first box-drawing tree of the document."""
    stack: list[str] = []
    out: list[str] = []
    for line in read(doc).splitlines():
        m = re.match(r"^((?:│   |    )*)[├└]── (\S+)", line)
        if not m:
            continue
        depth = len(m.group(1)) // 4
        del stack[depth:]
        name = m.group(2)
        stack.append(name.rstrip("/"))
        out.append("/".join(stack))
    return out


class DocFilesTests(unittest.TestCase):
    def test_docs_exist_and_are_non_empty(self) -> None:
        for doc in DOCS:
            with self.subTest(doc=doc):
                self.assertTrue(read(doc).strip())

    def test_backticked_paths_exist(self) -> None:
        for doc in DOCS:
            paths = paths_in(doc)
            self.assertTrue(paths, f"{doc}: no backticked paths found")
            for p in paths:
                if generated(p):
                    continue
                with self.subTest(doc=doc, path=p):
                    self.assertTrue((REPO / p).is_file(), f"{p} not found")

    def test_markdown_links_resolve(self) -> None:
        for doc in DOCS:
            base = (REPO / doc).parent
            for target in re.findall(r"\]\(([^)\s]+)\)", read(doc)):
                if re.match(r"^(?:https?:|mailto:|#)", target):
                    continue
                target = target.split("#")[0]
                with self.subTest(doc=doc, link=target):
                    self.assertTrue((base / target).exists(),
                                    f"{doc} links to missing {target}")

    def test_readme_tree_paths_exist(self) -> None:
        paths = tree_paths("README.md")
        self.assertGreater(len(paths), 20)
        for p in paths:
            if generated(p):
                continue
            with self.subTest(path=p):
                self.assertTrue((REPO / p).exists(), f"{p} not found")


class DocCommandTests(unittest.TestCase):
    def _check(self, doc: str, cmd: str) -> None:
        tokens = shlex.split(re.sub(r"<[^<>]+>", PLACEHOLDER, cmd))
        self.assertTrue(tokens[0].startswith("python"))
        arg = tokens[1] if len(tokens) > 1 else ""
        if arg == "-m":
            self.assertIn(tokens[2], ("unittest", "compileall"), cmd)
            if "-s" in tokens:
                self.assertTrue((REPO / tokens[tokens.index("-s") + 1]).is_dir())
        elif arg == "--version":
            pass
        elif arg.endswith(".py"):
            self.assertTrue((REPO / arg).is_file(), f"{arg} not found")
            if arg == "orchestrator.py":
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    try:
                        ns = orc.build_parser().parse_args(tokens[2:])
                    except SystemExit:
                        self.fail(f"{doc}: bad orchestrator usage: {cmd}\n"
                                  + err.getvalue())
                phase = getattr(ns, "phase", PLACEHOLDER)
                if phase != PLACEHOLDER:
                    self.assertIn(phase, IDS, cmd)
        else:
            self.fail(f"{doc}: unrecognised python command: {cmd}")

    def test_commands_are_valid(self) -> None:
        for doc in DOCS:
            cmds = commands_in(doc)
            self.assertTrue(cmds, f"{doc}: no python commands found")
            for cmd in cmds:
                with self.subTest(doc=doc, cmd=cmd):
                    self._check(doc, cmd)

    def test_key_commands_are_documented(self) -> None:
        text = read("README.md") + read("docs/RUNBOOK.md")
        for needle in ("python orchestrator.py status",
                       "python orchestrator.py next",
                       "python orchestrator.py check",
                       "python orchestrator.py submit architecture",
                       "python hooks/guard.py",
                       "python -m unittest discover -s tests -v"):
            with self.subTest(command=needle):
                self.assertIn(needle, text)


class DocContentTests(unittest.TestCase):
    def test_phase_table_matches_manifest(self) -> None:
        text = read("README.md")
        for ph in PHASES["phases"]:
            rows = [ln for ln in text.splitlines()
                    if ln.startswith("|") and f"`{ph['id']}`" in ln]
            with self.subTest(phase=ph["id"]):
                self.assertEqual(len(rows), 1, f"expected one row for {ph['id']}")
                # Phase 1 is a slash command, phases 2-8 are subagents
                if ph["id"] != "requirements":
                    self.assertIn(f"`{ph['agent']}`", rows[0])
                for f in ph["owns"]:
                    self.assertIn(f"`{f}`", rows[0])

    def test_skill_column(self) -> None:
        rows = {ph["id"]: next(ln for ln in read("README.md").splitlines()
                               if ln.startswith("|") and f"`{ph['id']}`" in ln)
                for ph in PHASES["phases"]}
        for i, row in rows.items():
            skill = f".claude/skills/{i}/SKILL.md"
            with self.subTest(phase=i):
                if (REPO / skill).is_file():
                    self.assertIn(f"`{skill}`", row)
                else:
                    self.assertIn("| none |", row)

    def test_mermaid_diagrams_present(self) -> None:
        text = read("README.md")
        self.assertGreaterEqual(text.count("```mermaid"), 2)
        for i in IDS:
            self.assertIn(i, text)

    def test_runbook_has_required_sections(self) -> None:
        text = read("docs/RUNBOOK.md")
        for n in range(1, 15):
            with self.subTest(step=n):
                self.assertRegex(text, rf"(?m)^## Step {n}\. ")
        for heading in ("Troubleshooting", "Reset to clean state",
                        "Using your own story"):
            with self.subTest(heading=heading):
                self.assertIn(f"## {heading}", text)


if __name__ == "__main__":
    unittest.main()
