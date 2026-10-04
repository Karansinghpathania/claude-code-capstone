# SDLC Pipeline Contract

## Purpose
user_story.md -> 8 phases, one custom agent each -> human approval after every phase -> PR raised by the last agent. Python 3.11+, stdlib only, unittest only. No third-party packages.

## Phases (strict order)
| # | id | agent file | command file | owns (only files this phase may write) |
|---|----|-----------|-------------|-----------------------------------------|
| 1 | requirements | .claude/commands/requirements.md (slash command, interactive) | .claude/commands/requirements.md | artifacts/requirements.md |
| 2 | architecture | .claude/agents/architecture.md | .claude/commands/architecture.md | artifacts/architecture.md |
| 3 | design-review | .claude/agents/design-review.md | .claude/commands/design-review.md | artifacts/design-review.md |
| 4 | planning | .claude/agents/planning.md | .claude/commands/planning.md | artifacts/implementation-plan.md |
| 5 | implementation | .claude/agents/implementation.md | .claude/commands/implementation.md | todo/__init__.py, todo/app.py, todo/cli.py, tests/test_todo.py |
| 6 | review | .claude/agents/review.md | .claude/commands/review.md | artifacts/review.md |
| 7 | verify | .claude/agents/verify.md | .claude/commands/verify.md | artifacts/verify.md |
| 8 | pr | .claude/agents/pr.md | .claude/commands/pr.md | artifacts/pr.md, CHANGELOG.md |

Phase 1 (requirements) is a slash command that runs interactively in the main Claude Code session, allowing the human to answer clarifying questions. Phases 2-8 are subagents. The command invocation name equals the phase id (e.g., `/requirements`, `/architecture`). Phase-5 file names (todo/...) are the example app for the sample story; the pipeline itself must stay story-agnostic.

## Status model
LOCKED -> ACTIVE -> AWAITING_APPROVAL -> APPROVED.
Initial: requirements ACTIVE, all others LOCKED.
submit (agent or human): ACTIVE -> AWAITING_APPROVAL.
approve (HUMAN ONLY): AWAITING_APPROVAL -> APPROVED, next phase LOCKED -> ACTIVE.
reject (HUMAN ONLY): AWAITING_APPROVAL -> ACTIVE (same phase, hashes cleared, reason logged). Next phase stays LOCKED.
reopen (HUMAN ONLY): rework an earlier APPROVED phase (see orchestrator rules).
A phase may only write its own files, and only while it is ACTIVE.

## Files
- sdlc/phases.json   manifest (phases, owned files, protected files)
- sdlc/state.json    runtime state, written only by orchestrator.py
- sdlc/audit.log.jsonl  append-only audit log, written only by orchestrator.py
- orchestrator.py    the single orchestrator script (importable + CLI)
- hooks/guard.py     the safety hook (blocks dangerous commands and enforces phase scope)
- .claude/settings.json   hook wiring and permissions
- CLAUDE.md  shared rules for all agents
- .claude/agents/*.md  subagent definitions for phases 2-8
- .claude/commands/*.md  slash command definitions for all phases
- .claude/skills/<name>/SKILL.md  reusable skill templates
- artifacts/   phase documents (empty until the live run)
- tests/       unittest tests
- user_story.md  the input

## Protected files (agents must never modify; hook enforces)
sdlc/state.json, sdlc/audit.log.jsonl, sdlc/phases.json, orchestrator.py, hooks/**, .claude/**

## Orchestrator CLI (python orchestrator.py ...)
status [--json] | next | submit <phase> | approve <phase> --by <name> | reject <phase> --reason <text> | reopen <phase> --reason <text> | check
Exit codes: 0 ok, 1 rule violation, 2 usage error. Every error says which rule failed and what to do.
approve, reject, reopen require an interactive terminal and the human typing the phase id to confirm; they refuse otherwise. Agents must NEVER run approve, reject or reopen.

## Traceability
Requirements use IDs FR-001, FR-002... and NFR-001... (regex \b(?:FR|NFR)-\d{3}\b). Later artifacts reference these IDs. Orchestrator enforces this at submit.

## Commands
Tests: python -m unittest discover -s tests -v
Syntax: python -m compileall -q .
Audit (clean pre-demo repo only): python tools/audit_repo.py

## Human-approval rule
No agent approves, advances or unlocks a phase. After submitting, every agent STOPS and prints: "Awaiting human approval. Run: python orchestrator.py approve <phase> --by <your-name>".
