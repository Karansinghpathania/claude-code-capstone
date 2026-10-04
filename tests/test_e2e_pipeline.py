"""End-to-end pipeline simulation. Everything runs in a TEMP COPY of the repo.

The real sdlc/state.json, audit log and artifacts/ are never written; the last
test proves it. Orchestrator functions are called with confirmed=True (the
human step) and the hook is run as a subprocess.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import orchestrator as orc  # noqa: E402

IDS = ["requirements", "architecture", "design-review", "planning",
       "implementation", "review", "verify", "pr"]
COVERS = "Covers FR-001, FR-002 and NFR-001."
REQ = ("# Requirements\n- FR-001: create a task\n- FR-002: list tasks\n"
       "- NFR-001: standard library only\n## Open Questions\n"
       "- [x] Q: duplicates? A: allowed (source: human)\n")
EXTRA = {"design-review": "Verdict: APPROVE\n",
         "verify": "```\nOK\n```\nResult: PASS\n"}


def content(phase: str, file: str) -> str:
    """Dummy but traceability-valid text for one owned file."""
    if file.endswith(".py"):
        return '"""Stub."""\n'
    if phase == "requirements":
        return REQ
    return f"# {phase}\n{COVERS}\n{EXTRA.get(phase, '')}"


def copy_repo(dst: Path) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for name in ("hooks", "docs", ".claude"):
        shutil.copytree(REPO / name, dst / name, ignore=ignore)
    shutil.copy2(REPO / "orchestrator.py", dst / "orchestrator.py")
    (dst / "sdlc").mkdir()
    shutil.copy2(REPO / "sdlc" / "phases.json", dst / "sdlc" / "phases.json")
    (dst / "artifacts").mkdir()


def snapshot() -> dict[str, object]:
    """Fingerprint of the real repo's runtime state and generated outputs."""
    def digest(rel: str) -> str | None:
        p = REPO / rel
        return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    return {"state": digest("sdlc/state.json"),
            "audit": digest("sdlc/audit.log.jsonl"),
            "artifacts": sorted(p.name for p in (REPO / "artifacts").iterdir()),
            "todo": (REPO / "todo").exists(),
            "changelog": (REPO / "CHANGELOG.md").exists()}


BEFORE = snapshot()  # taken at import, before any test in this module runs


class PipelineCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.assertNotEqual(self.root, REPO)
        copy_repo(self.root)
        self.manifest = orc.load_manifest(self.root)
        orc.init_state(self.root)

    # -- helpers ---------------------------------------------------------
    def write(self, phase: str) -> None:
        for f in orc._get(self.manifest, phase)["owns"]:
            path = self.root / f
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content(phase, f), encoding="utf-8")

    def status(self, phase: str) -> str:
        state = orc.load_state(self.root, self.manifest)
        return state["phases"][phase]["status"]

    def statuses(self) -> list[str]:
        return [self.status(i) for i in IDS]

    def advance(self, *phases: str) -> None:
        for phase in phases:
            self.write(phase)
            orc.submit(self.root, phase)
            orc.approve(self.root, phase, "tester", confirmed=True)

    def audit(self) -> list[dict]:
        text = (self.root / "sdlc" / "audit.log.jsonl").read_text("utf-8")
        return [json.loads(line) for line in text.splitlines()]

    def refused(self, fragment: str, fn, *args, **kwargs) -> None:
        with self.assertRaises(orc.RuleViolation) as cm:
            fn(*args, **kwargs)
        self.assertIn(fragment, str(cm.exception))
        self.assertEqual(self.audit()[-1]["result"], "refused")

    def guard(self, tool: str, **tool_input: str) -> subprocess.CompletedProcess:
        payload = json.dumps({"tool_name": tool, "tool_input": tool_input})
        return subprocess.run(
            [sys.executable, str(self.root / "hooks" / "guard.py")],
            input=payload, capture_output=True, text=True, encoding="utf-8",
            timeout=30, cwd=self.root)

    def run_cmd(self, command: str) -> subprocess.CompletedProcess:
        return self.guard("Bash", command=command)

    def write_file(self, rel: str) -> subprocess.CompletedProcess:
        return self.guard("Write", file_path=str(self.root / rel),
                          content="x")

    def assertDenied(self, result: subprocess.CompletedProcess,
                     rule: str) -> None:
        # Claude Code: exit code 2 blocks; stderr is shown to the model.
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn(f"[{rule}]", result.stderr)
        self.assertEqual(result.stdout, "")

    def assertAllowed(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")


class FullRunTests(PipelineCase):
    def test_1_complete_run_all_phases(self) -> None:
        for n, phase in enumerate(IDS):
            self.assertEqual(self.status(phase), "ACTIVE", phase)
            self.assertTrue(all(s == "LOCKED" for s in self.statuses()[n + 1:]))
            self.advance(phase)
        self.assertEqual(self.statuses(), ["APPROVED"] * 8)
        pairs = [(e["action"], e["phase"], e["result"]) for e in self.audit()]
        want = [(a, p, "ok") for p in IDS for a in ("submit", "approve")]
        self.assertEqual(pairs, want)
        self.assertEqual(orc.check(self.root), "all checks passed")
        done = subprocess.run(
            [sys.executable, str(self.root / "orchestrator.py"), "status",
             "--json"], capture_output=True, text=True, cwd=self.root)
        data = json.loads(done.stdout)
        self.assertEqual((done.returncode, data["approvalStatus"],
                          data["currentPhase"]), (0, "COMPLETE", None))


class TransitionTests(PipelineCase):
    def test_2_submit_architecture_while_requirements_active(self) -> None:
        self.write("architecture")
        self.refused("needs ACTIVE but 'architecture' is LOCKED",
                     orc.submit, self.root, "architecture")
        self.assertEqual(self.status("requirements"), "ACTIVE")

    def test_3_skipping_phases_is_blocked(self) -> None:
        self.refused("needs AWAITING_APPROVAL but 'architecture' is LOCKED",
                     orc.approve, self.root, "architecture", "t", True)
        self.advance("requirements")
        self.write("planning")
        self.refused("needs ACTIVE but 'planning' is LOCKED",
                     orc.submit, self.root, "planning")
        self.refused("needs AWAITING_APPROVAL but 'design-review' is LOCKED",
                     orc.approve, self.root, "design-review", "t", True)
        self.assertEqual(self.statuses(), ["APPROVED", "ACTIVE"]
                         + ["LOCKED"] * 6)

    def test_5_reject_loop(self) -> None:
        self.write("requirements")
        orc.submit(self.root, "requirements")
        orc.reject(self.root, "requirements", "answer open questions", True)
        entry = orc.load_state(self.root, self.manifest)["phases"]["requirements"]
        self.assertEqual((entry["status"], entry["hashes"]),
                         ("ACTIVE", {}))
        self.assertEqual(entry["rejectionReason"], "answer open questions")
        self.assertEqual(self.status("architecture"), "LOCKED")
        orc.submit(self.root, "requirements")
        orc.approve(self.root, "requirements", "tester", confirmed=True)
        self.assertEqual(self.status("architecture"), "ACTIVE")
        actions = [(e["action"], e["result"]) for e in self.audit()]
        self.assertEqual(actions, [("submit", "ok"), ("reject", "ok"),
                                   ("submit", "ok"), ("approve", "ok")])

    def test_6_reopen_needs_later_files_gone(self) -> None:
        self.advance("requirements", "architecture")
        self.write("design-review")
        orc.submit(self.root, "design-review")
        self.refused("later phases still have files on disk",
                     orc.reopen, self.root, "architecture", "rework", True)
        (self.root / "artifacts" / "design-review.md").unlink()
        orc.reopen(self.root, "architecture", "rework", confirmed=True)
        self.assertEqual(self.statuses(), ["APPROVED", "ACTIVE"]
                         + ["LOCKED"] * 6)


class TamperTests(PipelineCase):
    def test_4_modified_approved_artifact_fails_check(self) -> None:
        self.advance("requirements")
        self.assertEqual(orc.check(self.root), "all checks passed")
        path = self.root / "artifacts" / "requirements.md"
        path.write_text(path.read_text("utf-8") + "- FR-003: sneaked in\n",
                        encoding="utf-8")
        self.refused("APPROVED phase 'requirements' file changed",
                     orc.check, self.root)

    def test_4b_edit_between_submit_and_approve_is_refused(self) -> None:
        self.write("requirements")
        orc.submit(self.root, "requirements")
        (self.root / "artifacts" / "requirements.md").write_text("changed\n")
        self.refused("tamper detection", orc.approve, self.root,
                     "requirements", "t", True)
        self.assertEqual(self.status("requirements"), "AWAITING_APPROVAL")

    def test_8_future_phase_artifact_fails_check(self) -> None:
        self.assertEqual(orc.check(self.root), "all checks passed")
        (self.root / "artifacts" / "architecture.md").write_text(COVERS)
        self.refused("LOCKED phase 'architecture' owns existing file",
                     orc.check, self.root)


class GuardInContextTests(PipelineCase):
    def test_7_guard_with_requirements_active(self) -> None:
        self.assertAllowed(self.write_file("artifacts/requirements.md"))
        self.assertDenied(self.write_file("artifacts/architecture.md"), "R08")
        self.assertDenied(self.write_file("sdlc/state.json"), "R07")
        self.assertDenied(self.run_cmd(
            "python orchestrator.py approve requirements --by x"), "R06")
        self.assertDenied(self.run_cmd("git push --force origin main"), "R04")
        self.assertAllowed(self.run_cmd("python orchestrator.py status"))

    def test_7b_guard_follows_state_changes(self) -> None:
        self.write("requirements")
        orc.submit(self.root, "requirements")
        self.assertDenied(self.write_file("artifacts/requirements.md"), "R08")
        orc.approve(self.root, "requirements", "tester", confirmed=True)
        self.assertDenied(self.write_file("artifacts/requirements.md"), "R08")
        self.assertAllowed(self.write_file("artifacts/architecture.md"))


class ZzRealRepoTests(unittest.TestCase):  # name sorts last in this module
    def test_real_repo_untouched(self) -> None:
        self.assertEqual(snapshot(), BEFORE)


if __name__ == "__main__":
    unittest.main()
