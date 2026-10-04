# Requirements

## Source
user_story.md: Build a command-line todo list application that allows users to add, complete, and list tasks with persistent storage.

## Functional Requirements
- FR-001: The system shall allow users to add new tasks with a description.
  - Acceptance: Given an empty todo list, when user runs 'todo add "Buy groceries"', then a task is created with that description.
- FR-002: The system shall allow users to mark tasks as complete.
  - Acceptance: Given an existing task, when user runs 'todo complete <task-id>', then the task status changes to COMPLETE.
- FR-003: The system shall allow users to list all tasks.
  - Acceptance: Given tasks in the list, when user runs 'todo list', then all tasks are displayed with their IDs and status.
- FR-004: The system shall persist tasks to disk.
  - Acceptance: Given completed tasks, when the program exits and restarts, then all tasks are still present.
- FR-005: The system shall allow users to delete tasks.
  - Acceptance: Given a task, when user runs 'todo delete <task-id>', then the task is removed from the list.

## Non-Functional Requirements
- NFR-001: Python 3.11+ required, standard library only.
- NFR-002: Use unittest for all tests.
- NFR-003: Follow PEP 8 style guide.
- NFR-004: All functions must have type hints.
- NFR-005: No third-party packages allowed.

## Constraints
- Must use only Python standard library (no external packages)
- Must use unittest for testing
- Must follow PEP 8
- Must use Python 3.11+
- Must store tasks persistently

## Assumptions
- Tasks are stored in a JSON file in the current directory
- Task IDs are auto-incremented integers
- Tasks have: id, description, status (PENDING/COMPLETE)

## Open Questions
- [x] Q: Should completed tasks be deleted or just marked? A: Marked as complete, not deleted (user clarified)
- [x] Q: Should task IDs be persistent across runs? A: Yes, auto-increment from highest ID (user clarified)
- [x] Q: What format for task storage? A: JSON file tasks.json (user clarified)
