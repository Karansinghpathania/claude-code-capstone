#!/usr/bin/env python3
"""SDLC pipeline orchestrator. Rules: docs/CONTRACT.md.

Phases, owned files and protected paths are loaded from sdlc/phases.json.
Runtime state: sdlc/state.json. Audit log: sdlc/audit.log.jsonl.

HONEST LIMITATION: the human-only confirmation (TTY check plus typing the
phase id) is a demo-grade control. A determined user can bypass it, for
example by editing sdlc/state.json or calling the Python functions with
confirmed=True. Real enforcement comes from the Copilot hook (Part 3),
pull-request review and branch protection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

STATUSES = ("LOCKED", "ACTIVE", "AWAITING_APPROVAL", "APPROVED")
_RANK = {"APPROVED": 0, "ACTIVE": 1, "AWAITING_APPROVAL": 1, "LOCKED": 2}
_FIELDS = {"status", "hashes", "approvedBy", "approvedAt", "rejectionReason"}
ID_RE = re.compile(r"\b(?:FR|NFR)-\d{3}\b")
FR_RE = re.compile(r"\bFR-\d{3}\b")
DEFAULT_ACTOR = "agent/system"
HUMAN_HINT = "A human must run it in an interactive terminal and type the id"
# Traceability policy keyed by phase id; phases not listed get no ID checks.
REQ_PHASE = "requirements"
TRACE_RULES: dict[str, tuple[str, ...]] = {
    "requirements": ("fr", "open"),
    "architecture": ("any",),
    "design-review": ("any", "verdict"),
    "planning": ("any",),
    "review": ("all",),
    "verify": ("all", "fence"),
    "pr": ("all",),
}


class RuleViolation(Exception):
    """A pipeline rule was broken (exit code 1)."""

    def __init__(self, rule: str, hint: str = "") -> None:
        super().__init__(f"RULE VIOLATION: {rule}. {hint}".rstrip())


class UsageError(Exception):
    """Bad usage, e.g. unknown phase id (exit code 2)."""


def _require(cond: bool, rule: str, hint: str) -> None:
    if not cond:
        raise RuleViolation(rule, hint)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- manifest
def load_manifest(root: Path) -> dict[str, Any]:
    path = root / "sdlc" / "phases.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["phases"] = sorted(data["phases"], key=lambda p: p["order"])
        data["protected"] = list(data["protected"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuleViolation(f"sdlc/phases.json is missing or invalid "
                            f"({exc})", "Restore it from git") from exc
    return data


def _ids(m: dict[str, Any]) -> list[str]:
    return [p["id"] for p in m["phases"]]


def _get(m: dict[str, Any], phase: str) -> dict[str, Any]:
    for p in m["phases"]:
        if p["id"] == phase:
            return p
    raise UsageError(f"unknown phase '{phase}'. "
                     f"Valid phases: {', '.join(_ids(m))}")


# ------------------------------------------------------------------- state
def _blank(status: str, reason: str | None = None) -> dict[str, Any]:
    return {"status": status, "hashes": {}, "approvedBy": None,
            "approvedAt": None, "rejectionReason": reason}


def init_state(root: Path) -> dict[str, Any]:
    ids = _ids(load_manifest(root))
    state = {"phases": {i: _blank("ACTIVE" if n == 0 else "LOCKED")
                        for n, i in enumerate(ids)}}
    save_state(root, state)
    log = root / "sdlc" / "audit.log.jsonl"
    log.touch(exist_ok=True)
    return state


def save_state(root: Path, state: dict[str, Any]) -> None:
    path = root / "sdlc" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _bad(why: str) -> RuleViolation:
    return RuleViolation(f"sdlc/state.json is invalid ({why})",
                         "Ask the human to restore it from git or delete "
                         "it so it is re-initialised")


def _validate(state: Any, ids: list[str]) -> None:
    phases = state.get("phases") if isinstance(state, dict) else None
    if not isinstance(phases, dict):
        raise _bad("missing 'phases' object")
    extra, missing = set(phases) - set(ids), set(ids) - set(phases)
    if extra or missing:
        raise _bad(f"unknown phases {sorted(extra)}, "
                   f"missing phases {sorted(missing)}")
    for i in ids:
        e = phases[i]
        if not isinstance(e, dict) or set(e) != _FIELDS:
            raise _bad(f"phase '{i}' has wrong fields")
        if e["status"] not in STATUSES:
            raise _bad(f"phase '{i}' has invalid status {e['status']!r}")
        if not isinstance(e["hashes"], dict):
            raise _bad(f"phase '{i}' hashes must be an object")
    ranks = [_RANK[phases[i]["status"]] for i in ids]
    if ranks != sorted(ranks):
        raise _bad("statuses out of order, e.g. APPROVED after a "
                   "non-APPROVED phase")
    if ranks.count(1) > 1:
        raise _bad("more than one ACTIVE/AWAITING_APPROVAL phase")
    if 2 in ranks and 1 not in ranks:
        raise _bad("LOCKED phases remain but none is ACTIVE")


def load_state(root: Path, m: dict[str, Any]) -> dict[str, Any]:
    path = root / "sdlc" / "state.json"
    if not path.exists():
        raise RuleViolation("sdlc/state.json is missing",
                            "Run `python orchestrator.py status` to create it")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _bad(f"corrupt JSON: {exc}") from exc
    _validate(state, _ids(m))
    return state


def derive(m: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    ids, st = _ids(m), state["phases"]
    cur = next((i for i in ids if _RANK[st[i]["status"]] == 1), None)
    pos = ids.index(cur) if cur else len(ids)
    status = st[cur]["status"] if cur else "APPROVED"
    owns = _get(m, cur)["owns"] if cur else []
    approval = {"AWAITING_APPROVAL": "PENDING_HUMAN_APPROVAL",
                "ACTIVE": "NOT_SUBMITTED"}.get(status, "COMPLETE")
    return {"currentPhase": cur,
            "previousPhase": ids[pos - 1] if pos > 0 else None,
            "nextPhase": ids[pos + 1] if pos + 1 < len(ids) else None,
            "phaseStatus": status, "approvalStatus": approval,
            "requiredArtifacts": owns,
            "allowedFiles": owns if status == "ACTIVE" else []}


# ------------------------------------------------------- hashing and audit
def hash_files(root: Path, files: list[str]) -> dict[str, str]:
    return {f: hashlib.sha256((root / f).read_bytes()).hexdigest()
            for f in files if (root / f).is_file()}


def _drift(root: Path, files: list[str], recorded: dict[str, str]) -> list[str]:
    now = hash_files(root, files)
    return [f for f in files if now.get(f) != recorded.get(f)]


def audit(root: Path, actor: str, action: str, phase: str | None,
          result: str, detail: str, hashes: dict[str, str] | None = None
          ) -> None:
    entry: dict[str, Any] = {"timestamp": _now(), "actor": actor,
                             "action": action, "phase": phase,
                             "result": result, "detail": detail}
    if hashes:
        entry["hashes"] = hashes
    path = root / "sdlc" / "audit.log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def _guarded(root: Path, action: str, phase: str | None, actor: str,
             fn: Callable[[], tuple[str, dict[str, str] | None]]) -> str:
    """Run fn, auditing both success and refusal."""
    try:
        detail, hashes = fn()
    except RuleViolation as exc:
        audit(root, actor, action, phase, "refused", str(exc))
        raise
    audit(root, actor, action, phase, "ok", detail, hashes)
    return detail


# ------------------------------------------------------------ traceability
def _read(root: Path, files: list[str]) -> str:
    return "\n".join((root / f).read_text(encoding="utf-8", errors="replace")
                     for f in files if (root / f).is_file())


def _rule_problems(rule: str, text: str, found: set[str],
                   defined: set[str]) -> list[str]:
    if rule == "fr" and not FR_RE.search(text):
        return ["must define at least one FR-### id"]
    if rule == "open":
        sec = re.search(r"^## Open Questions[ \t]*$(.*?)(?=^## |\Z)", text,
                        re.M | re.S)
        if not sec:
            return ['missing heading "## Open Questions"']
        if re.search(r"^\s*- \[ \]", sec.group(1), re.M):
            return ['"## Open Questions" has unchecked "- [ ]" items; '
                    "the human must answer them or the section says None"]
    if rule == "any" and not found & defined:
        return ["must reference at least one id defined in requirements"]
    if rule == "verdict" and not re.search(
            r"^\s*Verdict: (?:APPROVE|REVISE)\b", text, re.M):
        return ['must contain a line "Verdict: APPROVE" or "Verdict: REVISE"']
    if rule == "all" and defined - found:
        return [f"must mention every defined id; missing: "
                f"{', '.join(sorted(defined - found))}"]
    if rule == "fence" and not re.search(r"^\s*```.*?^\s*```", text,
                                         re.M | re.S):
        return ["must contain a fenced code block with command output"]
    return []


def check_traceability(root: Path, phase: str) -> list[str]:
    rules = TRACE_RULES.get(phase)
    if rules is None:
        return []
    m = load_manifest(root)
    text = _read(root, _get(m, phase)["owns"])
    found = set(ID_RE.findall(text))
    if phase == REQ_PHASE:
        defined = found
    else:
        defined = set(ID_RE.findall(_read(root, _get(m, REQ_PHASE)["owns"])))
    problems = [] if defined else ["requirements define no FR-/NFR- ids"]
    if phase != REQ_PHASE and found - defined:
        problems.append("references undefined ids: "
                        + ", ".join(sorted(found - defined)))
    for rule in rules:
        problems += _rule_problems(rule, text, found, defined)
    return problems


# ---------------------------------------------------------------- commands
def _need(entry: dict[str, Any], want: str, phase: str, action: str) -> None:
    _require(entry["status"] == want,
             f"{action} needs {want} but '{phase}' is {entry['status']}",
             "Run `python orchestrator.py next` to see what is allowed")


def submit(root: Path, phase: str, actor: str = DEFAULT_ACTOR) -> str:
    m = load_manifest(root)
    owns = _get(m, phase)["owns"]

    def run() -> tuple[str, dict[str, str] | None]:
        state = load_state(root, m)
        entry = state["phases"][phase]
        _need(entry, "ACTIVE", phase, "submit")
        empty = [f for f in owns if not (root / f).is_file()
                 or not (root / f).read_bytes().strip()]
        _require(not empty, "owned files missing or empty: "
                 + ", ".join(empty), "Create them with real content first")
        issues = check_traceability(root, phase)
        _require(not issues, "traceability checks failed:\n  - "
                 + "\n  - ".join(issues), "Fix the artifact and resubmit")
        hashes = hash_files(root, owns)
        entry.update(status="AWAITING_APPROVAL", hashes=hashes)
        save_state(root, state)
        return f"'{phase}' submitted, AWAITING_APPROVAL", hashes

    return _guarded(root, "submit", phase, actor, run)


def approve(root: Path, phase: str, by: str, confirmed: bool = False) -> str:
    m = load_manifest(root)
    owns = _get(m, phase)["owns"]
    if not by.strip():
        raise UsageError("--by must not be empty")

    def run() -> tuple[str, dict[str, str] | None]:
        _require(confirmed, "approve must be confirmed by a human",
                 HUMAN_HINT)
        state = load_state(root, m)
        entry = state["phases"][phase]
        _need(entry, "AWAITING_APPROVAL", phase, "approve")
        drift = _drift(root, owns, entry["hashes"])
        _require(not drift, "files changed since submit (tamper detection): "
                 + ", ".join(drift),
                 "Human should `reject` the phase so it is fixed and resubmitted")
        entry.update(status="APPROVED", approvedBy=by, approvedAt=_now())
        ids = _ids(m)
        nxt = ids.index(phase) + 1
        detail = f"'{phase}' approved by {by}. Pipeline complete"
        if nxt < len(ids):
            state["phases"][ids[nxt]]["status"] = "ACTIVE"
            detail = f"'{phase}' approved by {by}; '{ids[nxt]}' is ACTIVE"
        save_state(root, state)
        return detail, dict(entry["hashes"])

    return _guarded(root, "approve", phase, by, run)


def reject(root: Path, phase: str, reason: str,
           confirmed: bool = False) -> str:
    m = load_manifest(root)
    _get(m, phase)
    if not reason.strip():
        raise UsageError("--reason is mandatory")

    def run() -> tuple[str, dict[str, str] | None]:
        _require(confirmed, "reject must be confirmed by a human",
                 HUMAN_HINT)
        state = load_state(root, m)
        entry = state["phases"][phase]
        _need(entry, "AWAITING_APPROVAL", phase, "reject")
        entry.update(status="ACTIVE", hashes={}, rejectionReason=reason)
        save_state(root, state)
        return f"'{phase}' rejected, ACTIVE again: {reason}", None

    return _guarded(root, "reject", phase, "human", run)


def reopen(root: Path, phase: str, reason: str,
           confirmed: bool = False) -> str:
    m = load_manifest(root)
    _get(m, phase)
    if not reason.strip():
        raise UsageError("--reason is mandatory")

    def run() -> tuple[str, dict[str, str] | None]:
        _require(confirmed, "reopen must be confirmed by a human",
                 HUMAN_HINT)
        state = load_state(root, m)
        _need(state["phases"][phase], "APPROVED", phase, "reopen")
        ids = _ids(m)
        later = ids[ids.index(phase) + 1:]
        files = [f for i in later for f in _get(m, i)["owns"]
                 if (root / f).exists()]
        _require(not files, "later phases still have files on disk: "
                 + ", ".join(files),
                 "Delete or move these files first, then reopen")
        for i in later:
            state["phases"][i] = _blank("LOCKED")
        state["phases"][phase] = _blank("ACTIVE", reason)
        save_state(root, state)
        return f"'{phase}' reopened, later phases LOCKED: {reason}", None

    return _guarded(root, "reopen", phase, "human", run)


def check(root: Path, actor: str = DEFAULT_ACTOR) -> str:
    m = load_manifest(root)

    def run() -> tuple[str, dict[str, str] | None]:
        state = load_state(root, m)
        problems: list[str] = []
        for p in m["phases"]:
            e = state["phases"][p["id"]]
            if e["status"] == "LOCKED":
                problems += [f"LOCKED phase '{p['id']}' owns existing "
                             f"file: {f}" for f in p["owns"]
                             if (root / f).exists()]
            elif e["status"] == "APPROVED":
                problems += [f"APPROVED phase '{p['id']}' file changed "
                             f"since approval: {f}"
                             for f in _drift(root, p["owns"], e["hashes"])]
        problems += [f"protected path missing: {x}" for x in m["protected"]
                     if not (root / x.rstrip("/")).exists()]
        _require(not problems, "check failed:\n  - " + "\n  - ".join(problems),
                 "Remove future-phase files, restore changed or missing "
                 "files from git")
        return "all checks passed", None

    return _guarded(root, "check", None, actor, run)


# ----------------------------------------------------------------- display
def status_data(root: Path, m: dict[str, Any]) -> dict[str, Any]:
    state = load_state(root, m)
    rows = [{"order": p["order"], "id": p["id"],
             "status": state["phases"][p["id"]]["status"],
             "approvedBy": state["phases"][p["id"]]["approvedBy"]}
            for p in m["phases"]]
    return {"phases": rows, **derive(m, state)}


def status_text(data: dict[str, Any]) -> str:
    lines = [f"{'#':<3}{'PHASE':<16}{'STATUS':<20}APPROVED BY"]
    lines += [f"{r['order']:<3}{r['id']:<16}{r['status']:<20}"
              f"{r['approvedBy'] or '-'}" for r in data["phases"]]
    lines += [""] + [f"{k}: {v}" for k, v in data.items() if k != "phases"]
    return "\n".join(lines)


def next_step(root: Path, m: dict[str, Any]) -> str:
    d = derive(m, load_state(root, m))
    cur = d["currentPhase"]
    if cur is None:
        return "Pipeline complete: every phase is APPROVED."
    if d["phaseStatus"] == "AWAITING_APPROVAL":
        return (f"Phase '{cur}' is AWAITING_APPROVAL.\nHuman must run: "
                f"python orchestrator.py approve {cur} --by <name>")
    ph = _get(m, cur)
    return (f"ACTIVE phase: {cur}\nRun prompt: /{cur} ({ph['prompt']})\n"
            f"Must produce: {', '.join(ph['owns'])}\n"
            f"Then run: python orchestrator.py submit {cur}")


# --------------------------------------------------------------------- CLI
def _confirm(root: Path, action: str, phase: str) -> bool:
    if not sys.stdin.isatty():
        exc = RuleViolation("approve/reject/reopen must be run by a human "
                            "in an interactive terminal",
                            "Agents must never run them; ask the human")
        audit(root, "unknown", action, phase, "refused", str(exc))
        raise exc
    try:
        return input("Type the phase id to confirm: ").strip() == phase
    except EOFError:
        return False


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="orchestrator.py",
                                description="SDLC pipeline orchestrator")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("status").add_argument("--json", action="store_true")
    sub.add_parser("next")
    sub.add_parser("check")
    sub.add_parser("submit").add_argument("phase")
    a = sub.add_parser("approve")
    a.add_argument("phase")
    a.add_argument("--by", required=True)
    for name in ("reject", "reopen"):
        r = sub.add_parser(name)
        r.add_argument("phase")
        r.add_argument("--reason", required=True)
    return p


def _dispatch(root: Path, m: dict[str, Any], args: argparse.Namespace) -> str:
    cmd = args.command
    if cmd == "status":
        data = status_data(root, m)
        return json.dumps(data, indent=2) if args.json else status_text(data)
    if cmd == "next":
        return next_step(root, m)
    if cmd == "check":
        return check(root)
    _get(m, args.phase)
    if cmd == "submit":
        return submit(root, args.phase)
    ok = _confirm(root, cmd, args.phase)
    if cmd == "approve":
        return approve(root, args.phase, args.by, ok)
    if cmd == "reject":
        return reject(root, args.phase, args.reason, ok)
    return reopen(root, args.phase, args.reason, ok)


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    root = root or Path(__file__).resolve().parent
    args = build_parser().parse_args(argv)
    try:
        m = load_manifest(root)
        if not (root / "sdlc" / "state.json").exists():
            init_state(root)
        print(_dispatch(root, m, args))
    except RuleViolation as exc:
        print(exc, file=sys.stderr)
        return 1
    except UsageError as exc:
        print(f"USAGE ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
