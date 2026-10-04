---
name: architecture
description: Kick off phase 2 (architecture). The architecture agent designs the solution from approved requirements.
---

# /architecture Command

## Phase 2: architecture

STEP 1. Run `python orchestrator.py status`. If `architecture` is not
ACTIVE, STOP, tell the human which phase is active, and do nothing else.

## Procedure

1. Read the requirements; list every FR and NFR id you must cover.
2. If a requirement is too vague to design against, ask the human a numbered
   question in chat and STOP and wait. Do not assume. Record the answer.
3. Design modules, data model, control/data flow, error handling.
4. Produce artifacts/architecture.md with all required sections.

## Finish
1. Run `python orchestrator.py submit architecture`. If it refuses, fix the
   artifact and retry.
2. STOP and print exactly:

Awaiting human approval. Run: python orchestrator.py approve architecture --by <your-name>

Never run approve, reject or reopen. Never begin the next phase.
