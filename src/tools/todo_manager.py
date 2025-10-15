"""
TODO List Manager

This module handles task management including:
1. Adding tasks with optional properties (priority, due_date, tags)
2. Completing tasks (moving from TODO to DONE with timestamp)
3. Listing tasks with filters
4. Getting specific tasks by number
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from ..utils.logger import app_logger


class TaskNotFoundError(Exception):
    """Raised when a task cannot be found."""
    pass


class InvalidTaskIdentifierError(Exception):
    """Raised when task identifier is invalid."""
    pass


class Task:
    """Represents a single task with optional properties."""

    def __init__(
        self,
        description: str,
        task_id: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_at: Optional[str] = None,
        completed_at: Optional[str] = None
    ):
        self.id = task_id or str(uuid.uuid4())
        self.description = description
        self.priority = priority  # high, medium, low, or None
        self.due_date = due_date
        self.tags = tags or []
        self.created_at = created_at or datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        self.completed_at = completed_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for JSON storage."""
        task_dict = {
            "id": self.id,
            "description": self.description,
            "created_at": self.created_at
        }

        # Add optional fields only if they have values
        if self.priority:
            task_dict["priority"] = self.priority
        if self.due_date:
            task_dict["due_date"] = self.due_date
        if self.tags:
            task_dict["tags"] = self.tags
        if self.completed_at:
            task_dict["completed_at"] = self.completed_at

        return task_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary loaded from JSON."""
        return cls(
            description=data["description"],
            task_id=data.get("id"),
            priority=data.get("priority"),
            due_date=data.get("due_date"),
            tags=data.get("tags"),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at")
        )


class TodoManager:
    """Manager for TODO list operations with JSON file storage."""

    # Configuration constants
    PRIORITY_ORDER = {'high': 0, 'medium': 1, 'low': 2, None: 3}
    VALID_PRIORITIES = {'high', 'medium', 'low'}
    DEFAULT_COUNT = 10
    MAX_COUNT = 100  # Prevent excessive memory usage
    CACHE_TTL_SECONDS = 5  # Cache time-to-live
    
    def __init__(self, data_dir: str = "./data/todos"):
        """
        Initialize the TODO manager.

        Args:
            data_dir: Directory to store TODO.json, DONE.json, and OBSOLETE.json files
        """
        self.data_dir = Path(data_dir)
        self.todo_file = self.data_dir / "TODO.json"
        self.done_file = self.data_dir / "DONE.json"
        self.obsolete_file = self.data_dir / "OBSOLETE.json"

        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize files if they don't exist
        self._init_files()

        # Initialize caches for performance
        self._todo_cache: Optional[Dict[str, Any]] = None
        self._done_cache: Optional[Dict[str, Any]] = None
        self._obsolete_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cached_tasks: Optional[List[Task]] = None

        app_logger.info(f"TodoManager initialized with data directory: {self.data_dir}")
    
    def _init_files(self):
        """Initialize TODO, DONE, and OBSOLETE files if they don't exist."""
        for file_path in [self.todo_file, self.done_file, self.obsolete_file]:
            if not file_path.exists():
                self._write_file(file_path, {"tasks": []})
                app_logger.info(f"Created TODO file: {file_path}")

    def _get_fresh_todo_data(self) -> Dict[str, Any]:
        """Get fresh TODO data, using cache if valid."""
        now = datetime.now()
        if (self._todo_cache and self._cache_timestamp and
            (now - self._cache_timestamp).seconds < self.CACHE_TTL_SECONDS):
            return self._todo_cache

        self._todo_cache = self._read_file(self.todo_file)
        self._cache_timestamp = now
        return self._todo_cache

    def _get_tasks_from_cache(self) -> List[Task]:
        """Get tasks with lazy loading."""
        if not self._cached_tasks:
            data = self._get_fresh_todo_data()
            self._cached_tasks = [Task.from_dict(t) for t in data["tasks"]]
        return self._cached_tasks

    def _find_task_by_identifier(self, task_identifier: str, tasks: List[Task]) -> Tuple[Optional[Task], Optional[int]]:
        """
        Find a task by number or description match.

        Args:
            task_identifier: Task number (1-based) or partial description
            tasks: List of tasks to search in

        Returns:
            Tuple of (task, original_index_in_unsorted_list)
        """
        # Try to parse as number first (1-based index)
        try:
            task_num = int(task_identifier)
            # Sort tasks by priority to match list_tasks behavior
            sorted_tasks = sorted(tasks, key=lambda t: self.PRIORITY_ORDER.get(t.priority, 3))

            if 1 <= task_num <= len(sorted_tasks):
                task_to_find = sorted_tasks[task_num - 1]
                # Find the original index in the unsorted list
                original_index = tasks.index(task_to_find)
                return task_to_find, original_index
        except ValueError:
            pass

        # Search by partial description match
        identifier_lower = task_identifier.lower()
        for idx, task in enumerate(tasks):
            if identifier_lower in task.description.lower():
                return task, idx

        return None, None
    
    def _read_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Read and parse a JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Dictionary with tasks data
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            app_logger.error(f"Error parsing JSON from {file_path}: {e}")
            return {"tasks": []}
        except Exception as e:
            app_logger.error(f"Error reading file {file_path}: {e}")
            return {"tasks": []}
    
    def _write_file(self, file_path: Path, data: Dict[str, Any]):
        """
        Write data to a JSON file atomically.
        
        Args:
            file_path: Path to the JSON file
            data: Dictionary to write
        """
        try:
            # Write to temporary file first
            temp_file = file_path.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_file.replace(file_path)
            app_logger.debug(f"Successfully wrote to {file_path}")
        except Exception as e:
            app_logger.error(f"Error writing to {file_path}: {e}")
            raise
    
    def add_task(
        self,
        description: str,
        priority: Optional[str] = None,
        due_date: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[bool, str, Optional[Task]]:
        """
        Add a new task to the TODO list.

        Args:
            description: Task description (required)
            priority: Task priority (high, medium, low, or None)
            due_date: Due date in any reasonable format
            tags: List of tags for the task

        Returns:
            Tuple of (success, message, task)
        """
        try:
            # Validate description
            if not description or not description.strip():
                return False, "Task description cannot be empty", None

            # Validate and normalize priority
            if priority:
                priority = priority.lower().strip()
                if priority not in self.VALID_PRIORITIES:
                    app_logger.warning(f"Invalid priority '{priority}', setting to None")
                    priority = None

            # Create new task
            task = Task(
                description=description,
                priority=priority,
                due_date=due_date,
                tags=tags
            )

            # Read current TODO list and add new task
            data = self._get_fresh_todo_data()
            data["tasks"].append(task.to_dict())

            # Write back to file
            self._write_file(self.todo_file, data)

            # Clear all caches since we modified data
            self._cached_tasks = None
            self._todo_cache = None
            self._cache_timestamp = None

            app_logger.info(f"Added task: {description} (priority: {priority or 'none'})")
            return True, "Task added successfully", task

        except Exception as e:
            app_logger.error(f"Error adding task: {e}", exc_info=True)
            return False, f"Error adding task: {str(e)}", None
    
    def complete_task(self, task_identifier: str) -> Tuple[bool, str, Optional[Task]]:
        """
        Complete a task by moving it from TODO to DONE. Tasks are sorted by priority when using numbers.

        Args:
            task_identifier: Task number (1-based, from priority-sorted list) or partial description

        Returns:
            Tuple of (success, message, completed_task)
        """
        try:
            todo_data = self._get_fresh_todo_data()
            tasks = self._get_tasks_from_cache()

            if not tasks:
                return False, "No tasks to complete", None

            # Use helper method to find task
            task_to_complete, original_index = self._find_task_by_identifier(task_identifier, tasks)

            if task_to_complete is None:
                raise TaskNotFoundError(f"Task '{task_identifier}' not found")

            # Move task to done list
            return self._move_task_to_done(todo_data, task_to_complete, original_index)

        except TaskNotFoundError as e:
            return False, str(e), None
        except Exception as e:
            app_logger.error(f"Error completing task: {e}", exc_info=True)
            return False, f"Error completing task: {str(e)}", None

    def _move_task_to_done(self, todo_data: Dict, task: Task, original_index: int) -> Tuple[bool, str, Task]:
        """Move a task from TODO to DONE list."""
        # Mark as completed
        task.completed_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        # Remove from TODO (using original index from unsorted list)
        todo_data["tasks"].pop(original_index)
        self._write_file(self.todo_file, todo_data)

        # Clear all caches since we modified data
        self._cached_tasks = None
        self._todo_cache = None
        self._cache_timestamp = None

        # Add to DONE
        done_data = self._read_file(self.done_file)
        done_data["tasks"].append(task.to_dict())
        self._write_file(self.done_file, done_data)

        app_logger.info(f"Completed task: {task.description}")
        return True, "Task completed successfully", task
    
    def list_tasks(
        self,
        filter_priority: Optional[str] = None,
        filter_tag: Optional[str] = None,
        filter_text: Optional[str] = None,
        count: int = DEFAULT_COUNT,
        offset: int = 0
    ) -> Tuple[bool, str, List[Task], int]:
        """
        List tasks with optional filters. Tasks are sorted by priority (high, medium, low, none).

        Args:
            filter_priority: Filter by priority (high, medium, low)
            filter_tag: Filter by tag
            filter_text: Filter by text content in task description (case-insensitive)
            count: Maximum number of tasks to return (default: 10)
            offset: Number of tasks to skip (for pagination)

        Returns:
            Tuple of (success, message, tasks, total_count)
        """
        try:
            # Validate count parameter
            if count < 1 or count > self.MAX_COUNT:
                return False, f"Count must be between 1 and {self.MAX_COUNT}", [], 0

            if offset < 0:
                return False, "Offset cannot be negative", [], 0

            # Get tasks from cache
            tasks = self._get_tasks_from_cache()

            # Apply filters
            if filter_priority:
                filter_priority = filter_priority.lower()
                if filter_priority not in self.VALID_PRIORITIES:
                    return False, f"Invalid priority filter: {filter_priority}", [], 0
                tasks = [t for t in tasks if t.priority == filter_priority]

            if filter_tag:
                filter_tag_lower = filter_tag.lower()
                tasks = [t for t in tasks if
                        (filter_tag_lower in [tag.lower() for tag in t.tags]) or
                        (filter_tag_lower in t.description.lower())]

            if filter_text:
                filter_text_lower = filter_text.lower()
                tasks = [t for t in tasks if filter_text_lower in t.description.lower()]

            # Sort by priority: high -> medium -> low -> none
            tasks.sort(key=lambda t: self.PRIORITY_ORDER.get(t.priority, 3))

            total_count = len(tasks)

            # Apply pagination
            tasks = tasks[offset:offset + count]

            app_logger.info(f"Listed {len(tasks)} tasks (total: {total_count})")
            return True, "Tasks retrieved successfully", tasks, total_count

        except Exception as e:
            app_logger.error(f"Error listing tasks: {e}", exc_info=True)
            return False, f"Error listing tasks: {str(e)}", [], 0
    
    def get_task_by_number(self, task_number: int) -> Tuple[bool, str, Optional[Task]]:
        """
        Get a specific task by its number (1-based index). Tasks are sorted by priority.

        Args:
            task_number: Task number (1-based)

        Returns:
            Tuple of (success, message, task)
        """
        try:
            if task_number < 1:
                return False, "Task number must be positive", None

            # Get tasks from cache
            tasks = self._get_tasks_from_cache()

            if not tasks:
                return False, "No tasks found", None

            # Sort by priority: high -> medium -> low -> none (same as list_tasks)
            tasks.sort(key=lambda t: self.PRIORITY_ORDER.get(t.priority, 3))

            if task_number > len(tasks):
                return False, f"Task number {task_number} is out of range (1-{len(tasks)})", None

            task = tasks[task_number - 1]
            app_logger.info(f"Retrieved task {task_number}: {task.description}")
            return True, "Task retrieved successfully", task

        except Exception as e:
            app_logger.error(f"Error getting task: {e}", exc_info=True)
            return False, f"Error getting task: {str(e)}", None
    
    def delete_task(self, task_identifier: str) -> Tuple[bool, str]:
        """
        Permanently delete a task from the TODO list.
        
        Args:
            task_identifier: Task number (1-based) or partial description
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Read TODO list
            todo_data = self._read_file(self.todo_file)
            tasks = [Task.from_dict(t) for t in todo_data["tasks"]]
            
            if not tasks:
                return False, "No tasks to delete"
            
            # Find task
            task_index = None
            task_description = None
            
            try:
                task_num = int(task_identifier)
                if 1 <= task_num <= len(tasks):
                    task_index = task_num - 1
                    task_description = tasks[task_index].description
            except ValueError:
                identifier_lower = task_identifier.lower()
                for idx, task in enumerate(tasks):
                    if identifier_lower in task.description.lower():
                        task_index = idx
                        task_description = task.description
                        break
            
            if task_index is None:
                return False, f"Task '{task_identifier}' not found"
            
            # Remove task
            todo_data["tasks"].pop(task_index)
            self._write_file(self.todo_file, todo_data)
            
            app_logger.info(f"Deleted task: {task_description}")
            return True, "Task deleted successfully"
            
        except Exception as e:
            app_logger.error(f"Error deleting task: {e}", exc_info=True)
            return False, f"Error deleting task: {str(e)}"
    
    def get_task_count(self) -> int:
        """Get the total number of pending tasks."""
        try:
            todo_data = self._read_file(self.todo_file)
            return len(todo_data.get("tasks", []))
        except Exception:
            return 0
    
    def get_completed_count(self) -> int:
        """Get the total number of completed tasks."""
        try:
            done_data = self._read_file(self.done_file)
            return len(done_data.get("tasks", []))
        except Exception:
            return 0
    
    def mark_task_obsolete(self, task_identifier: str) -> Tuple[bool, str, Optional[Task]]:
        """
        Mark a task as obsolete by moving it from TODO to OBSOLETE. Tasks are sorted by priority when using numbers.

        Args:
            task_identifier: Task number (1-based, from priority-sorted list) or partial description

        Returns:
            Tuple of (success, message, obsolete_task)
        """
        try:
            todo_data = self._get_fresh_todo_data()
            tasks = self._get_tasks_from_cache()

            if not tasks:
                return False, "No tasks to mark obsolete", None

            # Use helper method to find task
            task_to_obsolete, original_index = self._find_task_by_identifier(task_identifier, tasks)

            if task_to_obsolete is None:
                raise TaskNotFoundError(f"Task '{task_identifier}' not found")

            # Move task to obsolete list
            return self._move_task_to_obsolete(todo_data, task_to_obsolete, original_index)

        except TaskNotFoundError as e:
            return False, str(e), None
        except Exception as e:
            app_logger.error(f"Error marking task as obsolete: {e}", exc_info=True)
            return False, f"Error marking task as obsolete: {str(e)}", None

    def _move_task_to_obsolete(self, todo_data: Dict, task: Task, original_index: int) -> Tuple[bool, str, Task]:
        """Move a task from TODO to OBSOLETE list."""
        # Mark as obsolete (add timestamp)
        task.completed_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        # Remove from TODO (using original index from unsorted list)
        todo_data["tasks"].pop(original_index)
        self._write_file(self.todo_file, todo_data)

        # Clear all caches since we modified data
        self._cached_tasks = None
        self._todo_cache = None
        self._cache_timestamp = None

        # Add to OBSOLETE
        obsolete_data = self._read_file(self.obsolete_file)
        obsolete_data["tasks"].append(task.to_dict())
        self._write_file(self.obsolete_file, obsolete_data)

        app_logger.info(f"Marked task as obsolete: {task.description}")
        return True, "Task marked as obsolete successfully", task
    
    def get_obsolete_count(self) -> int:
        """Get the total number of obsolete tasks."""
        try:
            obsolete_data = self._read_file(self.obsolete_file)
            return len(obsolete_data.get("tasks", []))
        except Exception:
            return 0

    def health_check(self) -> Tuple[bool, str]:
        """Check if TODO files are accessible and valid."""
        try:
            # Test reading all files
            for file_path in [self.todo_file, self.done_file, self.obsolete_file]:
                if file_path.exists():
                    data = self._read_file(file_path)
                    if not isinstance(data, dict) or "tasks" not in data:
                        return False, f"Invalid file format in {file_path}"

            return True, "All TODO files are healthy"
        except Exception as e:
            return False, f"Health check failed: {str(e)}"


# Test code moved to src/test_todo_manager.py

