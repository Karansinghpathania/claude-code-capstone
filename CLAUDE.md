
# Claude Code Instructions

Python 3.11+, standard library only, tests with `unittest`. Full rules: `docs/CONTRACT.md`.

## Pipeline

- Read `docs/CONTRACT.md` before starting; it is the single source of truth.
- Work only in the phase that is ACTIVE.
- Run `python orchestrator.py status` before any work and confirm your phase is ACTIVE. If it is not, stop and tell the human.

## Requirements

- Ask, never assume.
- If anything in `user_story.md` or an approved artifact is ambiguous, stop and ask the human before continuing.
- Record each answer in your phase artifact with its source.

## Scope

- Write only files your phase owns (see `sdlc/phases.json`).
- Make minimal changes; do not refactor or add features beyond the approved requirements.
- Never create artifacts that belong to later phases.

## Code quality

- Follow PEP 8.
- Add type hints to all function signatures.
- No bare `except:`; catch specific exceptions.
- Standard library only; no third-party packages.

## Security

- Never read, print or commit secrets (tokens, keys, `.env` files).
- No network calls in application code.

## Testing

- Use `unittest` only.
- Run `python -m unittest discover -s tests -v` after every code change.
- Run `python -m compileall -q .` before submitting.

## Traceability

- Requirements use IDs `FR-001`... and `NFR-001`...
- Every later artifact, test and plan item cites the FR-/NFR- ids it covers.

## Human approval

- Never run `approve`, `reject` or `reopen`.
- Never edit anything under `sdlc/`, `hooks/`, `.claude/` or `orchestrator.py`.
- After `python orchestrator.py submit <phase>`, stop and print: "Awaiting human approval. Run: python orchestrator.py approve <phase> --by <your-name>".

## Git

- No force push and no history rewrite.
- Never use `--no-verify`.
- Use conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).

## Auditability

- State only facts you actually observed.
- Paste real command output; do not paraphrase it.
- Never claim a check passed without running it.
