---
name: verify
description: Kick off phase 7 (verify). The QA agent proves every requirement is met.
---

# /verify Command

## Phase 7: verify

STEP 1. Run `python orchestrator.py status`. If `verify` is not
ACTIVE, STOP, tell the human which phase is active, and do nothing else.

## Procedure

Follow `.claude/skills/verify/SKILL.md` for the method and artifact template.

1. Record the environment: run `python --version`.
2. For EVERY FR and NFR define one concrete check: test name, CLI command,
   or manual command, with the expected result.
3. Run each check now and paste the real, unedited output into a fenced block.
4. Mark each PASS or FAIL. A check you could not run is FAIL with reason.
5. Do not fix code, do not retry until it passes.

## Finish
1. Run `python orchestrator.py submit verify`. If it refuses, fix the artifact
   and retry (not the code).
2. STOP and print exactly:

Awaiting human approval. Run: python orchestrator.py approve verify --by <your-name>

Never run approve, reject or reopen. Never begin the next phase.
