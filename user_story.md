# User Story: Todo List

As a user, I want to manage a simple list of tasks from the command line so that I can keep track of what I need to do.

## Acceptance Criteria

### Create a task
- Given I provide a task title, when I add it, then a new task is created with a unique id and the status "open".
- The new task is shown to me with its id, title and status.

### View tasks
- Given tasks exist, when I list them, then I see every task, in the order created, with its id, title and status.
- Given no tasks exist, when I list them, then I see a message saying the list is empty.

### Complete a task
- Given an open task, when I complete it by id, then its status becomes "done".
- Given a task that is already done, when I complete it, then I see a message saying it is already done and nothing changes.
- Given an id that does not exist, when I complete it, then I see a clear error and nothing changes.

### Reopen a task
- Given a done task, when I reopen it by id, then its status becomes "open".
- Given a task that is already open, when I reopen it, then I see a message saying it is already open and nothing changes.
- Given an id that does not exist, when I reopen it, then I see a clear error and nothing changes.

### Delete a task
- Given an existing task, when I delete it by id, then it no longer appears in the list.
- Given an id that does not exist, when I delete it, then I see a clear error and nothing changes.

## Notes
- The tool is a small Python command-line application.
- Task titles are free text entered by the user.
