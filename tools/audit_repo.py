#!/usr/bin/env python3
"""Audit the REAL repository against docs/CONTRACT.md.

Prints PASS or FAIL for every check and exits 1 if any check fails.
Read-only, except that `python orchestrator.py status` is run (it only reads
state, and the state check runs first so a missing state file is reported
instead of silently re-created). Standard library only.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
PHASE_COUNT = 8
SKILLS = ("requirements", "verify", "pr")
CAUGHT = (OSError, ValueError, KeyError, TypeError, IndexError,
          subprocess.SubprocessError)
Result = tuple[bool, str]


def manifest() -> dict:
    return json.loads((ROOT / "sdlc" / "phases.json").read_text("utf-8"))


def phases() -> list[dict]:
    return sorted(manifest()["phases"], key=lambda p: p["order"])


def exists(rel: str, kind: str = "file") -> Result:
    path = ROOT / rel
    ok = path.is_dir() if kind == "dir" else path.is_file()
    return ok, rel if ok else f"missing {rel}"


def run(args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *args], input=stdin, cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8",
                          timeout=60)


def guard(command: str) -> subprocess.CompletedProcess:
    payload = {"tool_name": "run_in_terminal",
               "tool_input": {"command": command}}
    return run(["hooks/guard.py"], json.dumps(payload))


# ---------------------------------------------------------------- checks
def contract_exists() -> Result:
    return exists("docs/CONTRACT.md")


def manifest_valid() -> Result:
    ps = phases()
    orders = [p["order"] for p in ps]
    if len(ps) != PHASE_COUNT or orders != list(range(1, PHASE_COUNT + 1)):
        return False, f"need {PHASE_COUNT} phases ordered 1..{PHASE_COUNT}, got {orders}"
    for p in ps:
        if not p["id"] or not p["owns"]:
            return False, f"phase {p.get('id')!r} has no id or owns nothing"
    return True, ", ".join(p["id"] for p in ps)


def no_overlap() -> Result:
    owners: dict[str, str] = {}
    for p in phases():
        for f in p["owns"]:
            for other, who in owners.items():
                if f == other or f.startswith(other + "/") or other.startswith(f + "/"):
                    return False, f"{f} ({p['id']}) overlaps {other} ({who})"
            owners[f] = p["id"]
    return True, f"{len(owners)} owned files, none shared"


def agents_exist() -> Result:
    # Phase 1 (requirements) is a slash command, not an agent
    missing = [p["agent"] for p in phases() if p["id"] != "requirements"
               and not (ROOT / p["agent"]).is_file()]
    return not missing, f"{PHASE_COUNT - 1} agents" if not missing else f"missing {missing}"


def prompts_exist() -> Result:
    missing = [p["prompt"] for p in phases() if not (ROOT / p["prompt"]).is_file()]
    return not missing, f"{PHASE_COUNT} commands" if not missing else f"missing {missing}"


def skills_exist() -> Result:
    missing = [s for s in SKILLS
               if not (ROOT / ".claude" / "skills" / s / "SKILL.md").is_file()]
    return not missing, f"{len(SKILLS)} skills" if not missing else f"missing {missing}"


def instructions_exist() -> Result:
    return exists("CLAUDE.md")


def hook_files() -> Result:
    for rel in ("hooks/guard.py", ".claude/settings.json"):
        ok, detail = exists(rel)
        if not ok:
            return ok, detail
    return True, "hooks/guard.py and .claude/settings.json"


def hook_wired() -> Result:
    text = (ROOT / ".claude" / "settings.json").read_text("utf-8")
    json.loads(text)
    return "hooks/guard.py" in text, "settings.json references hooks/guard.py"


def orchestrator_exists() -> Result:
    return exists("orchestrator.py")


def state_is_initial() -> Result:
    state = json.loads((ROOT / "sdlc" / "state.json").read_text("utf-8"))["phases"]
    want = {p["id"]: "ACTIVE" if p["order"] == 1 else "LOCKED" for p in phases()}
    got = {i: e["status"] for i, e in state.items()}
    return got == want, "requirements ACTIVE, others LOCKED" if got == want else f"got {got}"


def status_runs() -> Result:
    if not (ROOT / "sdlc" / "state.json").is_file():
        return False, "sdlc/state.json missing; not running status (it would create it)"
    done = run(["orchestrator.py", "status"])
    return done.returncode == 0, f"exit {done.returncode}"


def allowed_files(text: str) -> list[str]:
    sec = re.search(r"^## Allowed files\n(.*?)(?=^## )", text, re.M | re.S)
    return re.findall(r"`([\w./-]+\.(?:md|py))`", sec.group(1)) if sec else []


def agents_match_manifest() -> Result:
    bad = []
    for p in phases():
        # Phase 1 (requirements) is a slash command, not an agent
        if p["id"] == "requirements":
            continue
        got = allowed_files((ROOT / p["agent"]).read_text("utf-8"))
        if sorted(got) != sorted(p["owns"]):
            bad.append(f"{p['id']}: agent {got} != manifest {p['owns']}")
    return not bad, "agents match" if not bad else "; ".join(bad)


def guard_denies_dangerous() -> Result:
    done = guard("git reset --hard")
    return done.returncode == 2 and "[R03]" in done.stderr, f"exit {done.returncode}"


def guard_denies_approve() -> Result:
    done = guard("python orchestrator.py approve requirements --by x")
    return done.returncode == 2 and "[R06]" in done.stderr, f"exit {done.returncode}"


def guard_allows_harmless() -> Result:
    done = guard("git status")
    return done.returncode == 0 and not done.stdout, f"exit {done.returncode}"


def docs_exist() -> Result:
    for rel in ("README.md", "docs/RUNBOOK.md"):
        ok, detail = exists(rel)
        if not ok:
            return ok, detail
    return True, "README.md and docs/RUNBOOK.md"


def no_phase_artifacts() -> Result:
    extra = sorted(p.name for p in (ROOT / "artifacts").iterdir()
                   if p.name != ".gitkeep")
    found = [f"artifacts/{n}" for n in extra]
    found += [rel for rel in ("todo", "CHANGELOG.md", "tests/test_todo.py")
              if (ROOT / rel).exists()]
    return not found, "no generated artifacts" if not found else f"found {found}"


def story_exists() -> Result:
    return exists("user_story.md")


CHECKS: list[tuple[str, Callable[[], Result]]] = [
    ("docs/CONTRACT.md exists", contract_exists),
    ("sdlc/phases.json valid, 8 ordered phases", manifest_valid),
    ("no overlapping file ownership", no_overlap),
    ("8 agent files exist", agents_exist),
    ("8 prompt files exist", prompts_exist),
    ("3 skill files exist", skills_exist),
    (".github/copilot-instructions.md exists", instructions_exist),
    ("hook files exist", hook_files),
    ("hooks.json references guard.py", hook_wired),
    ("orchestrator.py exists", orchestrator_exists),
    ("real state: requirements ACTIVE, rest LOCKED", state_is_initial),
    ("python orchestrator.py status runs", status_runs),
    ("agent allowed files match phases.json", agents_match_manifest),
    ("guard denies a dangerous payload", guard_denies_dangerous),
    ("guard denies an approve attempt", guard_denies_approve),
    ("guard allows a harmless command", guard_allows_harmless),
    ("README.md and docs/RUNBOOK.md exist", docs_exist),
    ("no phase artifacts exist in the repo", no_phase_artifacts),
    ("user_story.md exists", story_exists),
]


def main() -> int:
    failures = 0
    for name, check in CHECKS:
        try:
            ok, detail = check()
        except CAUGHT as exc:
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    print(f"\n{len(CHECKS) - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
