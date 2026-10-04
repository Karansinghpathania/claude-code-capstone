# Changelog
All notable changes to this project are documented in this file.
The format is based on Keep a Changelog (https://keepachangelog.com).

## [Unreleased]
### Added
- Command-line todo list: `python -m todo.cli add|list|complete|reopen|delete`, with tasks stored in `tasks.json` in the current folder (FR-001..FR-014).
- Task ids are unique and never reused, including after delete and across runs.
- Usage text on stderr with exit code 2 for usage errors; `-h` and `--help` print usage with exit code 0.
- Plain-language `Error:` messages on stderr with exit code 1; a corrupt `tasks.json` (including one with a UTF-8 BOM) is reported and left unchanged.
- Atomic saves and UTF-8 storage so Unicode titles round trip.
- Unit tests (`tests/test_todo.py`) covering every requirement.

### Changed
- Titles containing control characters (tab, newline, escape and similar) are rejected like an empty title (design-review R-1, extends FR-002).
- Loading `tasks.json` is strict: boolean ids and empty stored titles count as corrupt.
- Encoding errors on save or output give a plain error and exit 1 instead of a traceback.

### Fixed
- Nothing fixed; this is a new feature.
