"""
Tool Registry and Execution System

This module handles:
1. Parsing LLM tool call responses
2. Mapping tool calls to AutoHotkey script commands
3. Executing AutoHotkey scripts via subprocess
4. Capturing and logging script output/errors
"""

import subprocess
import os
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from src.config.settings import AppSettings
from src.utils.logger import app_logger

class ToolExecutionError(Exception):
    """Custom exception for tool execution failures."""
    pass

class ToolRegistry:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.autohotkey_exe = settings.paths.autohotkey_exe
        self.scripts_dir = Path(settings.paths.autohotkey_scripts_dir)
        
        # Validate AutoHotkey executable
        if not os.path.exists(self.autohotkey_exe):
            raise FileNotFoundError(f"AutoHotkey executable not found: {self.autohotkey_exe}")
        
        # Validate scripts directory
        if not self.scripts_dir.exists():
            raise FileNotFoundError(f"AutoHotkey scripts directory not found: {self.scripts_dir}")
        
        app_logger.info(f"Tool registry initialized with AutoHotkey: {self.autohotkey_exe}")
        app_logger.info(f"Scripts directory: {self.scripts_dir}")

    def execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call from the LLM.
        
        Args:
            tool_call: Dict with 'tool_name' and 'parameters' keys
            
        Returns:
            Dict with execution results including success status, output, and feedback
            
        Raises:
            ToolExecutionError: If tool execution fails
        """
        tool_name = tool_call.get("tool_name")
        parameters = tool_call.get("parameters", {})
        
        app_logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
        
        try:
            if tool_name == "play_music":
                return self._execute_play_music(parameters)
            elif tool_name == "control_volume":
                return self._execute_control_volume(parameters)
            elif tool_name == "system_control":
                return self._execute_system_control(parameters)
            elif tool_name == "unknown_request":
                return self._handle_unknown_request(parameters)
            else:
                app_logger.error(f"Unknown tool name: {tool_name}")
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}",
                    "feedback": f"I don't know how to execute '{tool_name}'"
                }
                
        except Exception as e:
            app_logger.error(f"Tool execution failed for {tool_name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "feedback": f"Failed to execute {tool_name}: {str(e)}"
            }

    def _execute_play_music(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute music playback commands."""
        action = parameters.get("action", "play")
        
        # Map LLM actions to music_controller.ahk commands
        command_map = {
            "play": ["play"],
            "pause": ["toggle"],  # toggle is used for pause
            "toggle": ["toggle"],
            "next": ["next"],  # Will need to be implemented in AHK script
            "previous": ["previous"]  # Will need to be implemented in AHK script
        }
        
        if action not in command_map:
            return {
                "success": False,
                "error": f"Unknown music action: {action}",
                "feedback": f"I don't know how to {action} music"
            }
        
        script_path = self.scripts_dir / "music_controller.ahk"
        command = command_map[action]
        
        result = self._run_autohotkey_script(script_path, command)
        
        if result["success"]:
            feedback_map = {
                "play": "Playing music",
                "pause": "Music paused",
                "toggle": "Music toggled",
                "next": "Playing next track",
                "previous": "Playing previous track"
            }
            result["feedback"] = feedback_map.get(action, f"Music {action} executed")
        
        return result

    def _execute_control_volume(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute volume control commands."""
        action = parameters.get("action", "up")
        amount = parameters.get("amount")
        
        script_path = self.scripts_dir / "music_controller.ahk"
        
        if action == "up":
            command = ["volume-up"]
            if amount:
                command.append(str(amount))
            feedback = f"Volume increased" + (f" by {amount}%" if amount else "")
            
        elif action == "down":
            command = ["volume-down"]
            if amount:
                command.append(str(amount))
            feedback = f"Volume decreased" + (f" by {amount}%" if amount else "")
            
        elif action == "mute":
            command = ["mute"]
            feedback = "Volume muted"
            
        elif action == "unmute":
            command = ["unmute"]
            feedback = "Volume unmuted"
            
        else:
            return {
                "success": False,
                "error": f"Unknown volume action: {action}",
                "feedback": f"I don't know how to {action} the volume"
            }
        
        result = self._run_autohotkey_script(script_path, command)
        
        if result["success"]:
            result["feedback"] = feedback
            # Try to capture the new volume level from output
            if result.get("output") and result["output"].strip().isdigit():
                volume_level = result["output"].strip()
                result["feedback"] += f" (now at {volume_level}%)"
        
        return result

    def _execute_system_control(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute system control commands."""
        action = parameters.get("action", "sleep")
        
        script_path = self.scripts_dir / "system_control.ahk"
        
        command_map = {
            "sleep": ["sleep"],
            "shutdown": ["shutdown"]
        }
        
        if action not in command_map:
            return {
                "success": False,
                "error": f"Unknown system action: {action}",
                "feedback": f"I don't know how to {action} the system"
            }
        
        command = command_map[action]
        result = self._run_autohotkey_script(script_path, command)
        
        if result["success"]:
            feedback_map = {
                "sleep": "Putting the computer to sleep",
                "shutdown": "Shutting down the computer"
            }
            result["feedback"] = feedback_map.get(action, f"System {action} executed")
        
        return result

    def _handle_unknown_request(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown requests from the LLM."""
        reason = parameters.get("reason", "Unknown request")
        
        app_logger.info(f"Unknown request handled: {reason}")
        
        return {
            "success": True,  # This is "successful" handling of an unknown request
            "output": reason,
            "feedback": f"I'm sorry, I can't help with that. {reason}"
        }

    def _run_autohotkey_script(self, script_path: Path, args: List[str]) -> Dict[str, Any]:
        """
        Run an AutoHotkey script with the given arguments.
        
        Args:
            script_path: Path to the .ahk script
            args: List of arguments to pass to the script
            
        Returns:
            Dict with success status, output, and error information
        """
        if not script_path.exists():
            error_msg = f"Script not found: {script_path}"
            app_logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output": "",
                "feedback": f"Script file not found: {script_path.name}"
            }
        
        # Build the command
        cmd = [str(self.autohotkey_exe), str(script_path)] + args
        
        app_logger.info(f"Executing: {' '.join(cmd)}")
        
        try:
            # Run the script with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                cwd=str(script_path.parent)  # Run from script directory
            )
            
            # Log the results
            app_logger.info(f"Script exit code: {result.returncode}")
            if result.stdout:
                app_logger.info(f"Script stdout: {result.stdout.strip()}")
            if result.stderr:
                app_logger.warning(f"Script stderr: {result.stderr.strip()}")
            
            success = result.returncode == 0
            
            return {
                "success": success,
                "exit_code": result.returncode,
                "output": result.stdout.strip() if result.stdout else "",
                "error": result.stderr.strip() if result.stderr else "",
                "feedback": "Command executed successfully" if success else f"Command failed with exit code {result.returncode}"
            }
            
        except subprocess.TimeoutExpired:
            error_msg = f"Script execution timed out after 30 seconds"
            app_logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output": "",
                "feedback": "Command timed out"
            }
            
        except FileNotFoundError:
            error_msg = f"AutoHotkey executable not found: {self.autohotkey_exe}"
            app_logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output": "",
                "feedback": "AutoHotkey not found"
            }
            
        except Exception as e:
            error_msg = f"Unexpected error running script: {e}"
            app_logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "output": "",
                "feedback": f"Script execution failed: {str(e)}"
            }

    def test_autohotkey_connection(self) -> bool:
        """
        Test if AutoHotkey is accessible and working.
        
        Returns:
            True if AutoHotkey is working, False otherwise
        """
        try:
            # Test with a simple AutoHotkey command (just check if executable exists and runs)
            # AutoHotkey v2 doesn't support --version, so we'll just run it with /? for help
            result = subprocess.run(
                [self.autohotkey_exe, "/?"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # AutoHotkey /? returns exit code 1 but shows help - this is expected
            if result.returncode in [0, 1]:
                app_logger.info(f"AutoHotkey test successful (exit code: {result.returncode})")
                return True
            else:
                app_logger.error(f"AutoHotkey test failed with exit code: {result.returncode}")
                return False
                
        except Exception as e:
            app_logger.error(f"AutoHotkey test failed: {e}")
            return False

    def list_available_scripts(self) -> List[str]:
        """
        List all available .ahk scripts in the scripts directory.
        
        Returns:
            List of script names
        """
        try:
            scripts = list(self.scripts_dir.glob("*.ahk"))
            script_names = [script.name for script in scripts]
            app_logger.info(f"Available scripts: {script_names}")
            return script_names
        except Exception as e:
            app_logger.error(f"Failed to list scripts: {e}")
            return []

if __name__ == "__main__":
    # Basic test of the tool registry
    from src.config.settings import load_settings
    
    try:
        settings = load_settings()
        registry = ToolRegistry(settings)
        
        # Test AutoHotkey connection
        if registry.test_autohotkey_connection():
            print("✅ AutoHotkey connection test passed")
        else:
            print("❌ AutoHotkey connection test failed")
        
        # List available scripts
        scripts = registry.list_available_scripts()
        print(f"📋 Available scripts: {scripts}")
        
        # Test a simple tool call
        test_call = {
            "tool_name": "control_volume",
            "parameters": {"action": "up", "amount": 5}
        }
        
        print(f"🧪 Testing tool call: {test_call}")
        result = registry.execute_tool_call(test_call)
        print(f"📊 Result: {result}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 