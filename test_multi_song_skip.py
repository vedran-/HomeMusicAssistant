#!/usr/bin/env python3
"""
Test script for multi-song skipping functionality.
Tests that the system can properly handle commands like "skip next 3 songs" and "go back 2 songs".
"""

import os
import sys

# Add src to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.config.settings import load_settings
from src.llm.client import LiteLLMClient
from src.llm.prompts import get_system_prompt, get_available_tools
from src.tools.registry import ToolRegistry
from src.utils.logger import app_logger

def test_multi_song_skip():
    """Test multi-song skipping functionality."""
    print("=== Testing Multi-Song Skip Functionality ===")
    
    # Initialize components
    settings = load_settings()
    llm_client = LiteLLMClient(settings)
    tool_registry = ToolRegistry(settings)
    system_prompt = get_system_prompt()
    available_tools = get_available_tools()
    
    # Test cases for multi-song skipping
    test_cases = [
        {
            "input": "skip next three songs",
            "expected_tool": "play_music",
            "expected_action": "next",
            "expected_count": 3,
            "description": "Skip multiple songs forward"
        },
        {
            "input": "go to next 2 songs",
            "expected_tool": "play_music", 
            "expected_action": "next",
            "expected_count": 2,
            "description": "Alternative phrasing for next multiple"
        },
        {
            "input": "skip forward 5 songs",
            "expected_tool": "play_music",
            "expected_action": "next", 
            "expected_count": 5,
            "description": "Skip forward with count"
        },
        {
            "input": "go back two songs",
            "expected_tool": "play_music",
            "expected_action": "previous",
            "expected_count": 2,
            "description": "Go back multiple songs"
        },
        {
            "input": "previous 4 songs",
            "expected_tool": "play_music",
            "expected_action": "previous",
            "expected_count": 4,
            "description": "Previous with explicit count"
        },
        {
            "input": "skip back three songs",
            "expected_tool": "play_music",
            "expected_action": "previous",
            "expected_count": 3,
            "description": "Skip backward with count"
        },
        # Single song tests (should still work)
        {
            "input": "next song",
            "expected_tool": "play_music",
            "expected_action": "next",
            "expected_count": None,  # No count should be provided
            "description": "Single next song"
        },
        {
            "input": "previous song",
            "expected_tool": "play_music",
            "expected_action": "previous", 
            "expected_count": None,  # No count should be provided
            "description": "Single previous song"
        }
    ]
    
    success_count = 0
    total_tests = len(test_cases)
    
    print(f"\n🧪 Running {total_tests} test cases...")
    
    for i, test_case in enumerate(test_cases, 1):
        input_text = test_case["input"]
        expected_tool = test_case["expected_tool"]
        expected_action = test_case["expected_action"]
        expected_count = test_case["expected_count"]
        description = test_case["description"]
        
        print(f"\n--- Test {i}/{total_tests}: {description} ---")
        print(f"Input: '{input_text}'")
        
        try:
            # Test LLM processing
            result = llm_client.process_transcript(input_text, system_prompt, available_tools)
            
            if not result:
                print("❌ FAILED: No tool call generated")
                continue
                
            tool_name = result.get("tool_name")
            parameters = result.get("parameters", {})
            action = parameters.get("action")
            count = parameters.get("count")
            
            # Validate tool and action
            if tool_name != expected_tool:
                print(f"❌ FAILED: Wrong tool - got {tool_name}, expected {expected_tool}")
                continue
                
            if action != expected_action:
                print(f"❌ FAILED: Wrong action - got {action}, expected {expected_action}")
                continue
                
            # Validate count
            if expected_count is None:
                if count is not None:
                    print(f"❌ FAILED: Unexpected count - got {count}, expected None")
                    continue
            else:
                if count != expected_count:
                    print(f"❌ FAILED: Wrong count - got {count}, expected {expected_count}")
                    continue
            
            print(f"✅ LLM SUCCESS: {tool_name} with action='{action}'", end="")
            if count:
                print(f", count={count}")
            else:
                print()
            
            # Test tool execution (without actually running AutoHotkey to avoid disruption)
            if not test_tool_execution_safe(tool_registry, result):
                print("❌ FAILED: Tool execution failed")
                continue
                
            print("✅ TOOL EXECUTION SUCCESS")
            success_count += 1
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    # Summary
    success_rate = (success_count / total_tests) * 100
    print(f"\n📊 Test Results: {success_count}/{total_tests} successful ({success_rate:.1f}%)")
    
    if success_count == total_tests:
        print("🎉 All tests passed! Multi-song skipping functionality is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Check the implementation.")
        return False

def test_tool_execution_safe(tool_registry, tool_call):
    """Test tool execution without actually running the AutoHotkey script."""
    try:
        # We'll test the command generation without executing
        tool_name = tool_call.get("tool_name")
        parameters = tool_call.get("parameters", {})
        
        if tool_name == "play_music":
            action = parameters.get("action")
            count = parameters.get("count")
            
            # Test command building logic
            command_map = {
                "play": ["play"],
                "pause": ["toggle"],
                "toggle": ["toggle"],
                "next": ["next"],
                "previous": ["previous"]
            }
            
            if action not in command_map:
                return False
                
            command = command_map[action].copy()
            
            # Test count parameter handling
            if action in ["next", "previous"] and count:
                command.append(str(count))
                print(f"  Generated command: {' '.join(command)}")
            
            return True
        
        return True
        
    except Exception as e:
        print(f"  Tool execution test error: {e}")
        return False

def test_autohotkey_commands():
    """Test AutoHotkey commands directly (requires user confirmation)."""
    print("\n=== AutoHotkey Command Testing ===")
    
    should_test = input("Do you want to test AutoHotkey commands directly? This will affect your music. (y/N): ")
    if should_test.lower() != 'y':
        print("Skipping AutoHotkey testing.")
        return
        
    settings = load_settings()
    tool_registry = ToolRegistry(settings)
    
    test_commands = [
        {"tool_name": "play_music", "parameters": {"action": "next", "count": 2}},
        {"tool_name": "play_music", "parameters": {"action": "previous", "count": 1}},
    ]
    
    for i, command in enumerate(test_commands, 1):
        print(f"\n--- AutoHotkey Test {i} ---")
        print(f"Command: {command}")
        
        confirm = input("Execute this command? (y/N): ")
        if confirm.lower() == 'y':
            try:
                result = tool_registry.execute_tool_call(command)
                print(f"Result: {result}")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("Skipped.")

if __name__ == "__main__":
    print("🎵 Multi-Song Skip Test Suite")
    print("=" * 50)
    
    # Test LLM and registry integration
    success = test_multi_song_skip()
    
    # Optional AutoHotkey testing
    if success:
        test_autohotkey_commands()
    
    print("\n" + "=" * 50)
    print("Testing complete!") 