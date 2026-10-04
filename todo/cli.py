"""CLI interface."""

import sys
from todo import app

def main() -> None:
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: todo [add|complete|delete|list] [args]")
        return
    
    command = sys.argv[1]
    
    if command == "add" and len(sys.argv) > 2:
        task = app.add_task(sys.argv[2])
        print(f"Added: {task}")
    elif command == "complete" and len(sys.argv) > 2:
        if app.complete_task(int(sys.argv[2])):
            print("Task completed")
        else:
            print("Task not found")
    elif command == "delete" and len(sys.argv) > 2:
        app.delete_task(int(sys.argv[2]))
        print("Task deleted")
    elif command == "list":
        for task in app.list_tasks():
            print(f"[{task['id']}] {task['description']} ({task['status']})")

if __name__ == "__main__":
    main()
