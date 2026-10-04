"""Tests for todo app."""

import unittest
import os
import json
from todo import app

class TestTodoApp(unittest.TestCase):
    """Test cases for todo application (covers all FRs)."""
    
    def setUp(self) -> None:
        """Setup test fixtures."""
        self.test_file = app.TASKS_FILE
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
    
    def tearDown(self) -> None:
        """Cleanup test files."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
    
    def test_add_task(self) -> None:
        """Test adding task (FR-001)."""
        task = app.add_task("Test task")
        self.assertEqual(task["description"], "Test task")
        self.assertEqual(task["status"], "PENDING")
    
    def test_complete_task(self) -> None:
        """Test completing task (FR-002)."""
        task = app.add_task("Complete me")
        self.assertTrue(app.complete_task(task["id"]))
        tasks = app.list_tasks()
        self.assertEqual(tasks[0]["status"], "COMPLETE")
    
    def test_list_tasks(self) -> None:
        """Test listing tasks (FR-003)."""
        app.add_task("Task 1")
        app.add_task("Task 2")
        tasks = app.list_tasks()
        self.assertEqual(len(tasks), 2)
    
    def test_persistence(self) -> None:
        """Test task persistence (FR-004)."""
        app.add_task("Persist me")
        with open(app.TASKS_FILE) as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
    
    def test_delete_task(self) -> None:
        """Test deleting task (FR-005)."""
        task = app.add_task("Delete me")
        app.delete_task(task["id"])
        tasks = app.list_tasks()
        self.assertEqual(len(tasks), 0)

if __name__ == "__main__":
    unittest.main()
