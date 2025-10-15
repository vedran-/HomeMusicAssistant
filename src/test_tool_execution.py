#!/usr/bin/env python3
"""
Tool Execution Test Script

This script tests the complete tool execution pipeline:
1. LLM processing of text commands
2. Tool registry execution of AutoHotkey scripts
3. End-to-end integration testing

Usage:
    python src/test_tool_execution.py
    python src/test_tool_execution.py --command "turn up the volume"
    python src/test_tool_execution.py --test-all
"""

import os
import sys
import argparse
from typing import Dict, Any

# Add src to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.config.settings import load_settings
from src.llm.client import LiteLLMClient
from src.llm.prompts import get_system_prompt, get_available_tools
from src.tools.registry import ToolRegistry
from src.utils.logger import app_logger

class ToolExecutionTester:
    def __init__(self):
        """Initialize the tester with all required components."""
        try:
            self.settings = load_settings()
            self.llm_client = LiteLLMClient(self.settings)
            self.tool_registry = ToolRegistry(self.settings)
            self.system_prompt = get_system_prompt(self.settings)
            self.available_tools = get_available_tools()
            
            app_logger.info("✅ Tool execution tester initialized successfully")
            
        except Exception as e:
            app_logger.error(f"❌ Failed to initialize tester: {e}")
            raise

    def test_single_command(self, command: str) -> Dict[str, Any]:
        """Test a single voice command end-to-end."""
        app_logger.info(f"🧪 Testing command: '{command}'")
        
        try:
            # Step 1: Process with LLM
            app_logger.info("🧠 Processing with LLM...")
            tool_call = self.llm_client.process_transcript(
                command, 
                self.system_prompt, 
                self.available_tools
            )
            
            if not tool_call:
                app_logger.error("❌ LLM failed to generate tool call")
                return {"success": False, "error": "No tool call generated"}
            
            tool_name = tool_call.get("tool_name")
            parameters = tool_call.get("parameters", {})
            app_logger.info(f"🎯 LLM decision: {tool_name} with parameters: {parameters}")
            
            # Step 2: Execute tool
            app_logger.info("⚙️ Executing tool...")
            execution_result = self.tool_registry.execute_tool_call(tool_call)
            
            # Step 3: Report results
            if execution_result["success"]:
                app_logger.info(f"✅ Success: {execution_result['feedback']}")
                
                # Make tool output more prominent in console/log (matching main.py)
                if execution_result.get("output"):
                    app_logger.info("=" * 50)
                    app_logger.info("🔧 TOOL OUTPUT:")
                    app_logger.info(f"{execution_result['output']}")
                    app_logger.info("=" * 50)
                    
            else:
                app_logger.error(f"❌ Failed: {execution_result['feedback']}")
                if execution_result.get("error"):
                    app_logger.error(f"Error: {execution_result['error']}")
            
            return {
                "success": execution_result["success"],
                "tool_call": tool_call,
                "execution_result": execution_result,
                "command": command
            }
            
        except Exception as e:
            app_logger.error(f"❌ Exception during test: {e}", exc_info=True)
            return {"success": False, "error": str(e), "command": command}

    def test_all_commands(self):
        """Test all common voice commands."""
        test_commands = [
            # Music control
            "play some music",
            "pause the music",
            "toggle music",
            
            # Volume control
            "turn up the volume",
            "turn down the volume",
            "turn up the volume by 10",
            "turn down the volume by 25",
            "mute the volume",
            "unmute the volume",
            
            # System control (safe tests only)
            # Note: We won't test actual sleep/shutdown for safety
            
            # Unknown requests
            "what time is it",
            "hello how are you",
            "tell me a joke"
        ]
        
        app_logger.info(f"🧪 Testing {len(test_commands)} commands...")
        
        results = []
        success_count = 0
        
        for i, command in enumerate(test_commands, 1):
            app_logger.info(f"\n{'='*60}")
            app_logger.info(f"Test {i}/{len(test_commands)}: '{command}'")
            app_logger.info(f"{'='*60}")
            
            result = self.test_single_command(command)
            results.append(result)
            
            if result["success"]:
                success_count += 1
                
            # Small delay between tests
            import time
            time.sleep(1)
        
        # Summary
        app_logger.info(f"\n{'='*60}")
        app_logger.info("TEST SUMMARY")
        app_logger.info(f"{'='*60}")
        app_logger.info(f"Total tests: {len(test_commands)}")
        app_logger.info(f"Successful: {success_count}")
        app_logger.info(f"Failed: {len(test_commands) - success_count}")
        app_logger.info(f"Success rate: {(success_count/len(test_commands)*100):.1f}%")
        
        # Detailed results
        app_logger.info(f"\nDETAILED RESULTS:")
        for result in results:
            status = "✅" if result["success"] else "❌"
            command = result["command"]
            if result["success"] and "tool_call" in result:
                tool_name = result["tool_call"]["tool_name"]
                app_logger.info(f"{status} '{command}' → {tool_name}")
            else:
                error = result.get("error", "Unknown error")
                app_logger.info(f"{status} '{command}' → FAILED: {error}")
        
        return results

    def test_registry_status(self):
        """Test the tool registry status and capabilities."""
        app_logger.info("🔧 Testing tool registry status...")
        
        # Test AutoHotkey connection
        ahk_status = self.tool_registry.test_autohotkey_connection()
        app_logger.info(f"AutoHotkey connection: {'✅ OK' if ahk_status else '❌ FAILED'}")
        
        # List available scripts
        scripts = self.tool_registry.list_available_scripts()
        app_logger.info(f"Available scripts: {scripts}")
        
        # Test a safe volume command
        app_logger.info("Testing safe volume command...")
        test_call = {
            "tool_name": "control_volume",
            "parameters": {"action": "up", "amount": 1}  # Very small increase
        }
        
        result = self.tool_registry.execute_tool_call(test_call)
        app_logger.info(f"Volume test result: {'✅ OK' if result['success'] else '❌ FAILED'}")
        
        return {
            "autohotkey_ok": ahk_status,
            "scripts": scripts,
            "volume_test_ok": result["success"]
        }

def main():
    """Main function for the test script."""
    parser = argparse.ArgumentParser(description="Test tool execution functionality")
    parser.add_argument("--command", type=str, help="Test a specific command")
    parser.add_argument("--test-all", action="store_true", help="Test all predefined commands")
    parser.add_argument("--status", action="store_true", help="Test registry status only")
    
    args = parser.parse_args()
    
    try:
        tester = ToolExecutionTester()
        
        if args.status:
            tester.test_registry_status()
        elif args.command:
            tester.test_single_command(args.command)
        elif args.test_all:
            tester.test_all_commands()
        else:
            # Default behavior: run status check and a few sample commands
            app_logger.info("🚀 Running default test suite...")
            
            # Status check
            tester.test_registry_status()
            
            # Test a few key commands
            sample_commands = [
                "turn up the volume by 5",
                "turn down the volume by 5",
                "play some music",
                "what time is it"
            ]
            
            app_logger.info(f"\n🧪 Testing {len(sample_commands)} sample commands...")
            for command in sample_commands:
                app_logger.info(f"\n--- Testing: '{command}' ---")
                tester.test_single_command(command)
                
        app_logger.info("\n🎉 Tool execution tests completed!")
        
    except Exception as e:
        app_logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 