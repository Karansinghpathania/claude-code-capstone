---
name: implementation
description: Kick off phase 5 (implementation). The implementation agent executes the approved plan.
---

# /implementation Command

## Phase 5: implementation

STEP 1. Run `python orchestrator.py status`. If `implementation` is not
ACTIVE, STOP, tell the human which phase is active, and do nothing else.

## Procedure

1. Read plan, architecture and requirements.
2. Do tasks T-01, T-02, ... in order. Stay inside the plan.
3. Code rules: Python 3.11+, stdlib only, type hints, PEP 8, specific exceptions.
4. Tests: unittest only in tests/test_todo.py. Cover every FR.
5. After each task run `python -m compileall -q .` and unittest.
6. Ensure all four files are non-empty.

## Finish
1. Summarize which tasks were completed in a table.
2. Run `python orchestrator.py submit implementation`. If it refuses, fix the
   files and retry.
3. STOP and print exactly:

Awaiting human approval. Run: python orchestrator.py approve implementation --by <your-name>

Never run approve, reject or reopen. Never begin the next phase.
