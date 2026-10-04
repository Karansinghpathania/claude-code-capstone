---
name: verify
description: How to turn every FR/NFR into a concrete runnable check, capture real command output as evidence, fill the PASS/FAIL table, and report failures honestly. Use when the verify agent writes artifacts/verify.md.
user-invocable: false
---

# Skill: verify (HOW)

The **verify agent** owns the phase, its file scope and the submit gate.
This skill is the method and the template for turning requirements into
evidence.

## Procedure
1. List every FR and NFR id from `artifacts/requirements.md`.
2. Choose ONE check per id, in this order of preference:
   a. a named unit test (`python -m unittest tests.test_todo.<Class>.<test>`),
   b. a CLI command with a stated expected output or exit code,
   c. a manual command (for example `python --version`, a grep for an
      import or a bare `except:` in the code).
   Use the implementation plan's test plan as the source of candidates.
3. Write the expected result BEFORE running the check.
4. Run the command now, in this session. Use temporary paths for anything
   that writes data. Copy the real output unedited into a fenced block.
5. Compare with the expectation; mark PASS or FAIL. A check that could not
   run is FAIL, with the reason.
6. Run the whole suite once more (`python -m unittest discover -s tests -v`,
   `python -m compileall -q .`) and include that output.
7. Fill in the results table, failures and overall result.

## Evidence rules
- Paste real output only. Never invent, shorten from memory, or "clean up"
  output; trimming is allowed only if marked with `[... trimmed ...]`.
- Output must come from a command run in this session; earlier runs by
  another agent do not count.
- Exit codes matter: show them (`$LASTEXITCODE` or `echo $?`).
- One requirement may need several commands; one command may cover several
  ids, but each id still gets its own row.
- Do not rerun until it passes. The first honest result is the result.

## Failure handling
- Mark FAIL, quote the real error, and name the id.
- Do not fix code, edit tests or loosen the expected result.
- Still submit; the human decides. Overall result is `Result: FAIL`.
- `Result: PASS` is allowed only when every row is PASS.

## Artifact template
````
# Verification
## Environment
```
<output of python --version>
```
## Checks
### FR-001
- Command: `<command>`
- Expected: <expected result>
```
<real output>
```
- Result: PASS | FAIL
## Results table
| id | check | PASS/FAIL |
|----|-------|-----------|
| FR-001 | <test name or command> | PASS |
## Failures and notes
<None, or each failure with id, error, and stray files from git status>
Result: PASS
````

## Validation checklist
- [ ] Every FR/NFR id has a check, a real output block and a verdict.
- [ ] Each output block came from a command run in this session.
- [ ] Table rows match the check sections; `Result:` matches the table.
- [ ] `git status --short` showed no stray files, or they are reported.
- [ ] No code or other file was changed.

## Stop condition
Finished when the checklist is all ticked. Hand control back to the verify
agent to submit (even on FAIL), then STOP for human approval. This skill
never fixes code, approves, or starts the next phase.
