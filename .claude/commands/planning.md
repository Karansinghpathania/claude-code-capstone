---
name: planning
description: Kick off phase 4 (planning). The planning agent turns approved design into an ordered implementation plan.
---

# /planning Command

## Phase 4: planning

STEP 1. Run `python orchestrator.py status`. If `planning` is not
ACTIVE, STOP, tell the human which phase is active, and do nothing else.

## Procedure

1. Read all three artifacts: requirements, architecture, design review.
2. If verdict was REVISE or High findings remain, ask human which to incorporate.
3. Order tasks so each is small, buildable, and testable.
4. For each task: goal, files touched, FR/NFR ids, done-when.
5. Make test plan: each FR/NFR -> test name or manual check command.
6. Write rollback notes: how to undo each task safely.

## Finish
1. Run `python orchestrator.py submit planning`. If it refuses, fix the
   artifact and retry.
2. STOP and print exactly:

Awaiting human approval. Run: python orchestrator.py approve planning --by <your-name>

Never run approve, reject or reopen. Never begin the next phase.
