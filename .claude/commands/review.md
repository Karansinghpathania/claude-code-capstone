---
name: review
description: Kick off phase 6 (review). The code reviewer agent judges the implementation.
---

# /review Command

## Phase 6: review

STEP 1. Run `python orchestrator.py status`. If `review` is not
ACTIVE, STOP, tell the human which phase is active, and do nothing else.

## Procedure

1. Read requirements, architecture and plan.
2. Read all code and tests. Run compileall and unittest.
3. Check correctness, coverage, edge cases, error handling, type hints, PEP 8.
4. Build traceability matrix: every FR/NFR -> code location -> test.
5. Compare with plan: mark each task done, not done, or deviated.
6. Rate findings Blocker, Major, Minor or Nit with file:line locations.

## Finish
1. Run `python orchestrator.py submit review`. If it refuses, fix the artifact
   and retry.
2. STOP and print exactly:

Awaiting human approval. Run: python orchestrator.py approve review --by <your-name>

Never run approve, reject or reopen. Never begin the next phase.
