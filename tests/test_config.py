"""Consistency tests for the agents, prompts, skills and hook wiring."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PHASES = json.loads((REPO / "sdlc" / "phases.json").read_text("utf-8"))
IDS = [p["id"] for p in PHASES["phases"]]
SKILLS = ["requirements", "verify", "pr"]
APPROVAL = "Awaiting human approval. Run: python orchestrator.py approve"


def split(path: Path) -> tuple[dict[str, str], str]:
    """Return (frontmatter key/value pairs, body). Frontmatter is the text
    between the first two '---' lines; only 'key: value' lines are read."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"{path.name}: must start with '---'")
    end = next((i for i, ln in enumerate(lines[1:], 1)
                if ln.strip() == "---"), None)
    if end is None:
        raise AssertionError(f"{path.name}: frontmatter is not closed")
    meta = {}
    for ln in lines[1:end]:
        m = re.match(r"^([A-Za-z][\w-]*):[ \t]*(.*)$", ln)
        if m:
            meta[m.group(1)] = m.group(2).strip()
    return meta, "\n".join(lines[end + 1:])


def agent(i: str) -> Path:
    return REPO / ".claude" / "agents" / f"{i}.md"


def prompt(i: str) -> Path:
    return REPO / ".claude" / "commands" / f"{i}.md"


def skill(i: str) -> Path:
    return REPO / ".claude" / "skills" / i / "SKILL.md"


def allowed_files(text: str) -> list[str]:
    sec = re.search(r"^## Allowed files\n(.*?)(?=^## )", text, re.M | re.S)
    if sec is None:
        raise AssertionError("no '## Allowed files' section")
    return re.findall(r"`([\w./-]+\.(?:md|py))`", sec.group(1))


class FileTests(unittest.TestCase):
    def test_all_files_exist(self) -> None:
        self.assertEqual(len(IDS), 8)
        # Phase 1 (requirements) is a slash command, not an agent
        for i in IDS:
            if i != "requirements":
                with self.subTest(agent=i):
                    self.assertTrue(agent(i).is_file())
            with self.subTest(command=i):
                self.assertTrue(prompt(i).is_file())
        for s in SKILLS:
            with self.subTest(skill=s):
                self.assertTrue(skill(s).is_file())

    def test_manifest_files_exist(self) -> None:
        for ph in PHASES["phases"]:
            for key in ("agent", "prompt"):
                with self.subTest(phase=ph["id"], key=key):
                    self.assertTrue((REPO / ph[key]).is_file(), ph[key])


class FrontmatterTests(unittest.TestCase):
    def test_agents(self) -> None:
        # Phase 1 (requirements) is a command, not an agent
        for i in IDS:
            if i == "requirements":
                continue
            with self.subTest(agent=i):
                meta, body = split(agent(i))
                self.assertEqual(meta.get("name"), i)
                self.assertTrue(meta.get("description"))
                self.assertTrue(body.strip())

    def test_prompts(self) -> None:
        for i in IDS:
            with self.subTest(prompt=i):
                meta, _ = split(prompt(i))
                self.assertTrue(meta.get("description"))
                self.assertEqual(meta.get("name"), i)

    def test_contract_table_matches_manifest(self) -> None:
        text = (REPO / "docs" / "CONTRACT.md").read_text("utf-8")
        rows = re.findall(
            r"^\| (\d) \| (\S+) \| (.+?) \| (.+?) \| (.+?) \|$", text, re.M)
        self.assertEqual(len(rows), len(IDS))
        for (n, i, a, c, owns), ph in zip(rows, PHASES["phases"]):
            with self.subTest(phase=ph["id"]):
                # Extract just the path from the agent/command cells (may have extra text)
                agent_path = re.search(r"\.claude/\S+\.md", a).group(0) if a.count(".claude") else a.strip()
                cmd_path = re.search(r"\.claude/\S+\.md", c).group(0) if c.count(".claude") else c.strip()
                self.assertEqual(int(n), ph["order"])
                self.assertEqual(i, ph["id"])
                self.assertEqual(agent_path, ph["agent"])
                self.assertEqual(cmd_path, ph["prompt"])

    def test_skills(self) -> None:
        for s in SKILLS:
            with self.subTest(skill=s):
                meta, _ = split(skill(s))
                self.assertTrue(meta.get("description"))
                # VS Code requires name == parent directory name
                self.assertEqual(meta.get("name"), s)
                self.assertLessEqual(len(meta["description"]), 1024)


class CommandTests(unittest.TestCase):
    def test_commands_have_description(self) -> None:
        for i in IDS:
            with self.subTest(command=i):
                meta, _ = split(prompt(i))
                self.assertTrue(meta.get("description"))
                self.assertEqual(meta.get("name"), i)

    def test_command_content(self) -> None:
        for i in IDS:
            with self.subTest(command=i):
                text = prompt(i).read_text("utf-8")
                # Requirements needs interactive questions; others need orchestrator commands
                if i == "requirements":
                    self.assertIn("clarifying question", text)
                else:
                    for needle in ("python orchestrator.py status",
                                   "python orchestrator.py submit"):
                        self.assertIn(needle, text)
                self.assertIn(f"approve {i} --by <your-name>", text)


class AgentTests(unittest.TestCase):
    def test_approval_sentence(self) -> None:
        # Phase 1 is a command, not an agent
        for i in IDS:
            if i == "requirements":
                continue
            with self.subTest(agent=i):
                text = agent(i).read_text("utf-8")
                self.assertIn(APPROVAL, text)
                self.assertIn(f"approve {i} --by <your-name>", text)

    def test_allowed_files_match_manifest(self) -> None:
        for ph in PHASES["phases"]:
            if ph["id"] == "requirements":
                continue
            with self.subTest(agent=ph["id"]):
                got = allowed_files(agent(ph["id"]).read_text("utf-8"))
                self.assertEqual(sorted(got), sorted(ph["owns"]))

    def test_bodies_are_distinct(self) -> None:
        # Phase 1 is a command, not an agent
        bodies = [split(agent(i))[1] for i in IDS if i != "requirements"]
        self.assertEqual(len(set(bodies)), len(bodies))

    def test_agents_forbid_protected_paths(self) -> None:
        # Phase 1 is a command, not an agent
        for i in IDS:
            if i == "requirements":
                continue
            with self.subTest(agent=i):
                text = agent(i).read_text("utf-8")
                for needle in ("sdlc/", "orchestrator.py", "hooks/**",
                               ".claude/", "reopen"):
                    self.assertIn(needle, text)

    def test_skill_references(self) -> None:
        for s in SKILLS:
            with self.subTest(skill=s):
                rel = f".claude/skills/{s}/SKILL.md"
                # Requirements is a slash command, not an agent, so skip the reference check
                if s != "requirements":
                    self.assertIn(rel, agent(s).read_text("utf-8"))
                self.assertTrue((REPO / rel).is_file())


class HookWiringTests(unittest.TestCase):
    def test_settings_json_points_to_guard(self) -> None:
        path = REPO / ".claude" / "settings.json"
        data = json.loads(path.read_text("utf-8"))
        # Claude Code layout: PreToolUse -> [{matcher, hooks: [{type,
        # command, timeout}]}]
        entries = data.get("hooks", {}).get("PreToolUse", [])
        self.assertTrue(entries)
        commands = []
        for entry in entries:
            self.assertTrue(entry.get("matcher"), "matcher is required")
            self.assertTrue(entry.get("hooks"))
            for hook in entry["hooks"]:
                self.assertEqual(hook.get("type"), "command")
                commands.append(hook.get("command", ""))
        self.assertTrue(all("hooks/guard.py" in c for c in commands))
        self.assertTrue((REPO / "hooks" / "guard.py").is_file())

    def test_guard_matcher_covers_write_and_shell_tools(self) -> None:
        path = REPO / ".claude" / "settings.json"
        data = json.loads(path.read_text("utf-8"))
        for entry in data["hooks"]["PreToolUse"]:
            tools = set(entry["matcher"].split("|"))
            for tool in ("Bash", "PowerShell", "Edit", "Write", "MultiEdit",
                         "NotebookEdit"):
                with self.subTest(tool=tool):
                    self.assertIn(tool, tools)


if __name__ == "__main__":
    unittest.main()
