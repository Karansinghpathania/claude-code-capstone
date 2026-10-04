# Architecture

## Overview
A command-line todo application with persistent JSON storage.

## Components and Responsibilities
- 	odo/__init__.py: Package initialization with version
- 	odo/app.py: Core logic (add, complete, delete, list tasks)
- 	odo/cli.py: Command-line interface and argument parsing

## Data Model
Tasks stored in 	asks.json:
`json
[
  {"id": 1, "description": "Buy groceries", "status": "PENDING"},
  {"id": 2, "description": "Write code", "status": "COMPLETE"}
]
`

## Control Flow
1. CLI parses arguments
2. App loads tasks from JSON
3. Performs requested operation
4. Saves tasks back to JSON
5. Returns success/error message

## Mermaid Diagram
\\\mermaid
graph LR
    CLI["CLI Parser"] --> APP["App Logic"]
    APP --> FS["File System"]
    FS --> JSON["tasks.json"]
    APP --> OUT["Output"]
\\\

## Decisions
- JSON storage (FR-004): Simple, human-readable, standard library only
- Auto-increment IDs (FR-001, FR-002): Sequential integers, stored in JSON
- In-memory list during execution (NFR-005): Comply with stdlib-only constraint

## Requirement Coverage
| Requirement | Component |
|-------------|-----------|
| FR-001 | app.py:add_task() |
| FR-002 | app.py:complete_task() |
| FR-003 | app.py:list_tasks() |
| FR-004 | app.py:load/save_tasks() |
| FR-005 | app.py:delete_task() |
| NFR-001 | Python 3.11+ |
| NFR-002 | unittest in tests/ |
| NFR-003 | PEP 8 compliance |
| NFR-004 | Type hints on all functions |
| NFR-005 | Stdlib only |
