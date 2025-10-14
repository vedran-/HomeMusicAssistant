# Adding New Tools to the Voice Control System

This guide documents the process for adding new tools/capabilities to the Home Assistant Voice Control System, based on the TODO list tool implementation.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Step-by-Step Implementation](#step-by-step-implementation)
3. [File Structure](#file-structure)
4. [Important Patterns](#important-patterns)
5. [Testing Strategy](#testing-strategy)
6. [Common Pitfalls](#common-pitfalls)
7. [Example: TODO Tool Implementation](#example-todo-tool-implementation)

---

## Architecture Overview

The tool system follows this flow:

```
User Voice Command 
  → Wake Word Detection 
  → Transcription (Groq Whisper) 
  → LLM (processes intent + selects tool)
  → Tool Registry (executes tool)
  → Tool Implementation (actual logic)
  → Response (spoken via TTS)
```

### Key Components

1. **Tool Implementation** (`src/tools/your_tool.py`) - Core logic and business rules
2. **Tool Registry** (`src/tools/registry.py`) - Execution dispatcher and orchestration
3. **LLM Prompts** (`src/llm/prompts.py`) - Tool definitions and examples for the LLM
4. **Configuration** (`src/config/settings.py`) - Tool-specific settings
5. **Tests** (`src/test_your_tool.py`) - Comprehensive testing suite

---

## Step-by-Step Implementation

### Phase 1: Planning

**Before writing any code:**

1. **Define the tool's purpose** - What will it do? What problem does it solve?
2. **List all operations** - What actions should users be able to perform?
3. **Identify data storage needs** - Files? Database? In-memory?
4. **Determine voice commands** - How will users interact with it?
5. **Consider brevity** - Voice feedback should be short and clear

**Example (TODO tool):**
- Purpose: Manage tasks via voice
- Operations: add, complete, list, get specific, mark obsolete
- Storage: JSON files (TODO.json, DONE.json, OBSOLETE.json)
- Commands: "add task", "what's next", "mark done", etc.
- Brevity: "Task added" not "I've successfully added the task to your list"

### Phase 2: Core Implementation

#### Step 1: Create the Tool Manager

**File:** `src/tools/your_tool_manager.py`

**Key requirements:**
- Implement all business logic here
- Use type hints for all methods
- Return tuples of `(success: bool, message: str, data: Optional[Any])`
- Use the app logger for all logging
- Handle errors gracefully
- Make operations atomic (especially file writes)

**Template:**

```python
"""
Your Tool Manager

This module handles:
1. Operation A
2. Operation B
3. Operation C
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from src.utils.logger import app_logger


class YourToolManager:
    """Manager for your tool operations."""
    
    def __init__(self, config_param: str):
        """
        Initialize the manager.
        
        Args:
            config_param: Configuration parameter
        """
        self.config_param = config_param
        app_logger.info(f"YourToolManager initialized")
    
    def operation_a(self, param: str) -> Tuple[bool, str, Optional[Any]]:
        """
        Perform operation A.
        
        Args:
            param: Parameter description
            
        Returns:
            Tuple of (success, message, result_data)
        """
        try:
            # Your logic here
            app_logger.info(f"Operation A completed: {param}")
            return True, "Success message", result_data
            
        except Exception as e:
            app_logger.error(f"Error in operation_a: {e}", exc_info=True)
            return False, f"Error: {str(e)}", None
```

**Important patterns:**
- ✅ Always use try/except blocks
- ✅ Log all operations (info level for success, error level for failures)
- ✅ Return consistent tuple format: `(bool, str, Optional[data])`
- ✅ Validate inputs before processing
- ✅ Use atomic operations for data persistence
- ❌ Don't log sensitive information
- ❌ Don't use blocking operations without timeouts

#### Step 2: Add Configuration Settings

**File:** `src/config/settings.py`

**Add a settings class:**

```python
class YourToolSettings(BaseModel):
    """Your tool configuration."""
    enabled: bool = Field(default=True, description="Enable your tool")
    data_dir: str = Field(default="./data/yourtool", description="Data directory")
    
    @validator('data_dir', pre=True, always=True)
    def resolve_data_dir(cls, v):
        return os.path.abspath(v)
```

**Add to AppSettings:**

```python
class AppSettings(BaseModel):
    # ... existing fields ...
    yourtool_settings: YourToolSettings = Field(default_factory=YourToolSettings)
```

**Update load_settings() to create directories:**

```python
def load_settings(config_path: str = "config.json") -> AppSettings:
    # ... existing code ...
    
    # Create your tool data directory if it doesn't exist
    yourtool_settings_data = config_data.get('yourtool_settings', {})
    if 'data_dir' in yourtool_settings_data:
        data_dir = os.path.abspath(yourtool_settings_data['data_dir'])
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            print(f"Created your tool data directory: {data_dir}")
        config_data['yourtool_settings']['data_dir'] = data_dir
    
    return AppSettings(**config_data)
```

#### Step 3: Register Tools with LLM

**File:** `src/llm/prompts.py`

**A. Update the system prompt with usage instructions:**

```python
CRITICAL RULE FOR YOUR TOOL:
Describe how the tool works:
- Key concept 1
- Key concept 2
- Important behaviors

Examples:
- If user says "X" → call tool_name with param="value"
- If user says "Y" → call other_tool with param="value"
```

**B. Add tool definitions to `get_available_tools()`:**

```python
{
    "type": "function",
    "function": {
        "name": "your_tool_action",
        "description": "Clear, concise description of what this does. Include when to use it.",
        "parameters": {
            "type": "object",
            "properties": {
                "param_name": {
                    "type": "string",
                    "description": "What this parameter does",
                    "enum": ["option1", "option2"]  # Optional: for fixed choices
                },
                "optional_param": {
                    "type": "integer",
                    "description": "Optional parameter description",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10
                }
            },
            "required": ["param_name"]  # Only required params here
        }
    }
}
```

**Important for LLM prompts:**
- ✅ Be explicit and specific in descriptions
- ✅ Provide multiple examples of natural language commands
- ✅ Emphasize brevity in system prompt
- ✅ Use CRITICAL or IMPORTANT for key rules
- ✅ Group related examples together
- ❌ Don't assume the LLM knows implicit behaviors
- ❌ Don't make descriptions too verbose

#### Step 4: Add Execution Handlers

**File:** `src/tools/registry.py`

**A. Initialize your tool manager in `__init__`:**

```python
def __init__(self, settings: AppSettings):
    # ... existing code ...
    
    # Initialize your tool manager
    self.yourtool_manager = None
    if settings.yourtool_settings.enabled:
        try:
            self.yourtool_manager = YourToolManager(
                config_param=settings.yourtool_settings.data_dir
            )
            app_logger.info(f"Your tool manager initialized")
        except Exception as e:
            app_logger.error(f"Failed to initialize your tool manager: {e}")
```

**B. Add to `execute_tool_call()` dispatcher:**

```python
def execute_tool_call(self, tool_call: Dict[str, Any], ...) -> Dict[str, Any]:
    # ... existing code ...
    
    elif tool_name == "your_tool_action":
        return self._execute_your_tool_action(parameters)
```

**C. Implement execution methods:**

```python
def _execute_your_tool_action(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute your tool action."""
    if not self.yourtool_manager:
        return {
            "success": False,
            "error": "Your tool is not enabled",
            "feedback": "Your tool is not available"
        }
    
    # Extract parameters
    param = parameters.get("param_name")
    
    # Validate
    if not param:
        return {
            "success": False,
            "error": "Parameter required",
            "feedback": "I need more information"
        }
    
    # Execute
    success, message, data = self.yourtool_manager.operation(param)
    
    # Return result
    if success:
        # Create brief feedback for voice
        feedback = "Brief confirmation message"  # Keep it SHORT!
        
        return {
            "success": True,
            "output": message,
            "feedback": feedback
        }
    else:
        return {
            "success": False,
            "error": message,
            "feedback": "Brief error message"
        }
```

**Voice feedback guidelines:**
- ✅ 1-5 words for simple confirmations: "Done", "Task added", "Volume up"
- ✅ Under 15 words for informational responses
- ✅ Use natural, conversational language
- ✅ Be specific enough to be useful
- ❌ Don't repeat what the user just said
- ❌ Don't over-explain
- ❌ Don't use technical jargon

### Phase 3: Testing

#### Step 5: Create Comprehensive Tests

**File:** `src/test_your_tool.py`

**Test categories to include:**

```python
"""
Test script for Your Tool functionality.

This script tests:
1. Basic operations
2. Edge cases and error handling
3. Integration with ToolRegistry
4. Data persistence
5. Configuration validation
"""

def test_basic_operations():
    """Test all basic operations work correctly."""
    pass

def test_edge_cases():
    """Test error handling and edge cases."""
    pass

def test_registry_integration():
    """Test tool works through ToolRegistry."""
    pass

def test_persistence():
    """Test data persists across sessions."""
    pass

def main():
    """Run all tests."""
    try:
        test_basic_operations()
        test_edge_cases()
        test_registry_integration()
        test_persistence()
        
        print("✅ All tests passed successfully!")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
```

**Testing best practices:**
- ✅ Test each operation independently
- ✅ Test error conditions and invalid inputs
- ✅ Test data persistence (if applicable)
- ✅ Test integration through ToolRegistry
- ✅ Clean up test data after each test
- ✅ Use descriptive test names
- ✅ Add print statements for progress visibility
- ❌ Don't leave test data/files behind
- ❌ Don't test implementation details, test behavior

---

## File Structure

When adding a new tool, you'll typically modify these files:

```
HomeMusicAssistant/
├── src/
│   ├── config/
│   │   └── settings.py              # Add YourToolSettings class
│   ├── llm/
│   │   └── prompts.py                # Add tool definitions + examples
│   ├── tools/
│   │   ├── registry.py               # Add execution handlers
│   │   └── your_tool_manager.py      # NEW: Core tool logic
│   └── test_your_tool.py             # NEW: Comprehensive tests
├── config.json                        # Optionally add tool config
└── docs/
    └── YOUR_TOOL_GUIDE.md            # NEW: User-facing documentation
```

---

## Important Patterns

### 1. Return Value Pattern

**Always return tuples for operations:**

```python
def operation(self, param: str) -> Tuple[bool, str, Optional[Data]]:
    """
    Returns:
        Tuple of (success, message, data)
    """
```

**In registry execution methods, return dicts:**

```python
def _execute_tool(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns:
        Dict with keys: success, output, feedback, (optional) error
    """
    return {
        "success": True,
        "output": "Detailed output for logs",
        "feedback": "Brief message for TTS"
    }
```

### 2. Error Handling Pattern

```python
try:
    # Your operation
    app_logger.info("Success message")
    return True, "Success", result
    
except SpecificException as e:
    app_logger.error(f"Specific error: {e}")
    return False, "User-friendly error message", None
    
except Exception as e:
    app_logger.error(f"Unexpected error: {e}", exc_info=True)
    return False, f"Error: {str(e)}", None
```

### 3. Logging Pattern

```python
# Info level for successful operations
app_logger.info(f"Operation completed: {param}")

# Warning for recoverable issues
app_logger.warning(f"Non-critical issue: {detail}")

# Error for failures
app_logger.error(f"Operation failed: {error}", exc_info=True)

# Debug for detailed information (usually not needed)
app_logger.debug(f"Internal state: {details}")
```

### 4. Data Persistence Pattern (JSON)

```python
def _write_file(self, file_path: Path, data: Dict[str, Any]):
    """Write data atomically to avoid corruption."""
    try:
        # Write to temporary file first
        temp_file = file_path.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        temp_file.replace(file_path)
        
    except Exception as e:
        app_logger.error(f"Error writing to {file_path}: {e}")
        raise
```

### 5. Priority/Sorting Pattern

If your tool has items that need prioritization:

```python
# Define priority order
priority_order = {'high': 0, 'medium': 1, 'low': 2, None: 3}

# Sort using the order
items.sort(key=lambda item: priority_order.get(item.priority, 3))
```

**Important:** Keep sorting consistent across all operations (list, get, complete, etc.)

---

## Testing Strategy

### Unit Tests

Test each component in isolation:

```python
def test_manager_operations():
    """Test the manager's core operations."""
    manager = YourToolManager(config)
    
    # Test operation A
    success, msg, data = manager.operation_a("test")
    assert success, f"Operation A failed: {msg}"
    assert data is not None, "Expected data to be returned"
    
    # Test operation B
    success, msg, data = manager.operation_b("test")
    assert success, f"Operation B failed: {msg}"
```

### Integration Tests

Test through the ToolRegistry:

```python
def test_tool_registry_integration():
    """Test tool works through ToolRegistry."""
    settings = load_settings()
    registry = ToolRegistry(settings)
    
    # Test tool call
    result = registry.execute_tool_call({
        "tool_name": "your_tool_action",
        "parameters": {"param": "value"}
    })
    
    assert result['success'], f"Tool call failed: {result.get('error')}"
    assert 'feedback' in result, "Missing feedback message"
```

### Edge Case Tests

```python
def test_edge_cases():
    """Test error handling and edge cases."""
    manager = YourToolManager(config)
    
    # Test with empty input
    success, msg, data = manager.operation("")
    assert not success, "Should fail with empty input"
    
    # Test with invalid input
    success, msg, data = manager.operation("invalid")
    assert not success, "Should fail with invalid input"
    
    # Test with None
    success, msg, data = manager.operation(None)
    assert not success, "Should fail with None input"
```

### Persistence Tests

```python
def test_persistence():
    """Test data persists across manager instances."""
    # Create manager and perform operation
    manager1 = YourToolManager(test_dir)
    manager1.add_data("test")
    
    # Delete and recreate manager
    del manager1
    manager2 = YourToolManager(test_dir)
    
    # Verify data persisted
    success, msg, data = manager2.get_data()
    assert success, "Failed to retrieve persisted data"
    assert data is not None, "Data did not persist"
```

---

## Common Pitfalls

### 1. ❌ Verbose Voice Feedback

**Bad:**
```python
feedback = "I've successfully added the task 'buy milk' to your todo list and it will be available when you check your tasks."
```

**Good:**
```python
feedback = "Task added"
```

### 2. ❌ Inconsistent Task Numbers After Sorting

If you sort items for display, **ALL operations** must use the same sorting:

```python
# In list_tasks()
items.sort(key=lambda x: priority_order.get(x.priority, 3))

# In get_task_by_number() - MUST use same sorting!
items.sort(key=lambda x: priority_order.get(x.priority, 3))

# In complete_task() - MUST use same sorting!
sorted_items = sorted(items, key=lambda x: priority_order.get(x.priority, 3))
```

### 3. ❌ Not Handling Tool Disabled State

Always check if the tool manager was initialized:

```python
def _execute_tool(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
    if not self.yourtool_manager:
        return {
            "success": False,
            "error": "Tool not enabled",
            "feedback": "Tool is not available"
        }
```

### 4. ❌ Forgetting to Clean Up Test Data

```python
def test_something():
    test_dir = "./test_data"
    manager = YourToolManager(test_dir)
    
    # ... tests ...
    
    # ALWAYS clean up!
    import shutil
    shutil.rmtree(test_dir)
```

### 5. ❌ Not Providing Examples in Prompts

The LLM needs concrete examples:

**Bad:**
```python
"Use this tool to manage tasks"
```

**Good:**
```python
Examples:
- If user says "add buy milk" → call add_task with description="buy milk"
- If user says "what's next" → call get_task with task_number=1
- If user says "mark first task done" → call complete_task with task_identifier="1"
```

### 6. ❌ Non-Atomic File Operations

**Bad:**
```python
# Direct write - can corrupt on failure
with open(file_path, 'w') as f:
    json.dump(data, f)
```

**Good:**
```python
# Atomic write - safe on failure
temp_file = file_path.with_suffix('.tmp')
with open(temp_file, 'w') as f:
    json.dump(data, f)
temp_file.replace(file_path)  # Atomic rename
```

### 7. ❌ Assuming LLM Knows Implicit Behavior

**Be explicit in prompts:**

```python
CRITICAL: When user asks for a RECOMMENDATION or NEXT TASK, give them just ONE task (the highest priority):
- "what should I work on next" → call get_task with task_number=1 (gives highest priority task)
- "what's my next task" → call get_task with task_number=1
```

---

## Example: TODO Tool Implementation

### Overview

The TODO tool allows voice-based task management with priorities, due dates, and tags.

### Key Features

1. **Add tasks** with optional properties
2. **Complete tasks** (moves to DONE.json)
3. **Mark obsolete** (moves to OBSOLETE.json)
4. **List tasks** with filtering
5. **Get specific task** by number
6. **Priority sorting** (high → medium → low → none)

### Files Modified

1. **`src/tools/todo_manager.py`** (371 lines)
   - Task data class
   - TodoManager with full CRUD operations
   - JSON file management (atomic writes)
   - Priority-based sorting

2. **`src/config/settings.py`** (added ~10 lines)
   - TodoSettings class
   - Integration with AppSettings
   - Directory creation in load_settings()

3. **`src/llm/prompts.py`** (added ~100 lines)
   - System prompt with TODO instructions
   - 5 tool definitions (add_task, complete_task, list_tasks, get_task, obsolete_task)
   - Examples for each operation
   - Special handling for "next task" recommendations

4. **`src/tools/registry.py`** (added ~200 lines)
   - TodoManager initialization
   - 5 execution handler methods
   - Helper method for ordinal numbers ("First", "Second", etc.)
   - Brief voice feedback formatting

5. **`src/test_todo.py`** (560 lines)
   - 7 test suites with 50+ test cases
   - Unit tests for TodoManager
   - Integration tests with ToolRegistry
   - Edge case testing
   - Persistence validation
   - Priority sorting verification

### Design Decisions

1. **Three separate files** (TODO.json, DONE.json, OBSOLETE.json)
   - Keeps completed/obsolete tasks separate
   - Maintains history
   - Easy to query current tasks

2. **Priority-based sorting everywhere**
   - Consistent numbering across all operations
   - Always shows highest priority first
   - Improves user experience

3. **Brief voice feedback**
   - "Task added" not "I've added your task to the list"
   - Single task for "what's next" questions
   - Multiple tasks only when explicitly listing

4. **Flexible task properties**
   - Only description required
   - Optional: priority, due_date, tags
   - LLM handles extracting properties from natural language

5. **Atomic file operations**
   - Write to .tmp file first
   - Atomic rename prevents corruption
   - Error handling at each step

### Time Investment

- Planning & Design: 30 minutes
- Core Implementation: 2 hours
- Testing: 1 hour
- Documentation: 30 minutes
- **Total: ~4 hours**

### Results

- ✅ 100% test pass rate
- ✅ All edge cases handled
- ✅ Clean, maintainable code
- ✅ Comprehensive documentation
- ✅ Natural voice interaction

---

## Checklist for Adding a New Tool

Use this checklist when implementing a new tool:

### Planning Phase
- [ ] Define tool purpose and scope
- [ ] List all required operations
- [ ] Determine data storage approach
- [ ] Design voice command patterns
- [ ] Plan brief voice feedback messages

### Implementation Phase
- [ ] Create tool manager (`src/tools/your_tool_manager.py`)
  - [ ] Implement all operations
  - [ ] Add logging
  - [ ] Handle errors gracefully
  - [ ] Return consistent tuple format
- [ ] Add configuration (`src/config/settings.py`)
  - [ ] Create settings class
  - [ ] Add to AppSettings
  - [ ] Update load_settings()
- [ ] Register with LLM (`src/llm/prompts.py`)
  - [ ] Add system prompt instructions
  - [ ] Define tool functions
  - [ ] Provide examples
  - [ ] Emphasize brevity
- [ ] Add execution handlers (`src/tools/registry.py`)
  - [ ] Initialize tool manager
  - [ ] Add to execute_tool_call()
  - [ ] Implement handler methods
  - [ ] Format voice feedback

### Testing Phase
- [ ] Create test file (`src/test_your_tool.py`)
  - [ ] Test basic operations
  - [ ] Test edge cases
  - [ ] Test registry integration
  - [ ] Test persistence (if applicable)
  - [ ] Clean up test data
- [ ] Run all tests and verify 100% pass rate
- [ ] Test manually via voice (if possible)

### Documentation Phase
- [ ] Add user-facing documentation (`docs/YOUR_TOOL.md`)
- [ ] Update main README if significant feature
- [ ] Add inline code comments
- [ ] Document any special configurations

### Validation Phase
- [ ] Code review (check patterns, logging, error handling)
- [ ] Voice feedback is brief and natural
- [ ] No linter errors
- [ ] All tests pass
- [ ] Documentation is complete

---

## Tips for Success

1. **Start simple** - Implement core functionality first, add features later
2. **Test early, test often** - Don't wait until the end to write tests
3. **Keep voice feedback brief** - 1-5 words is usually enough
4. **Be explicit in prompts** - The LLM needs clear instructions and examples
5. **Handle errors gracefully** - Always return useful feedback
6. **Log everything** - It helps with debugging
7. **Think about edge cases** - What if the user provides invalid input?
8. **Consider performance** - Will this work with large datasets?
9. **Document as you go** - Don't leave it for the end
10. **Follow existing patterns** - Consistency makes maintenance easier

---

## Getting Help

When stuck:

1. **Check existing tools** - Look at how music_controller or todo_manager work
2. **Review test files** - They show usage patterns
3. **Check logs** - The app logger provides detailed information
4. **Test incrementally** - Build and test one feature at a time

---

## Conclusion

Adding a new tool requires careful planning and attention to detail, but following this guide will help ensure a smooth implementation. The key principles are:

- **Consistency** - Follow established patterns
- **Brevity** - Keep voice feedback short
- **Robustness** - Handle errors gracefully
- **Testing** - Verify everything works
- **Documentation** - Help future maintainers

Good luck with your new tool implementation! 🚀

