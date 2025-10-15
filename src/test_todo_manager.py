#!/usr/bin/env python3
"""
Test script for TodoManager functionality.
Moved from todo_manager.py for better separation of concerns.
"""

import sys
import os
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.todo_manager import TodoManager, TaskNotFoundError


def test_basic_functionality():
    """Test basic TODO manager operations."""
    test_dir = "./test_todos"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    try:
        manager = TodoManager(data_dir=test_dir)

        print("=== Adding tasks ===")
        success, msg, task = manager.add_task("Buy milk", priority="high", tags=["shopping"])
        print(f"Add task 1: {success} - {msg}")

        success, msg, task = manager.add_task("Call dentist", priority="medium", due_date="2025-10-20")
        print(f"Add task 2: {success} - {msg}")

        success, msg, task = manager.add_task("Finish report", priority="high", due_date="2025-10-15")
        print(f"Add task 3: {success} - {msg}")

        print("\n=== Listing tasks ===")
        success, msg, tasks, total = manager.list_tasks()
        print(f"Total tasks: {total}")
        for i, task in enumerate(tasks, 1):
            print(f"{i}. {task.description} (priority: {task.priority or 'none'})")

        print("\n=== Get specific task ===")
        success, msg, task = manager.get_task_by_number(2)
        print(f"Task 2: {task.description if task else 'Not found'}")

        print("\n=== Complete task ===")
        success, msg, task = manager.complete_task("1")
        print(f"Complete task 1: {success} - {msg}")

        print("\n=== Listing remaining tasks ===")
        success, msg, tasks, total = manager.list_tasks()
        print(f"Remaining tasks: {total}")
        for i, task in enumerate(tasks, 1):
            print(f"{i}. {task.description}")

        print("\n=== Filter by priority ===")
        success, msg, tasks, total = manager.list_tasks(filter_priority="high")
        print(f"High priority tasks: {total}")
        for i, task in enumerate(tasks, 1):
            print(f"{i}. {task.description}")

        print("\n=== Health check ===")
        success, msg = manager.health_check()
        print(f"Health check: {success} - {msg}")

        print("\n✅ Basic functionality test passed!")

    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


def test_text_search():
    """Test text search functionality."""
    test_dir = "./test_search"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    try:
        manager = TodoManager(data_dir=test_dir)

        # Add test tasks
        manager.add_task("Call Donna about the project", priority="high")
        manager.add_task("Buy milk from store", priority="medium")
        manager.add_task("Email Donna with updates", priority="low")

        print("=== Text search tests ===")

        # Test search for "donna"
        success, msg, tasks, total = manager.list_tasks(filter_text="donna")
        print(f"Search 'donna': {total} tasks found")
        for task in tasks:
            print(f"  - {task.description}")

        # Test search for "milk"
        success, msg, tasks, total = manager.list_tasks(filter_text="milk")
        print(f"Search 'milk': {total} tasks found")
        for task in tasks:
            print(f"  - {task.description}")

        # Test case insensitive
        success, msg, tasks, total = manager.list_tasks(filter_text="DONNA")
        print(f"Search 'DONNA' (uppercase): {total} tasks found")

        print("\n✅ Text search test passed!")

    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


def test_error_handling():
    """Test error handling."""
    test_dir = "./test_errors"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    try:
        manager = TodoManager(data_dir=test_dir)

        print("=== Error handling tests ===")

        # Test invalid priority
        success, msg, task = manager.add_task("Test task", priority="invalid")
        print(f"Invalid priority: {success} - {msg}")

        # Test empty description
        success, msg, task = manager.add_task("")
        print(f"Empty description: {success} - {msg}")

        # Test invalid task number
        success, msg, task = manager.get_task_by_number(999)
        print(f"Invalid task number: {success} - {msg}")

        # Test non-existent task
        success, msg, task = manager.complete_task("nonexistent")
        print(f"Complete nonexistent task: {success} - {msg}")

        # Test invalid count
        success, msg, tasks, total = manager.list_tasks(count=0)
        print(f"Invalid count: {success} - {msg}")

        success, msg, tasks, total = manager.list_tasks(count=1000)
        print(f"Count too high: {success} - {msg}")

        print("\n✅ Error handling test passed!")

    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


def main():
    """Run all tests."""
    print("🧪 Running TodoManager tests...\n")

    test_basic_functionality()
    print()
    test_text_search()
    print()
    test_error_handling()

    print("\n🎉 All tests passed successfully!")


if __name__ == "__main__":
    main()
