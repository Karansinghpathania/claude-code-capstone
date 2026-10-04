---
name: requirements
description: Kick off phase 1 (requirements). Ask the human clarifying questions, then write artifacts/requirements.md with FR-/NFR- requirements.
---

# /requirements Command

## Phase 1: requirements

STEP 1. Run `python orchestrator.py status`. If `requirements` is not
ACTIVE, STOP, tell the human which phase is active, and do nothing else.

## Procedure

Follow `.claude/skills/requirements/SKILL.md` for the detailed method:

1. Read `user_story.md` completely.
2. Extract functional requirements `FR-001`, `FR-002`, ... Each is one
   testable statement ("The system shall ...") with acceptance criteria that
   a test could verify.
3. Extract non-functional requirements `NFR-001`, ... (for example Python
   3.11+, standard library only, performance, error handling, usability,
   data safety), using the contract and the story, never your own preferences.
4. List constraints (from the story and `docs/CONTRACT.md`).
5. Detect ambiguities: vague words, missing limits, undefined behaviour on
   bad input, conflicting statements, unstated defaults.
6. **For each ambiguity ask the human a numbered clarifying question in chat
   and STOP and wait.** Do not guess and do not write a provisional answer.
7. After the human answers, record the question and the answer verbatim in
   `## Open Questions`, and reflect the answer in the affected requirements.
8. Write the artifact. Only assumptions the human confirmed may appear.

## Required artifact structure
```
# Requirements
## Source              (user_story.md, with any quoted lines)
## Functional Requirements   (FR-### + acceptance criteria)
## Non-Functional Requirements   (NFR-###)
## Constraints
## Assumptions         (only human-confirmed ones; else "None")
## Open Questions      (each as "- [x] Q: ... A: ..." or "None")
```
The Open Questions section must contain no `- [ ]` item. Ids are three
digits, unique, and never reused.

## Self-check before submit
- Every FR/NFR is testable and has a unique id.
- At least one `FR-###` exists; the six headings above all exist.
- `## Open Questions` has no `- [ ]`; every question has the human's answer.
- No requirement contradicts `user_story.md` or `docs/CONTRACT.md`.
- No design, class, file or library choices leaked into requirements.

## Approval gate
Run `python orchestrator.py submit requirements`. If it refuses, read the
message, fix the artifact and retry. Once accepted, STOP and print exactly:

Awaiting human approval. Run: python orchestrator.py approve requirements --by <your-name>

Never run approve, reject or reopen. Never begin the next phase.
