"""
Tool Registry and Execution System

This module handles:
1. Parsing LLM tool call responses
2. Mapping tool calls to appropriate controllers (YouTube Music API or AutoHotkey)
3. Executing controls and capturing results
4. Logging output/errors
"""

import subprocess
import os
import json
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
from datetime import datetime

from src.config.settings import AppSettings
from src.utils.logger import app_logger
from src.tools.music_controller_api import YouTubeMusicAPIController
from .utils import run_ahk_script

class ToolExecutionError(Exception):
    """Custom exception for tool execution failures."""
    pass

class ToolRegistry:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.autohotkey_exe = settings.paths.autohotkey_exe
        self.scripts_dir = Path(settings.paths.autohotkey_scripts_dir)
        
        # Initialize YouTube Music API controller
        self.music_api = YouTubeMusicAPIController(
            settings=settings, 
            host=settings.youtube_music_api.host,
            port=settings.youtube_music_api.port
        )
        
        # Validate AutoHotkey executable (still needed for system controls)
        if not os.path.exists(self.autohotkey_exe):
            raise FileNotFoundError(f"AutoHotkey executable not found: {self.autohotkey_exe}")
        
        # Validate scripts directory
        if not self.scripts_dir.exists():
            raise FileNotFoundError(f"AutoHotkey scripts directory not found: {self.scripts_dir}")
        
        app_logger.info(f"Tool registry initialized with YouTube Music API at {settings.youtube_music_api.host}:{settings.youtube_music_api.port}")
        app_logger.info(f"AutoHotkey: {self.autohotkey_exe}")
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
            elif tool_name == "music_control":
                return self._execute_music_control(parameters)
            elif tool_name == "control_volume":
                return self._execute_control_volume(parameters)
            elif tool_name == "system_control":
                return self._execute_system_control(parameters)
            elif tool_name == "unknown_request":
                return self._handle_unknown_request(parameters)
            elif tool_name == "get_time":
                return self._execute_get_time(parameters)
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
        """Execute music playback commands, now primarily using AHK for play/radio actions."""
        action = parameters.get("action", "play")
        search_term = parameters.get("search_term")
        play_type = parameters.get("play_type", "default") 
        count = parameters.get("count", 1)
        
        app_logger.info(f"Music API action: {action}, search_term: '{search_term}', play_type: '{play_type}', count: {count}")
        
        try:
            result = None
            feedback = ""

            if action == "play" and search_term:
                if play_type == "radio":
                    app_logger.info(f"Calling start_radio_ahk for: {search_term}")
                    result = self.music_api.start_radio_ahk(search_term)
                    feedback = f"Attempting to start radio for: {search_term}"
                else: 
                    app_logger.info(f"Calling play_music_ahk for: {search_term}")
                    result = self.music_api.play_music_ahk(search_term)
                    feedback = f"Attempting to play: {search_term}"
            
            elif action == "play": 
                result = self.music_api.play() 
                feedback = "Resuming music playback"
            
            elif action == "pause" or action == "toggle":
                result = self.music_api.toggle_playback() 
                feedback = "Music playback toggled"
            
            elif action == "next":
                result = self.music_api.next(count=count) 
                song_word = "song" if count == 1 else "songs"
                feedback = f"Skipped {count} {song_word} forward"
            
            elif action == "previous":
                result = self.music_api.previous(count=count) 
                song_word = "song" if count == 1 else "songs"
                feedback = f"Skipped {count} {song_word} backward"
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown music action: {action}",
                    "feedback": f"I don't know how to {action} music"
                }
            
            if not result or not result.get("success", False): 
                error_detail = result.get("error", result.get("stderr", "Unknown error")) if result else "AHK script did not return a result."
                app_logger.error(f"Music action '{action}' failed: {error_detail}")
                return {
                    "success": False,
                    "error": error_detail,
                    "feedback": f"Failed to {action} music: {error_detail}"
                }
            
            return {
                "success": True,
                "output": result.get("stdout", json.dumps(result) if isinstance(result, dict) else str(result)),
                "feedback": feedback
            }
            
        except Exception as e:
            app_logger.error(f"Music API/AHK exception during '{action}': {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "feedback": f"Error performing '{action}' music: {str(e)}"
            }    

    def _execute_music_control(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute advanced music control commands using YouTube Music API."""
        action = parameters.get("action")
        amount = parameters.get("amount")
        search_term = parameters.get("search_term")
        
        app_logger.info(f"Advanced music control: {action}, amount: {amount}, search_term: {search_term}")
        
        try:
            # Map LLM actions to YouTube Music API methods
            if action == "forward":
                seconds = amount or 10
                result = self.music_api.forward(seconds)
                feedback = f"Forwarded {seconds} seconds"
                
            elif action in ["back", "rewind"]:
                seconds = amount or 10
                result = self.music_api.rewind(seconds)
                feedback = f"Went back {seconds} seconds"
                
            elif action == "like":
                result = self.music_api.like()
                feedback = "Song liked"
                
            elif action == "dislike":
                result = self.music_api.dislike()
                feedback = "Song disliked"
                
            elif action == "shuffle":
                result = self.music_api.toggle_shuffle()
                feedback = "Shuffle mode toggled"
                
            elif action == "repeat":
                result = self.music_api.toggle_repeat()
                feedback = "Repeat mode toggled"
                
            elif action == "search":
                if not search_term:
                    return {
                        "success": False,
                        "error": "Search term required for search action",
                        "feedback": "Please specify what to search for"
                    }
                result = self.music_api.search(search_term)
                feedback = f"Searching for: {search_term}"
                
            else:
                return {
                    "success": False,
                    "error": f"Unknown music control action: {action}",
                    "feedback": f"I don't know how to {action} music"
                }
            
            # Process API result
            if not result.get("success", True):
                app_logger.error(f"Music API error: {result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "feedback": f"Failed to {action}: {result.get('error', 'Unknown error')}"
                }
            
            return {
                "success": True,
                "output": json.dumps(result) if isinstance(result, dict) else str(result),
                "feedback": feedback
            }
            
        except Exception as e:
            app_logger.error(f"Music API exception: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "feedback": f"Error performing {action}: {str(e)}"
            }

    def _execute_control_volume(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute volume control commands using AutoHotkey system_control.ahk."""
        action = parameters.get("action", "up")
        amount = parameters.get("amount")
        
        script_path = self.scripts_dir / "system_control.ahk"
        
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
            
        elif action == "set":
            if amount is None:
                return {
                    "success": False,
                    "error": "Amount required for set volume action",
                    "feedback": "Please specify a volume percentage to set"
                }
            command = ["set-volume", str(amount)]
            feedback = f"Volume set to {amount}%"
            
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
            "shutdown": ["shutdown"],
            "restart": ["restart"]
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
                "shutdown": "Shutting down the computer",
                "restart": "Restarting the computer"
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

    def _execute_get_time(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get_time tool to return current system time and optionally date."""
        include_date = parameters.get("include_date", False)
        time_format = parameters.get("format", "auto")
        
        try:
            now = datetime.now()
            
            # Create human-friendly time format
            hour = now.hour
            minute = now.minute
            
            # Convert to 12-hour format if requested
            if time_format == "12hour":
                am_pm = "AM" if hour < 12 else "PM"
                display_hour = hour if hour <= 12 else hour - 12
                if display_hour == 0:
                    display_hour = 12
                time_str = f"{display_hour} {self._hour_word(display_hour)} and {minute} {self._minute_word(minute)} {am_pm}"
            elif time_format == "24hour" or time_format == "auto":  # Default to 24-hour
                time_str = f"{hour} {self._hour_word(hour)} and {minute} {self._minute_word(minute)}"
            else:
                # Fallback to 24-hour
                time_str = f"{hour} {self._hour_word(hour)} and {minute} {self._minute_word(minute)}"
            
            # Add date if requested
            if include_date:
                date_str = now.strftime('%A, %B %d, %Y')
                output = f"{date_str} at {time_str}"
                feedback = f"Today is {date_str} and the current time is {time_str}"
            else:
                output = time_str
                feedback = f"The current time is {time_str}"
            
            app_logger.info(f"Time request - include_date: {include_date}, format: {time_format}, result: {output}")
            
            return {
                "success": True,
                "output": output,
                "feedback": feedback
            }
            
        except Exception as e:
            app_logger.error(f"Failed to get current time: {e}")
            return {
                "success": False,
                "error": str(e),
                "feedback": "Sorry, I couldn't get the current time"
            }
    
    def _hour_word(self, hour: int) -> str:
        """Return 'hour' or 'hours' based on the number."""
        return "hour" if hour == 1 else "hours"
    
    def _minute_word(self, minute: int) -> str:
        """Return 'minute' or 'minutes' based on the number."""
        return "minute" if minute == 1 else "minutes"

    def _run_autohotkey_script(self, script_path: Path, args: List[str]) -> Dict[str, Any]:
        """
        Run an AutoHotkey script using the utility function.
        
        Args:
            script_path: Path to the .ahk script.
            args: List of arguments to pass to the script.
            
        Returns:
            A dictionary with execution results, including success status, output, and feedback.
        """
        # The new utility function returns a slightly different dict structure.
        # We adapt it here to maintain compatibility with how _run_autohotkey_script was used previously,
        # particularly the 'output' and 'error' keys, and the 'feedback' message construction.
        
        result = run_ahk_script(
            script_path=script_path,
            args=args,
            autohotkey_exe_path=self.autohotkey_exe, # Use configured AHK exe path
            logger=app_logger # Pass the existing app_logger
            # timeout and cwd will use the defaults in run_ahk_script (30s, script's parent dir)
        )
        
        # Adapt the result from run_ahk_script to the expected format of _run_autohotkey_script callers
        # The main difference is that run_ahk_script uses 'stdout', 'stderr', and 'error_message'
        # while the old _run_autohotkey_script used 'output' (for stdout) and 'error' (for stderr or high-level error).
        # The 'feedback' is also slightly different.
        
        adapted_result = {
            "success": result["success"],
            "exit_code": result.get("exit_code"), # Might be None if script didn't run
            "output": result["stdout"], # Map stdout to 'output'
            "error": result["stderr"] or result.get("error_message", ""), # Combine stderr and high-level error_message
            "feedback": result["feedback"] # Use feedback directly from utility
        }
        
        # If the utility reported a high-level error_message (e.g. script not found, timeout),
        # ensure this is prioritized in the 'error' field if stderr was empty.
        if result.get("error_message") and not result["stderr"]:
            adapted_result["error"] = result["error_message"]
            
        return adapted_result

    def test_autohotkey_connection(self) -> bool:
        """
        Test if AutoHotkey is accessible and working.
        
        Returns:
            True if AutoHotkey is working, False otherwise
        """
        try:
            # Test by running a simple script that just exits successfully
            # This is more reliable than trying to get version info
            test_script_content = """
; Simple test script that exits with code 0
ExitApp(0)
"""
            
            # Create a temporary test script
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ahk', delete=False) as temp_file:
                temp_file.write(test_script_content)
                temp_script_path = temp_file.name
            
            try:
                # Run the temporary script
                result = subprocess.run(
                    [self.autohotkey_exe, temp_script_path],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # Clean up the temporary file
                import os
                os.unlink(temp_script_path)
                
                if result.returncode == 0:
                    app_logger.info(f"AutoHotkey connection test successful")
                    return True
                else:
                    app_logger.error(f"AutoHotkey test failed with exit code: {result.returncode}")
                    if result.stderr:
                        app_logger.error(f"AutoHotkey stderr: {result.stderr}")
                    return False
                    
            except Exception as e:
                # Clean up the temporary file even if there's an exception
                import os
                try:
                    os.unlink(temp_script_path)
                except:
                    pass
                raise e
                
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