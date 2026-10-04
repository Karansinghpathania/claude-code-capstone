"""Todo app core logic."""

from typing import List, Dict, Any
import json
import os

TASKS_FILE = "tasks.json"

def load_tasks() -> List[Dict[str, Any]]:
    """Load tasks from JSON file."""
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE) as f:
            return json.load(f)
    return []

def save_tasks(tasks: List[Dict[str, Any]]) -> None:
    """Save tasks to JSON file."""
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)

def add_task(description: str) -> Dict[str, Any]:
    """Add a new task (FR-001)."""
    tasks = load_tasks()
    task_id = max([t["id"] for t in tasks], default=0) + 1
    task = {"id": task_id, "description": description, "status": "PENDING"}
    tasks.append(task)
    save_tasks(tasks)
    return task

def complete_task(task_id: int) -> bool:
    """Mark task as complete (FR-002)."""
    tasks = load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            task["status"] = "COMPLETE"
            save_tasks(tasks)
            return True
    return False

def delete_task(task_id: int) -> bool:
    """Delete a task (FR-005)."""
    tasks = load_tasks()
    tasks = [t for t in tasks if t["id"] != task_id]
    save_tasks(tasks)
    return True

def list_tasks() -> List[Dict[str, Any]]:
    """List all tasks (FR-003)."""
    return load_tasks()
