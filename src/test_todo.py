"""
Test script for TODO list functionality.

This script tests:
1. Adding tasks with various property combinations
2. Completing tasks by number and text matching
3. Listing tasks with filters and pagination
4. Getting specific tasks by number
5. Edge cases (empty lists, invalid indices)
6. File persistence and JSON format validation
"""

import sys
import os
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.todo_manager import TodoManager
from src.config.settings import load_settings
from src.tools.registry import ToolRegistry


def print_separator(title=""):
    """Print a visual separator."""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print(f"{'='*60}\n")


def test_todo_manager_basic():
    """Test basic TodoManager functionality."""
    print_separator("TEST 1: Basic TodoManager Functionality")
    
    # Use temporary directory for testing
    test_dir = "./test_todos_temp"
    manager = TodoManager(data_dir=test_dir)
    
    # Test 1: Add simple task
    print("1. Adding simple task...")
    success, msg, task = manager.add_task("Buy milk")
    print(f"   Result: {success} - {msg}")
    assert success, "Failed to add simple task"
    assert task is not None, "Task object is None"
    print(f"   Task ID: {task.id}")
    print(f"   Created at: {task.created_at}")
    
    # Test 2: Add task with priority
    print("\n2. Adding task with high priority...")
    success, msg, task = manager.add_task("Finish report", priority="high")
    print(f"   Result: {success} - {msg}")
    assert success, "Failed to add task with priority"
    assert task.priority == "high", f"Expected 'high', got '{task.priority}'"
    
    # Test 3: Add task with all properties
    print("\n3. Adding task with all properties...")
    success, msg, task = manager.add_task(
        "Call dentist",
        priority="medium",
        due_date="2025-10-20",
        tags=["health", "urgent"]
    )
    print(f"   Result: {success} - {msg}")
    assert success, "Failed to add task with all properties"
    assert len(task.tags) == 2, f"Expected 2 tags, got {len(task.tags)}"
    
    # Test 4: List all tasks
    print("\n4. Listing all tasks...")
    success, msg, tasks, total = manager.list_tasks(count=10)
    print(f"   Total tasks: {total}")
    for i, t in enumerate(tasks, 1):
        print(f"   {i}. {t.description} (priority: {t.priority or 'none'})")
    assert total == 3, f"Expected 3 tasks, got {total}"
    # After sorting by priority: high (Finish report), medium (Call dentist), none (Buy milk)
    assert tasks[0].priority == "high", "First task should be high priority"
    assert tasks[1].priority == "medium", "Second task should be medium priority"
    
    # Test 5: Get specific task (should be sorted by priority now)
    print("\n5. Getting task #2 (should be medium priority task)...")
    success, msg, task = manager.get_task_by_number(2)
    print(f"   Result: {success}")
    print(f"   Task: {task.description if task else 'None'}")
    assert success, "Failed to get task #2"
    assert task.description == "Call dentist", "Task #2 should be 'Call dentist' (medium priority)"
    assert task.priority == "medium", "Task #2 should be medium priority"
    
    # Test 6: Complete task by number (should complete highest priority task)
    print("\n6. Completing task #1 (should be the high priority task)...")
    success, msg, completed_task = manager.complete_task("1")
    print(f"   Result: {success} - {msg}")
    assert success, "Failed to complete task #1"
    assert completed_task.description == "Finish report", "Task #1 should be 'Finish report' (high priority)"
    assert completed_task.completed_at is not None, "No completion timestamp"
    
    # Test 7: List remaining tasks
    print("\n7. Listing remaining tasks...")
    success, msg, tasks, total = manager.list_tasks(count=10)
    print(f"   Total remaining: {total}")
    assert total == 2, f"Expected 2 remaining tasks, got {total}"
    
    # Test 8: Complete task by text
    print("\n8. Completing task by text match ('dentist')...")
    success, msg, completed_task = manager.complete_task("dentist")
    print(f"   Result: {success} - {msg}")
    assert success, "Failed to complete task by text"
    assert completed_task.description == "Call dentist", "Wrong task completed"
    
    # Test 9: Filter by priority (no medium tasks left, they were completed)
    print("\n9. Checking remaining tasks...")
    success, msg, tasks, total = manager.list_tasks()
    print(f"   Remaining tasks: {total}")
    # After completing "Finish report" and "Call dentist", only "Buy milk" remains
    assert total == 1, f"Expected 1 remaining task, got {total}"
    assert tasks[0].description == "Buy milk", "Remaining task should be 'Buy milk'"
    
    # Test 10: Add more tasks to test filtering
    print("\n10. Adding more tasks to test filtering...")
    manager.add_task("Doctor appointment", priority="high", tags=["health"])
    manager.add_task("Gym session", priority="low", tags=["health"])
    
    # Filter by tag
    print("\n11. Filtering by 'health' tag...")
    success, msg, tasks, total = manager.list_tasks(filter_tag="health")
    print(f"   Total tasks with 'health' tag: {total}")
    assert total == 2, f"Expected 2 tasks with 'health' tag, got {total}"
    # Should be sorted by priority: high first, then low
    assert tasks[0].priority == "high", "First health task should be high priority"
    assert tasks[1].priority == "low", "Second health task should be low priority"
    
    # Test 12: Pagination
    print("\n12. Testing pagination (offset=1, count=1)...")
    manager.add_task("Task A")
    manager.add_task("Task B")
    manager.add_task("Task C")
    success, msg, tasks, total = manager.list_tasks(offset=1, count=1)
    print(f"   Total: {total}, Returned: {len(tasks)}")
    assert len(tasks) == 1, f"Expected 1 task, got {len(tasks)}"
    
    # Cleanup
    print("\n13. Cleaning up test directory...")
    shutil.rmtree(test_dir)
    print("   Test directory removed")
    
    print("\n✅ All basic tests passed!")


def test_todo_manager_edge_cases():
    """Test edge cases and error handling."""
    print_separator("TEST 2: Edge Cases & Error Handling")
    
    test_dir = "./test_todos_edge"
    manager = TodoManager(data_dir=test_dir)
    
    # Test 1: List tasks when empty
    print("1. Listing tasks when empty...")
    success, msg, tasks, total = manager.list_tasks()
    print(f"   Total: {total}")
    assert total == 0, f"Expected 0 tasks, got {total}"
    assert len(tasks) == 0, "Task list should be empty"
    
    # Test 2: Get task with invalid number
    print("\n2. Getting task with invalid number (999)...")
    success, msg, task = manager.get_task_by_number(999)
    print(f"   Result: {success} - {msg}")
    assert not success, "Should fail for invalid task number"
    
    # Test 3: Complete non-existent task
    print("\n3. Completing non-existent task...")
    success, msg, task = manager.complete_task("nonexistent")
    print(f"   Result: {success} - {msg}")
    assert not success, "Should fail for non-existent task"
    
    # Test 4: Invalid priority
    print("\n4. Adding task with invalid priority...")
    success, msg, task = manager.add_task("Test task", priority="super-high")
    print(f"   Result: {success}")
    assert success, "Should succeed but ignore invalid priority"
    assert task.priority is None, f"Priority should be None, got {task.priority}"
    
    # Test 5: Empty description
    print("\n5. Testing empty description handling...")
    # This should be caught by the registry, but test manager directly
    success, msg, task = manager.add_task("")
    print(f"   Result: {success}")
    # Manager currently accepts empty strings, registry validates
    
    # Cleanup
    print("\n6. Cleaning up test directory...")
    shutil.rmtree(test_dir)
    print("   Test directory removed")
    
    print("\n✅ All edge case tests passed!")


def test_priority_sorting():
    """Test that tasks are sorted by priority."""
    print_separator("TEST 3: Priority Sorting")
    
    test_dir = "./test_todos_priority"
    manager = TodoManager(data_dir=test_dir)
    
    # Add tasks in random priority order
    print("1. Adding tasks in mixed priority order...")
    manager.add_task("Low priority task", priority="low")
    manager.add_task("High priority task 1", priority="high")
    manager.add_task("Medium priority task", priority="medium")
    manager.add_task("No priority task")
    manager.add_task("High priority task 2", priority="high")
    
    # List tasks and verify order
    print("\n2. Listing tasks to verify priority sorting...")
    success, msg, tasks, total = manager.list_tasks(count=10)
    print(f"   Total tasks: {total}")
    
    priorities_in_order = [t.priority for t in tasks]
    print(f"   Priority order: {priorities_in_order}")
    
    # Expected order: high, high, medium, low, none
    expected_order = ['high', 'high', 'medium', 'low', None]
    assert priorities_in_order == expected_order, f"Expected {expected_order}, got {priorities_in_order}"
    
    # Print task descriptions in sorted order
    for i, task in enumerate(tasks, 1):
        print(f"   {i}. {task.description} (priority: {task.priority or 'none'})")
    
    # Test get_task_by_number uses same sorting
    print("\n3. Testing get_task_by_number uses priority sorting...")
    success, msg, task = manager.get_task_by_number(1)
    print(f"   Task 1: {task.description}")
    assert task.priority == "high", f"First task should be high priority, got {task.priority}"
    assert "High priority task" in task.description, "First task should be a high priority one"
    
    # Test complete_task uses priority sorting
    print("\n4. Testing complete_task with task number (should complete first high priority)...")
    success, msg, completed = manager.complete_task("1")
    assert success, "Failed to complete task"
    print(f"   Completed: {completed.description}")
    
    # Verify the correct high priority task was completed
    success, msg, tasks, total = manager.list_tasks(count=10)
    print(f"   Remaining tasks: {total}")
    print(f"   First task is now: {tasks[0].description}")
    assert total == 4, f"Should have 4 remaining tasks, got {total}"
    assert tasks[0].priority == "high", "First task should still be high priority"
    
    # Cleanup
    print("\n5. Cleaning up test directory...")
    shutil.rmtree(test_dir)
    print("   Test directory removed")
    
    print("\n✅ Priority sorting tests passed!")


def test_obsolete_functionality():
    """Test marking tasks as obsolete."""
    print_separator("TEST 4: Obsolete Task Functionality")
    
    test_dir = "./test_todos_obsolete"
    manager = TodoManager(data_dir=test_dir)
    
    # Add some tasks
    print("1. Adding tasks...")
    manager.add_task("Task to complete", priority="high")
    manager.add_task("Task to make obsolete", priority="medium")
    manager.add_task("Task to keep", priority="low")
    
    success, msg, tasks, total = manager.list_tasks()
    print(f"   Total tasks: {total}")
    assert total == 3, f"Expected 3 tasks, got {total}"
    
    # Mark one as obsolete
    print("\n2. Marking task #2 as obsolete...")
    success, msg, task = manager.mark_task_obsolete("2")
    print(f"   Result: {success} - {msg}")
    assert success, "Failed to mark task as obsolete"
    assert task.description == "Task to make obsolete", "Wrong task marked obsolete"
    
    # Verify it's removed from TODO
    print("\n3. Verifying task removed from TODO list...")
    success, msg, tasks, total = manager.list_tasks()
    print(f"   Remaining tasks: {total}")
    assert total == 2, f"Expected 2 remaining tasks, got {total}"
    
    # Check OBSOLETE file exists and has the task
    print("\n4. Checking OBSOLETE file...")
    obsolete_count = manager.get_obsolete_count()
    print(f"   Obsolete tasks: {obsolete_count}")
    assert obsolete_count == 1, f"Expected 1 obsolete task, got {obsolete_count}"
    
    # Complete one task
    print("\n5. Completing task #1...")
    manager.complete_task("1")
    
    # Check counts
    print("\n6. Verifying final counts...")
    pending = manager.get_task_count()
    completed = manager.get_completed_count()
    obsolete = manager.get_obsolete_count()
    print(f"   Pending: {pending}, Completed: {completed}, Obsolete: {obsolete}")
    assert pending == 1, f"Expected 1 pending, got {pending}"
    assert completed == 1, f"Expected 1 completed, got {completed}"
    assert obsolete == 1, f"Expected 1 obsolete, got {obsolete}"
    
    # Cleanup
    print("\n7. Cleaning up test directory...")
    shutil.rmtree(test_dir)
    print("   Test directory removed")
    
    print("\n✅ Obsolete functionality tests passed!")


def test_tool_registry_integration():
    """Test TODO tools through the ToolRegistry."""
    print_separator("TEST 5: Tool Registry Integration")
    
    print("1. Loading settings...")
    settings = load_settings()
    
    # Override TODO settings for testing
    settings.todo_settings.enabled = True
    settings.todo_settings.data_dir = "./test_todos_registry"
    
    print("2. Initializing ToolRegistry...")
    registry = ToolRegistry(settings)
    
    # Test 1: Add task via tool call
    print("\n3. Testing add_task tool...")
    result = registry.execute_tool_call({
        "tool_name": "add_task",
        "parameters": {
            "description": "Test task from registry",
            "priority": "high"
        }
    })
    print(f"   Success: {result['success']}")
    print(f"   Feedback: {result['feedback']}")
    assert result['success'], "add_task tool failed"
    assert "added" in result['feedback'].lower(), "Unexpected feedback"
    
    # Test 2: Add another task
    print("\n4. Adding second task...")
    result = registry.execute_tool_call({
        "tool_name": "add_task",
        "parameters": {
            "description": "Second task",
            "tags": ["test", "demo"]
        }
    })
    assert result['success'], "Failed to add second task"
    
    # Test 3: List tasks via tool call
    print("\n5. Testing list_tasks tool...")
    result = registry.execute_tool_call({
        "tool_name": "list_tasks",
        "parameters": {"count": 2}
    })
    print(f"   Success: {result['success']}")
    print(f"   Feedback: {result['feedback']}")
    assert result['success'], "list_tasks tool failed"
    assert "2 task" in result['feedback'].lower(), "Should show 2 tasks"
    
    # Test 4: Get specific task via tool call
    print("\n6. Testing get_task tool...")
    result = registry.execute_tool_call({
        "tool_name": "get_task",
        "parameters": {"task_number": 1}
    })
    print(f"   Success: {result['success']}")
    print(f"   Feedback: {result['feedback']}")
    assert result['success'], "get_task tool failed"
    assert "first" in result['feedback'].lower(), "Should say 'First task'"
    
    # Test 5: Complete task via tool call
    print("\n7. Testing complete_task tool...")
    result = registry.execute_tool_call({
        "tool_name": "complete_task",
        "parameters": {"task_identifier": "1"}
    })
    print(f"   Success: {result['success']}")
    print(f"   Feedback: {result['feedback']}")
    assert result['success'], "complete_task tool failed"
    
    # Test 6: List after completion
    print("\n8. Listing tasks after completion...")
    result = registry.execute_tool_call({
        "tool_name": "list_tasks",
        "parameters": {}
    })
    print(f"   Feedback: {result['feedback']}")
    assert "1 task" in result['feedback'].lower(), "Should show 1 task remaining"
    
    # Test 7: Filter by tag
    print("\n9. Testing filter by tag...")
    result = registry.execute_tool_call({
        "tool_name": "list_tasks",
        "parameters": {"filter_tag": "test"}
    })
    print(f"   Feedback: {result['feedback']}")
    assert result['success'], "Filter by tag failed"
    
    # Test 8: Add another task and mark as obsolete
    print("\n10. Adding task to mark as obsolete...")
    result = registry.execute_tool_call({
        "tool_name": "add_task",
        "parameters": {"description": "Task to cancel"}
    })
    assert result['success'], "Failed to add task"
    
    # Test 9: Mark task as obsolete
    print("\n11. Testing obsolete_task tool...")
    result = registry.execute_tool_call({
        "tool_name": "obsolete_task",
        "parameters": {"task_identifier": "cancel"}
    })
    print(f"   Success: {result['success']}")
    print(f"   Feedback: {result['feedback']}")
    assert result['success'], "obsolete_task tool failed"
    assert "obsolete" in result['feedback'].lower(), "Should mention obsolete"
    
    # Cleanup
    print("\n12. Cleaning up test directory...")
    shutil.rmtree("./test_todos_registry")
    print("   Test directory removed")
    
    print("\n✅ All registry integration tests passed!")


def test_file_persistence():
    """Test that tasks persist across manager instances."""
    print_separator("TEST 6: File Persistence")
    
    test_dir = "./test_todos_persist"
    
    # Create manager and add tasks
    print("1. Creating first manager instance and adding tasks...")
    manager1 = TodoManager(data_dir=test_dir)
    manager1.add_task("Persistent task 1", priority="high")
    manager1.add_task("Persistent task 2", tags=["persist"])
    
    # Get task count
    count1 = manager1.get_task_count()
    print(f"   Task count: {count1}")
    
    # Delete manager and create new one
    print("\n2. Creating second manager instance (simulating app restart)...")
    del manager1
    manager2 = TodoManager(data_dir=test_dir)
    
    # Check if tasks persisted
    count2 = manager2.get_task_count()
    print(f"   Task count after restart: {count2}")
    assert count1 == count2, f"Task count mismatch: {count1} vs {count2}"
    
    # List tasks
    print("\n3. Listing persisted tasks...")
    success, msg, tasks, total = manager2.list_tasks()
    for i, task in enumerate(tasks, 1):
        print(f"   {i}. {task.description}")
    assert total == 2, f"Expected 2 tasks, got {total}"
    
    # Complete a task
    print("\n4. Completing a task...")
    manager2.complete_task("1")
    
    # Check DONE file
    print("\n5. Verifying DONE file...")
    completed_count = manager2.get_completed_count()
    print(f"   Completed tasks: {completed_count}")
    assert completed_count == 1, f"Expected 1 completed task, got {completed_count}"
    
    # Cleanup
    print("\n6. Cleaning up test directory...")
    shutil.rmtree(test_dir)
    print("   Test directory removed")
    
    print("\n✅ File persistence tests passed!")


def test_json_format():
    """Test that JSON files are properly formatted."""
    print_separator("TEST 7: JSON Format Validation")
    
    test_dir = "./test_todos_json"
    manager = TodoManager(data_dir=test_dir)
    
    # Add task with all properties
    print("1. Adding task with all properties...")
    manager.add_task(
        "Complete task",
        priority="high",
        due_date="2025-10-20",
        tags=["urgent", "work"]
    )
    
    # Read and verify JSON format
    print("\n2. Reading TODO.json file...")
    import json
    todo_file = Path(test_dir) / "TODO.json"
    with open(todo_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"   File structure: {list(data.keys())}")
    assert "tasks" in data, "Missing 'tasks' key"
    assert isinstance(data["tasks"], list), "'tasks' should be a list"
    assert len(data["tasks"]) == 1, "Should have 1 task"
    
    task_data = data["tasks"][0]
    print(f"\n3. Task structure: {list(task_data.keys())}")
    assert "id" in task_data, "Missing 'id' field"
    assert "description" in task_data, "Missing 'description' field"
    assert "created_at" in task_data, "Missing 'created_at' field"
    assert "priority" in task_data, "Missing 'priority' field"
    assert "due_date" in task_data, "Missing 'due_date' field"
    assert "tags" in task_data, "Missing 'tags' field"
    
    print(f"\n4. Task content:")
    print(f"   Description: {task_data['description']}")
    print(f"   Priority: {task_data['priority']}")
    print(f"   Due date: {task_data['due_date']}")
    print(f"   Tags: {task_data['tags']}")
    
    # Complete task and check DONE format
    print("\n5. Completing task and checking DONE.json...")
    manager.complete_task("1")
    
    done_file = Path(test_dir) / "DONE.json"
    with open(done_file, 'r', encoding='utf-8') as f:
        done_data = json.load(f)
    
    assert len(done_data["tasks"]) == 1, "Should have 1 completed task"
    completed_task = done_data["tasks"][0]
    assert "completed_at" in completed_task, "Missing 'completed_at' field"
    print(f"   Completed at: {completed_task['completed_at']}")
    
    # Cleanup
    print("\n6. Cleaning up test directory...")
    shutil.rmtree(test_dir)
    print("   Test directory removed")
    
    print("\n✅ JSON format validation passed!")


def main():
    """Run all tests."""
    print("="*60)
    print("  TODO LIST FUNCTIONALITY - COMPREHENSIVE TESTS")
    print("="*60)
    
    try:
        # Run all test suites
        test_todo_manager_basic()
        test_todo_manager_edge_cases()
        test_priority_sorting()
        test_obsolete_functionality()
        test_tool_registry_integration()
        test_file_persistence()
        test_json_format()
        
        # Final summary
        print_separator("ALL TESTS COMPLETED")
        print("✅ All test suites passed successfully!")
        print("\nThe TODO list tool is ready for use.")
        print("\nYou can now use voice commands like:")
        print("  - 'Add buy milk to my todo list'")
        print("  - 'What's on my todo list?'")
        print("  - 'Mark first task as done'")
        print("  - 'Mark second task as obsolete'")
        print("  - 'Cancel the report task'")
        print("  - 'Show high priority tasks'")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

