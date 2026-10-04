#!/usr/bin/env python3
"""Pre-tool-use hook guard for the SDLC pipeline (see docs/CONTRACT.md).

Demonstration guard. Not complete shell-security coverage.

CONFIRMED FROM THE OFFICIAL DOCS (read 2026-10-03):
  VS Code "Local hooks reference" and GitHub "Copilot hooks reference"
  - Config: .github/hooks/*.json. VS Code Local format (PascalCase event,
    no "version"): {"hooks": {"PreToolUse": [{"type": "command",
    "command": "...", "windows": "...", "timeout": 15}]}}. Copilot CLI and
    cloud agent format: {"version": 1, "hooks": {"preToolUse": [{"type":
    "command", "bash": "...", "powershell": "...", "timeoutSec": 15}]}};
    there "command" is a cross-platform fallback.
  - Event: PreToolUse (Local, PascalCase) / preToolUse (CLI + cloud, camel).
  - stdin JSON (Local): hook_event_name, session_id, timestamp, cwd,
    tool_name, tool_input (object), tool_use_id. Copilot camelCase format:
    toolName, toolArgs (arguments, may be a JSON string).
  - DENY: exit code 2 (stderr is shown to the model), or exit 0 with stdout
    {"hookSpecificOutput": {"hookEventName": "PreToolUse",
    "permissionDecision": "deny", "permissionDecisionReason": "..."}}
    (Local) / {"permissionDecision": "deny", "permissionDecisionReason":
    "..."} (Copilot CLI + cloud). ALLOW: exit 0 with empty stdout.
  - Copilot CLI/cloud: a crashing or non-zero preToolUse command hook
    denies, but a hook TIMEOUT FAILS OPEN. Keep this script fast.
NOT CONFIRMED BY THE DOCS: the exact Local tool names and the field names
inside tool_input (the docs say to inspect the agent debug logs). Every such
assumption lives in parse_payload() below, so a format change touches only
that function.

R01 choice: "rm -rf <named dir>" (node_modules, __pycache__) is allowed;
only dangerous targets (/, ~, $HOME, ., .., repo root, .git, bare *) are not.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Callable, NamedTuple
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent


class MalformedPayload(ValueError):
    """The hook input could not be understood (the guard then fails closed)."""


class Policy(NamedTuple):
    known: bool  # sdlc/phases.json was readable
    protected: list[str]
    owned: dict[str, str]  # owned file -> phase id
    active: str | None
    error: str | None


class Req(NamedTuple):
    root: Path
    segments: list[str]  # shell command pieces (nested bash -c expanded)
    paths: list[str]  # repo-relative paths the tool call would modify
    policy: Policy


class Rule(NamedTuple):
    id: str
    description: str
    matcher: Callable[[Req], str | None]  # returns what matched, or None
    reason: str
    safe_alternative: str


RULES = [
    Rule("R01", "Recursive deletion of /, ~, $HOME, ., .., the repo root, "
         ".git or a bare * (rm -rf <named dir> is allowed)",
         lambda r: m_rm(r), "Could wipe the machine or the whole repository.",
         "Delete the specific directory, e.g. rm -rf node_modules"),
    Rule("R02", "Dangerous disk or permission operations (mkfs, dd of=/dev/, "
         "chmod -R 777, writes to /dev/sd*)", lambda r: m_disk(r),
         "Can destroy disks or make the system insecure.",
         "Use a file inside the repo and narrower permissions (chmod 644)."),
    Rule("R03", "Destructive git (reset --hard, clean -f, checkout -- ., "
         "restore ., branch -D main, filter-branch, rebase on main)",
         lambda r: m_git_destructive(r),
         "Discards work or rewrites history; the rules forbid this.",
         "Use git status/diff, git stash, or git revert."),
    Rule("R04", "Force push, +refspec push, or any push to main/master "
         "(--force-with-lease to a feature branch is allowed)",
         lambda r: m_push(r), "Overwrites shared history or bypasses review.",
         "git push --force-with-lease origin <feature-branch>, then a PR."),
    Rule("R05", "Bypass attempts (--no-verify, hooksPath/hook config, "
         "curl|sh, base64 -d | sh, eval | sh)", lambda r: m_bypass(r),
         "Disables or evades safety checks.",
         "Fix what the hook complains about and commit normally."),
    Rule("R06", "SDLC human-only commands (orchestrator.py approve/reject/"
         "reopen)", lambda r: m_orchestrator(r),
         "Only a human may approve, reject or reopen a phase.",
         "Run `python orchestrator.py status`, tell the human, and let them "
         "run the command in a separate terminal."),
    Rule("R07", "Writes to protected files listed in sdlc/phases.json",
         lambda r: m_protected(r), "Protected files are the pipeline's "
         "control plane; agents must never modify them.",
         "Ask the human to make the change."),
    Rule("R08", "Writes to a file owned by a phase that is not ACTIVE",
         lambda r: m_scope(r), "A phase may only write its own files, and "
         "only while it is ACTIVE.",
         "Write only the files listed under Phase; if blocked, stop and "
         "tell the human."),
]

# ------------------------------------------------------------ payload format
SHELL_HINTS = ("terminal", "shell", "bash", "powershell")
NOT_RUNNING = ("output", "last", "selection", "kill")
WRITE_EXACT = {"edit", "write", "create", "multiedit", "notebookedit",
               "strreplaceeditor", "strreplace", "applypatch"}
WRITE_VERBS = ("create", "edit", "write", "replace", "insert", "delete",
               "rename", "move", "remove", "append", "save", "update", "patch")
WRITE_NOUNS = ("file", "notebook", "directory", "folder")


def _collect_paths(obj: Any, key: str = "") -> list[str]:
    out: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += _collect_paths(v, re.sub(r"[^a-z]", "", str(k).lower()))
    elif isinstance(obj, list):
        for v in obj:
            out += _collect_paths(v, key)
    elif isinstance(obj, str):
        if "path" in key or key in ("file", "uri", "filename", "target",
                                    "destination", "files"):
            if obj.startswith("file:"):  # file:///c%3A/x -> c:/x
                obj = re.sub(r"^/([a-zA-Z]:)", r"\1",
                             unquote(urlparse(obj).path))
            out.append(obj)
        out += [m.group(1) for m in re.finditer(  # apply_patch bodies
            r"^\*\*\* (?:(?:Add|Update|Delete) File|Move to): (.+?)\s*$",
            obj, re.M)]
    return out


def parse_payload(raw: str) -> tuple[str, str | None, list[str]]:
    """Return (tool_name, shell_command_or_None, target_paths).

    The ONLY function that knows the hook JSON layout and tool names.
    Supports both GitHub Copilot and Claude Code formats.
    Raises MalformedPayload when a tool that could modify things cannot be
    understood, so that main() fails closed.
    """
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise MalformedPayload(f"stdin is not valid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise MalformedPayload("payload is not a JSON object")
    # Support both Copilot (camelCase) and Claude Code (snake_case) field names
    tool = data.get("tool_name", data.get("toolName"))
    args = data.get("tool_input", data.get("toolArgs"))
    if not isinstance(tool, str) or not tool:
        raise MalformedPayload("no tool_name / toolName")
    if isinstance(args, str):  # Copilot CLI and Claude Code may send arguments as a string
        try:
            args = json.loads(args)
        except ValueError:
            pass
    key = re.sub(r"[^a-z]", "", tool.lower())
    if (any(h in key for h in SHELL_HINTS)
            and not any(n in key for n in NOT_RUNNING)):
        cmd = args.get("command", args.get("cmd")) \
            if isinstance(args, dict) else None
        if not isinstance(cmd, str):
            raise MalformedPayload(f"shell tool '{tool}' has no 'command'")
        return tool, cmd, []
    if key in WRITE_EXACT or (any(v in key for v in WRITE_VERBS)
                              and any(n in key for n in WRITE_NOUNS)):
        paths = _collect_paths(args)
        if not paths:
            raise MalformedPayload(f"file tool '{tool}' has no known path")
        return tool, None, paths
    return tool, None, []


# ----------------------------------------------------------- shell analysis
WRAPPERS = {"sudo", "env", "time", "nohup", "command", "exec"}
SHELLS = {"bash", "sh", "zsh", "dash", "pwsh", "powershell", "cmd"}
RM = {"rm", "rmdir", "del", "erase", "rd", "ri", "remove-item"}
ALL_ARGS = RM | {"mv", "tee", "truncate", "touch", "move", "move-item", "mi",
                 "ren", "rename-item", "set-content", "add-content", "sc",
                 "ac", "out-file", "clear-content", "new-item", "ni",
                 "unlink", "shred"}
DEST_ONLY = {"cp", "copy", "copy-item", "cpi", "install", "ln"}
DANGER = {"", "~", "$home", "${home}", ".git", "*", "./*", ".*", "/*",
          "~/*", "$home/*", "%userprofile%", "$env:userprofile", "c:"}
WRITE_CODE = re.compile(
    r"write_text|write_bytes|\.write\(|unlink|os\.(?:remove|replace|rename)|"
    r"shutil\.|truncate|writefile|set-content|"
    r"open\([^)]*,\s*['\"][^'\"]*[wax+]", re.I)
_Q = r"""(?=(?:[^'"]|'[^']*'|"[^"]*")*$)"""  # delimiter not inside quotes


def _split(s: str, delim: str) -> list[str]:
    return re.split(delim + _Q, s)


def _tok(s: str) -> list[str]:
    try:
        return shlex.split(s)
    except ValueError:
        return s.split()


def _name(t: str) -> str:
    n = t.rsplit("/", 1)[-1].lower()
    return n[:-4] if n.endswith(".exe") else n


def _units(seg: str) -> list[list[str]]:
    """Piped commands of a segment as token lists, wrappers stripped."""
    out = []
    for part in _split(seg, r"\|"):
        t = _tok(part)
        while t and (_name(t[0]) in WRAPPERS
                     or re.fullmatch(r"\w+=\S*", t[0])):
            t = t[1:]
        if t:
            out.append(t)
    return out


def expand(cmd: str) -> list[str]:
    """Split a command on ; && || & newline (outside quotes); recurse into
    `bash -c "..."`, `powershell -Command ...` and `cmd /c ...`."""
    out: list[str] = []
    for seg in _split(cmd.replace("\\", "/"), r"\|\||&&|[;&\n]"):
        if not seg.strip():
            continue
        out.append(seg.strip())
        for t in _units(seg):
            if _name(t[0]) in SHELLS:
                for i, x in enumerate(t):
                    if x.lower() in ("-c", "-lc", "-command", "/c"):
                        out += expand(" ".join(t[i + 1:]))
                        break
    return out


def _git(t: list[str]) -> tuple[str, list[str]] | None:
    if _name(t[0]) != "git":
        return None
    i = 1
    while i < len(t) and t[i].startswith("-"):  # skip global -C/-c options
        i += 2 if t[i] in ("-C", "-c") else 1
    return (t[i], t[i + 1:]) if i < len(t) else None


def _gits(req: Req) -> list[tuple[str, list[str]]]:
    return [g for s in req.segments for t in _units(s)
            if (g := _git(t)) is not None]


def _rel(root: Path, p: str) -> str | None:
    """Repo-relative posix path, or None if outside the repo."""
    try:
        full = os.path.normpath(os.path.join(root, p.strip().strip("'\"")
                                             .replace("\\", "/")))
        rel = os.path.relpath(full, root)
    except ValueError:  # different drive on Windows
        return None
    if rel == ".." or rel.startswith(".." + os.sep):
        return None
    return rel.replace(os.sep, "/")


def written_paths(seg: str) -> list[str]:
    """Raw path strings that a shell segment would modify (best effort)."""
    out: list[str] = []
    for t in _units(seg):
        n, args = _name(t[0]), t[1:]
        for i, a in enumerate(t):  # redirections: > >> 2> >file
            m = re.fullmatch(r"\d*>>?(.*)", a)
            if m:
                tgt = m.group(1) or (t[i + 1] if i + 1 < len(t) else "")
                if tgt and not tgt.startswith("&"):
                    out.append(tgt)
        pos = [a for a in args if not a.startswith("-")
               and not re.fullmatch(r"\d*>>?.*", a)]
        in_place = n in ("sed", "perl") and any(
            re.fullmatch(r"-[a-zA-Z]*i[a-zA-Z.]*|--in-place.*", a)
            for a in args)
        g = _git(t)
        if n in ALL_ARGS or in_place:
            out += pos
        elif n in DEST_ONLY and pos:
            out.append(pos[-1])  # only the destination is modified
        elif g and g[0] in ("rm", "mv", "restore", "checkout"):
            out += [a for a in g[1] if not a.startswith("-")]
        elif (re.fullmatch(r"python[\d.]*|pythonw|py|node|perl|ruby", n)
              and any(a in ("-c", "-e") for a in args)):
            code = " ".join(args)
            if WRITE_CODE.search(code):
                out += re.findall(r"""['"]([^'"\n]+)['"]""", code)
    return out


# ------------------------------------------------------------------ matchers
def m_rm(req: Req) -> str | None:
    for seg in req.segments:
        for t in _units(seg):
            n, args = _name(t[0]), t[1:]
            if n not in RM:
                continue
            rec = any(re.fullmatch(r"--recursive|-recurse|/s", a, re.I)
                      or (n == "rm"
                          and re.fullmatch(r"-[a-zA-Z]*[rR][a-zA-Z]*", a))
                      for a in args)
            for a in (x for x in args if not x.startswith("-") and x != "/s"):
                bad = (a.rstrip("/").lower() in DANGER
                       or re.fullmatch(r"(\.\.?/?)+", a)
                       or _rel(req.root, a) == ".")
                if rec and bad:
                    return f"{n} recursive on '{a}'"
    return None


def m_disk(req: Req) -> str | None:
    pat = re.compile(
        r"\bmkfs(?:\.\w+)?\b|\bdd\b.*\bof=/dev/(?!null\b)|>\s*/dev/sd|"
        r"\bchmod\b(?=.*(?:\s-[a-z]*R|--recursive))(?=.*\b0?777\b)")
    return next((m.group(0) for s in req.segments
                 if (m := pat.search(s))), None)


def m_git_destructive(req: Req) -> str | None:
    main = re.compile(r"(?:^|/)(?:main|master)$")
    for sub, a in _gits(req):
        force = any(re.fullmatch(r"-[a-z]*f[a-z]*|--force", x) for x in a)
        if ((sub == "reset" and "--hard" in a)
                or (sub == "clean" and force)
                or (sub == "checkout" and "." in a)
                or (sub == "restore" and "." in a and "--staged" not in a)
                or (sub == "branch" and any(main.search(x) for x in a)
                    and any(re.fullmatch(r"-[a-zA-Z]*D[a-zA-Z]*", x)
                            for x in a))
                or sub in ("filter-branch", "filter-repo")
                or (sub == "rebase" and any(main.search(x) for x in a))):
            return "git " + sub + " " + " ".join(a)
    return None


def m_push(req: Req) -> str | None:
    for sub, a in _gits(req):
        if sub != "push":
            continue
        pos = [x for x in a if not x.startswith("-")]
        force = any(re.fullmatch(r"-[a-z]*f[a-z]*|--force", x) for x in a)
        for ref in pos[1:]:  # pos[0] is the remote
            dest = ref.lstrip("+").split(":")[-1]
            if ref.startswith("+") or re.search(r"(?:^|/)(?:main|master)$",
                                                dest):
                return f"git push {' '.join(a)}"
        if force:
            return f"git push {' '.join(a)}"
    return None


def m_bypass(req: Req) -> str | None:
    pat = re.compile(
        r"core\.hookspath|\bgit\b.*\bconfig\b.*\bhook|"
        r"\b(?:curl|wget)\b.*\|\s*(?:sudo\s+)?(?:ba|z|da|k)?sh\b|"
        r"\|\s*(?:iex|invoke-expression)\b|"
        r"\bbase64\b\s+(?:-d|-D|--decode)\b.*\|\s*(?:sudo\s+)?"
        r"(?:ba|z|da)?sh\b|"
        r"\beval\b.*\|\s*(?:ba|z|da)?sh\b", re.I)
    for s in req.segments:
        if m := pat.search(s):
            return m.group(0)[:80]
    for sub, a in _gits(req):
        if "--no-verify" in a or (sub == "commit" and any(
                re.fullmatch(r"-[a-zA-Z]*n[a-zA-Z]*", x) for x in a)):
            return f"git {sub} skips hooks: {' '.join(a)}"
    return None


def m_orchestrator(req: Req) -> str | None:
    for seg in req.segments:
        for t in _units(seg):
            if re.fullmatch(r"python[\d.]*|pythonw|py", _name(t[0])):
                txt = " ".join(t[1:])
                if re.search(r"orchestrator\b.*\b(?:approve|reject|reopen)\b",
                             txt, re.S):
                    return "python " + txt[:80]
    return None


def _hits(rel: str, entry: str) -> bool:
    """rel is the entry, inside a dir entry, or a parent dir of the entry."""
    r, e = rel.casefold(), entry.casefold().rstrip("/")
    return r == e or r.startswith(e + "/") or e.startswith(r + "/")


def m_protected(req: Req) -> str | None:
    for rel in req.paths:
        for e in req.policy.protected:
            if _hits(rel, e):
                return f"write to '{rel}' (protected entry '{e}')"
    return None


def m_scope(req: Req) -> str | None:
    p = req.policy
    for rel in req.paths:
        if not p.known:
            return f"write to '{rel}' (policy unreadable: {p.error})"
        owners = {ph for f, ph in p.owned.items() if _hits(rel, f)}
        if owners and (p.error or owners - {p.active}):
            return f"write to '{rel}' owned by phase {sorted(owners)}"
    return None


# ------------------------------------------------------------------ plumbing
def load_policy(root: Path) -> Policy:
    try:
        m = json.loads((root / "sdlc" / "phases.json").read_text("utf-8"))
        protected = [str(x) for x in m["protected"]]
        owned = {f: p["id"] for p in m["phases"] for f in p["owns"]}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return Policy(False, [], {}, None, f"phases.json: {exc}")
    try:
        st = json.loads((root / "sdlc" / "state.json").read_text("utf-8"))
        act = [i for i, v in st["phases"].items() if v["status"] == "ACTIVE"]
        if len(act) > 1:
            raise ValueError("more than one ACTIVE phase")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return Policy(True, protected, owned, None, f"state.json: {exc}")
    return Policy(True, protected, owned, act[0] if act else None, None)


def scope_line(p: Policy) -> str:
    if p.error:
        return (f"policy unreadable ({p.error}); owned files are read-only "
                "until the human fixes sdlc/")
    if p.active is None:
        return ("no phase is ACTIVE (all awaiting approval or complete); "
                "no phase-owned file may be written")
    files = [f for f, ph in p.owned.items() if ph == p.active]
    return f"current phase '{p.active}' may write only: {', '.join(files)}"


def render(rule: str, desc: str, tool: str, detail: str, reason: str,
           alt: str, scope: str | None = None) -> str:
    lines = [f"BLOCKED by SDLC guard [{rule}]",
             f"  Blocked: {tool}: {detail}", f"  Rule:    {desc}",
             f"  Why:     {reason}", f"  Instead: {alt}"]
    if scope:
        lines.append(f"  Phase:   {scope}")
    return "\n".join(lines)


def evaluate(raw: str, root: Path = ROOT) -> str | None:
    """Return a denial message, or None when the tool call is allowed."""
    try:
        tool, command, paths = parse_payload(raw)
    except MalformedPayload as exc:
        return render("FAIL-CLOSED", "Payload could not be understood", "?",
                      str(exc), "A tool that may modify things cannot be "
                      "checked.", "Ask the human; do not retry blindly.")
    if command is None and not paths:
        return None
    segs = expand(command) if command else []
    raw_paths = paths + [p for s in segs for p in written_paths(s)]
    rels = [r for r in (_rel(root, p) for p in raw_paths)
            if r not in (None, ".")]
    req = Req(root, segs, rels, load_policy(root))
    for rule in RULES:
        if detail := rule.matcher(req):
            scope = scope_line(req.policy) if rule.id in ("R07", "R08") \
                else None
            return render(rule.id, rule.description, tool, detail,
                          rule.reason, rule.safe_alternative, scope)
    return None


def main() -> int:
    try:
        msg = evaluate(sys.stdin.buffer.read().decode("utf-8-sig"))
    except Exception as exc:  # noqa: BLE001 - guard bugs must fail closed
        msg = render("FAIL-CLOSED", "Guard error", "?",
                     f"{type(exc).__name__}: {exc}", "The guard could not "
                     "decide.", "Ask the human to check hooks/guard.py.")
    if msg is None:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "PreToolUse",
                               "permissionDecision": "deny",
                               "permissionDecisionReason": msg},
        "permissionDecision": "deny", "permissionDecisionReason": msg}))
    print(msg, file=sys.stderr)
    return 2  # exit 2 denies on every surface documented above


if __name__ == "__main__":
    sys.exit(main())
