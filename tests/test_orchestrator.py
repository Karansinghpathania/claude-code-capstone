"""Tests for orchestrator.py. Uses temporary directories only."""
from __future__ import annotations

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
REQ = ("# Requirements\n- FR-001 create\n- FR-002 list\n- NFR-001 stdlib\n"
       "## Open Questions\nNone\n")
BODY = "Covers FR-001, FR-002, NFR-001.\nVerdict: APPROVE\n```\nok\n```\n"


class OrchestratorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "sdlc").mkdir()
        shutil.copy(REPO / "sdlc" / "phases.json",
                    self.root / "sdlc" / "phases.json")
        self.manifest = orc.load_manifest(self.root)
        for prot in self.manifest["protected"]:
            if prot.endswith("/"):
                (self.root / prot).mkdir(parents=True, exist_ok=True)
        (self.root / "orchestrator.py").write_text("# stub\n")
        orc.init_state(self.root)

    # helpers
    def owns(self, phase: str) -> list[str]:
        return orc._get(self.manifest, phase)["owns"]

    def write(self, phase: str, text: str | None = None) -> None:
        for f in self.owns(phase):
            path = self.root / f
            path.parent.mkdir(parents=True, exist_ok=True)
            if text is not None:
                body = text
            elif phase == "requirements":
                body = REQ
            else:
                body = "x = 1\n" if f.endswith(".py") else BODY
            path.write_text(body, encoding="utf-8")

    def status(self, phase: str) -> str:
        return orc.load_state(self.root, self.manifest)["phases"][phase][
            "status"]

    def advance(self, phase: str) -> None:
        self.write(phase)
        orc.submit(self.root, phase)
        orc.approve(self.root, phase, "tester", confirmed=True)

    def audit_lines(self) -> list[dict]:
        text = (self.root / "sdlc" / "audit.log.jsonl").read_text()
        return [json.loads(line) for line in text.splitlines()]


class StateTests(OrchestratorTestCase):
    def test_init_state(self) -> None:
        state = orc.load_state(self.root, self.manifest)
        self.assertEqual(self.status("requirements"), "ACTIVE")
        for phase in IDS[1:]:
            self.assertEqual(state["phases"][phase]["status"], "LOCKED")

    def test_derived_fields(self) -> None:
        state = orc.load_state(self.root, self.manifest)
        d = orc.derive(self.manifest, state)
        self.assertEqual(d["currentPhase"], "requirements")
        self.assertIsNone(d["previousPhase"])
        self.assertEqual(d["nextPhase"], "architecture")
        self.assertEqual(d["allowedFiles"], ["artifacts/requirements.md"])
        self.write("requirements")
        orc.submit(self.root, "requirements")
        d = orc.derive(self.manifest, orc.load_state(self.root,
                                                     self.manifest))
        self.assertEqual(d["allowedFiles"], [])
        self.assertEqual(d["approvalStatus"], "PENDING_HUMAN_APPROVAL")

    def test_corrupt_state(self) -> None:
        path = self.root / "sdlc" / "state.json"
        good = json.loads(path.read_text())

        def variant(mutate) -> str:
            data = json.loads(json.dumps(good))
            mutate(data["phases"])
            return json.dumps(data)

        cases = {
            "not json": "{nope",
            "no phases": "{}",
            "unknown phase": variant(lambda p: p.update(bogus=p["pr"])),
            "bad status": variant(
                lambda p: p["pr"].update(status="DONE")),
            "two active": variant(
                lambda p: p["architecture"].update(status="ACTIVE")),
            "approved after locked": variant(
                lambda p: p["pr"].update(status="APPROVED")),
        }
        for name, text in cases.items():
            with self.subTest(name):
                path.write_text(text)
                with self.assertRaises(orc.RuleViolation):
                    orc.load_state(self.root, self.manifest)

    def test_corrupt_state_cli_exit_1(self) -> None:
        (self.root / "sdlc" / "state.json").write_text("{nope")
        self.assertEqual(orc.main(["status"], root=self.root), 1)


class FlowTests(OrchestratorTestCase):
    def test_happy_path_all_phases(self) -> None:
        for phase in IDS:
            self.assertEqual(self.status(phase), "ACTIVE")
            self.write(phase)
            orc.submit(self.root, phase)
            self.assertEqual(self.status(phase), "AWAITING_APPROVAL")
            orc.approve(self.root, phase, "tester", confirmed=True)
            self.assertEqual(self.status(phase), "APPROVED")
        state = orc.load_state(self.root, self.manifest)
        self.assertEqual(state["phases"]["pr"]["approvedBy"], "tester")
        self.assertIn("Pipeline complete", orc.next_step(self.root,
                                                         self.manifest))
        self.assertEqual(orc.check(self.root), "all checks passed")
        self.assertTrue(all(e["result"] == "ok" for e in self.audit_lines()))

    def test_submit_locked_refused(self) -> None:
        self.write("architecture")
        with self.assertRaises(orc.RuleViolation):
            orc.submit(self.root, "architecture")
        self.assertEqual(self.status("architecture"), "LOCKED")

    def test_approve_without_submit_refused(self) -> None:
        with self.assertRaises(orc.RuleViolation):
            orc.approve(self.root, "requirements", "t", confirmed=True)

    def test_approve_twice_refused(self) -> None:
        self.advance("requirements")
        with self.assertRaises(orc.RuleViolation):
            orc.approve(self.root, "requirements", "t", confirmed=True)

    def test_approve_next_phase_before_current_refused(self) -> None:
        self.write("requirements")
        orc.submit(self.root, "requirements")
        with self.assertRaises(orc.RuleViolation):
            orc.approve(self.root, "architecture", "t", confirmed=True)

    def test_approve_requires_confirmation(self) -> None:
        self.write("requirements")
        orc.submit(self.root, "requirements")
        with self.assertRaises(orc.RuleViolation):
            orc.approve(self.root, "requirements", "t", confirmed=False)
        self.assertEqual(self.status("requirements"), "AWAITING_APPROVAL")

    def test_approve_after_tamper_refused(self) -> None:
        self.write("requirements")
        orc.submit(self.root, "requirements")
        path = self.root / "artifacts" / "requirements.md"
        path.write_text(path.read_text() + "\n- FR-003 sneaky\n")
        with self.assertRaises(orc.RuleViolation) as ctx:
            orc.approve(self.root, "requirements", "t", confirmed=True)
        self.assertIn("tamper", str(ctx.exception))
        self.assertEqual(self.status("requirements"), "AWAITING_APPROVAL")

    def test_reject_then_resubmit(self) -> None:
        self.write("requirements")
        orc.submit(self.root, "requirements")
        orc.reject(self.root, "requirements", "needs work", confirmed=True)
        entry = orc.load_state(self.root, self.manifest)["phases"][
            "requirements"]
        self.assertEqual(entry["status"], "ACTIVE")
        self.assertEqual(entry["hashes"], {})
        self.assertEqual(entry["rejectionReason"], "needs work")
        self.assertEqual(self.status("architecture"), "LOCKED")
        orc.submit(self.root, "requirements")
        self.assertEqual(self.status("requirements"), "AWAITING_APPROVAL")

    def test_reject_needs_reason_and_submission(self) -> None:
        with self.assertRaises(orc.UsageError):
            orc.reject(self.root, "requirements", " ", confirmed=True)
        with self.assertRaises(orc.RuleViolation):
            orc.reject(self.root, "requirements", "why", confirmed=True)

    def test_unknown_phase_is_usage_error(self) -> None:
        with self.assertRaises(orc.UsageError):
            orc.submit(self.root, "nonsense")
        self.assertEqual(orc.main(["submit", "nonsense"], root=self.root), 2)

    def test_refusals_are_audited(self) -> None:
        with self.assertRaises(orc.RuleViolation):
            orc.submit(self.root, "architecture")
        last = self.audit_lines()[-1]
        self.assertEqual((last["action"], last["result"]),
                         ("submit", "refused"))


class SubmitChecksTests(OrchestratorTestCase):
    def test_missing_file_refused(self) -> None:
        with self.assertRaises(orc.RuleViolation):
            orc.submit(self.root, "requirements")

    def test_empty_file_refused(self) -> None:
        self.write("requirements", "   \n")
        with self.assertRaises(orc.RuleViolation):
            orc.submit(self.root, "requirements")

    def test_unchecked_open_question_refused(self) -> None:
        self.write("requirements", REQ.replace(
            "None", "- [ ] Empty titles allowed?"))
        with self.assertRaises(orc.RuleViolation):
            orc.submit(self.root, "requirements")

    def test_checked_open_question_allowed(self) -> None:
        self.write("requirements", REQ.replace(
            "None", "- [x] Empty titles rejected (human, 2026-10-03)"))
        orc.submit(self.root, "requirements")

    def test_missing_open_questions_heading_refused(self) -> None:
        self.write("requirements", "# R\nFR-001 only\n")
        with self.assertRaises(orc.RuleViolation):
            orc.submit(self.root, "requirements")

    def test_unknown_id_refused(self) -> None:
        self.advance("requirements")
        self.write("architecture", "Covers FR-001 and FR-999.\n")
        with self.assertRaises(orc.RuleViolation) as ctx:
            orc.submit(self.root, "architecture")
        self.assertIn("FR-999", str(ctx.exception))

    def test_design_review_needs_verdict(self) -> None:
        self.advance("requirements")
        self.advance("architecture")
        self.write("design-review", "Covers FR-001.\n")
        with self.assertRaises(orc.RuleViolation):
            orc.submit(self.root, "design-review")

    def test_verify_missing_id_refused(self) -> None:
        for phase in IDS[:6]:
            self.advance(phase)
        self.write("verify", "FR-001 FR-002\n```\nok\n```\n")
        with self.assertRaises(orc.RuleViolation) as ctx:
            orc.submit(self.root, "verify")
        self.assertIn("NFR-001", str(ctx.exception))

    def test_verify_needs_code_block(self) -> None:
        for phase in IDS[:6]:
            self.advance(phase)
        self.write("verify", "FR-001 FR-002 NFR-001\n")
        with self.assertRaises(orc.RuleViolation):
            orc.submit(self.root, "verify")


class CheckAndReopenTests(OrchestratorTestCase):
    def test_future_artifact_detected(self) -> None:
        self.write("architecture")
        with self.assertRaises(orc.RuleViolation) as ctx:
            orc.check(self.root)
        self.assertIn("architecture", str(ctx.exception))

    def test_hash_mismatch_detected(self) -> None:
        self.advance("requirements")
        path = self.root / "artifacts" / "requirements.md"
        path.write_text(path.read_text() + "changed\n")
        with self.assertRaises(orc.RuleViolation) as ctx:
            orc.check(self.root)
        self.assertIn("changed since approval", str(ctx.exception))

    def test_missing_protected_path_detected(self) -> None:
        shutil.rmtree(self.root / "hooks")
        with self.assertRaises(orc.RuleViolation) as ctx:
            orc.check(self.root)
        self.assertIn("hooks/", str(ctx.exception))

    def test_reopen_refused_then_allowed(self) -> None:
        self.advance("requirements")
        self.advance("architecture")
        self.advance("design-review")
        with self.assertRaises(orc.RuleViolation) as ctx:
            orc.reopen(self.root, "architecture", "REVISE", confirmed=True)
        self.assertIn("design-review.md", str(ctx.exception))
        (self.root / "artifacts" / "design-review.md").unlink()
        orc.reopen(self.root, "architecture", "REVISE", confirmed=True)
        self.assertEqual(self.status("architecture"), "ACTIVE")
        self.assertEqual(self.status("design-review"), "LOCKED")
        self.assertEqual(self.status("planning"), "LOCKED")
        self.assertEqual(self.status("requirements"), "APPROVED")

    def test_reopen_requires_approved_phase(self) -> None:
        with self.assertRaises(orc.RuleViolation):
            orc.reopen(self.root, "requirements", "why", confirmed=True)


class CliTests(OrchestratorTestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        shutil.copy(REPO / "orchestrator.py", self.root / "orchestrator.py")
        return subprocess.run(
            [sys.executable, str(self.root / "orchestrator.py"), *args],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            cwd=self.root, timeout=60)

    def test_human_commands_refused_without_tty(self) -> None:
        self.write("requirements")
        orc.submit(self.root, "requirements")
        for args in (["approve", "requirements", "--by", "x"],
                     ["reject", "requirements", "--reason", "x"],
                     ["reopen", "requirements", "--reason", "x"]):
            with self.subTest(args[0]):
                proc = self.run_cli(*args)
                self.assertEqual(proc.returncode, 1)
                self.assertIn("interactive terminal", proc.stderr)
        self.assertEqual(self.status("requirements"), "AWAITING_APPROVAL")

    def test_cli_exit_codes_and_json(self) -> None:
        self.assertEqual(self.run_cli("submit", "nonsense").returncode, 2)
        self.assertEqual(self.run_cli("submit", "architecture").returncode, 1)
        self.assertEqual(self.run_cli("bogus").returncode, 2)
        proc = self.run_cli("status", "--json")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout)["currentPhase"],
                         "requirements")


if __name__ == "__main__":
    unittest.main()
