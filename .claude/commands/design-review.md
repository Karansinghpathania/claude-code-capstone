---
name: design-review
description: Kick off phase 3 (design-review). The design-review agent critiques the architecture against requirements.
---

# /design-review Command

## Phase 3: design-review

STEP 1. Run `python orchestrator.py status`. If `design-review` is not
ACTIVE, STOP, tell the human which phase is active, and do nothing else.

## Procedure

1. Read requirements, then architecture.
2. Check coverage: every FR/NFR must map to a component.
3. Challenge decisions: hidden assumptions, over-engineering, error paths.
4. Review security and usability.
5. Rate findings High, Med, or Low; propose changes.
6. Pick verdict: REVISE if any High finding remains, else APPROVE.

## Finish
1. Run `python orchestrator.py submit design-review`. If it refuses, fix the
   artifact and retry.
2. STOP and print exactly:

Awaiting human approval. Run: python orchestrator.py approve design-review --by <your-name>

Never run approve, reject or reopen. Never begin the next phase.
