---
name: requirements
description: How to turn a user story into testable FR-001/NFR-001 requirements, find ambiguities, ask the human, and fill the requirements artifact template. Use when the requirements agent writes artifacts/requirements.md.
user-invocable: false
---

# Skill: requirements (HOW)

The **requirements command** decides who works and what it may touch. This
skill is the reusable method and template. It does not repeat the command's
rules about files, `status` and `submit`.

## Procedure
1. Read the story once for intent, once sentence by sentence. Number every
   sentence that states behaviour, a limit, or a constraint.
2. Turn each behaviour into one functional requirement `FR-001`, `FR-002`,
   ... one statement each, written as "The system shall ...". Split
   sentences that contain "and" if the parts can fail separately.
3. Give every FR acceptance criteria in Given/When/Then form with concrete
   values, so a unit test can be written without further questions.
4. Collect quality needs as `NFR-001`, ... : runtime and language
   (Python 3.11+, standard library only), error handling, performance,
   usability, data safety. Each needs a measurable criterion.
5. List constraints (from the story and `docs/CONTRACT.md`), kept apart from
   requirements.
6. Walk the ambiguity checklist below for EVERY FR. Each unanswered item is
   a question for the human.
7. Run the question protocol. Only then write the artifact.
8. Ids are three digits, unique, never reused or renumbered after approval.

## Ambiguity checklist
- Empty or whitespace-only input; very long input; special characters.
- Duplicates: allowed, rejected, or merged? Case sensitivity?
- Persistence: is data kept between runs? Where, in what format, what if
  the file is missing, empty or corrupt?
- Limits: maximum count, length, size; what happens at the limit.
- Ordering: of creation, of listing, after deletion; stable ids or indexes?
- Concurrency: two runs at once; partial writes.
- Errors: unknown id, bad arguments; message text, exit codes.
- Output format: exact wording, columns, empty-state message, encoding.
- Anything the story says "etc.", "should", "usually", "fast" about.

## Question protocol
1. Collect all questions first; number them `1.`, `2.`, ... Each is
   answerable in one line, offers the likely options, and names the FR it
   affects.
2. Ask in chat in a single message, then STOP and wait. Never fill a gap
   with your own assumption, and never write a provisional answer.
3. Record each as `- [x] Q: <question> A: <answer> (source: human, <date>)`
   and update the affected requirements. If new ambiguity appears, ask again.

## Artifact template
```
# Requirements
## Source
user_story.md: <quote or summary with line references>
## Functional Requirements
- FR-001: The system shall <behaviour>.
  - Acceptance: Given <state>, when <action>, then <observable result>.
## Non-Functional Requirements
- NFR-001: <quality> measured by <criterion>.
## Constraints
- <constraint> (source: user_story.md | CONTRACT.md)
## Assumptions
- <human-confirmed assumption> or None
## Open Questions
- [x] Q: <question> A: <answer>
```
Use `None` under Open Questions when nothing was ambiguous. Never leave a
`- [ ]` item.

## Validation checklist
- [ ] Each FR is one testable statement with concrete acceptance criteria.
- [ ] Every checklist item was considered for every FR.
- [ ] Every question has a recorded human answer; no `- [ ]` remains.
- [ ] Nothing in Assumptions lacks human confirmation.
- [ ] No design, class names, file names or libraries beyond constraints.
- [ ] Ids unique, three digits; all six headings present.

## Stop condition
Finished when the checklist is all ticked. Execute the self-check and submit.
This skill never approves or starts the next phase.
