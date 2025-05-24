"""
Test script for the enhanced music control tools.

This script tests the new music_control tool and updated play_music tool
to ensure the LLM can properly understand and execute all YouTube Music commands.
"""

import json
from typing import Dict, Any

from src.config.settings import load_settings
from src.llm.client import LiteLLMClient
from src.llm.prompts import get_system_prompt, get_available_tools
from src.tools.registry import ToolRegistry
from src.utils.logger import app_logger

class MusicControlToolTester:
    def __init__(self, config_path: str = "config.json"):
        self.settings = load_settings(config_path)
        self.llm_client = LiteLLMClient(self.settings)
        self.tool_registry = ToolRegistry(self.settings)
        self.system_prompt = get_system_prompt()
        self.available_tools = get_available_tools()
        
        app_logger.info("Music Control Tool Tester initialized")
        
    def test_voice_command(self, voice_input: str, expected_tool: str = None, expected_action: str = None) -> bool:
        """Test a voice command through the complete LLM pipeline."""
        app_logger.info(f"\n🎤 Testing voice input: '{voice_input}'")
        
        try:
            # Process with LLM
            tool_call = self.llm_client.process_transcript(voice_input, self.system_prompt, self.available_tools)
            
            if not tool_call:
                app_logger.error("❌ LLM did not return a tool call")
                return False
                
            tool_name = tool_call.get("tool_name")
            parameters = tool_call.get("parameters", {})
            
            app_logger.info(f"🧠 LLM Response: {tool_name} with parameters: {parameters}")
            
            # Validate expected tool if provided
            if expected_tool and tool_name != expected_tool:
                app_logger.error(f"❌ Expected tool '{expected_tool}' but got '{tool_name}'")
                return False
                
            # Validate expected action if provided
            if expected_action:
                actual_action = parameters.get("action")
                if actual_action != expected_action:
                    app_logger.error(f"❌ Expected action '{expected_action}' but got '{actual_action}'")
                    return False
            
            # Test tool execution (dry run - don't actually execute)
            app_logger.info(f"✅ Tool call validation successful: {tool_name}({parameters})")
            return True
            
        except Exception as e:
            app_logger.error(f"❌ Test failed: {e}", exc_info=True)
            return False

    def run_comprehensive_tests(self):
        """Run comprehensive tests for all music control functionality."""
        app_logger.info("🚀 Starting comprehensive music control tool tests...")
        
        test_cases = [
            # Basic play_music tool tests
            {
                "input": "play some music",
                "expected_tool": "play_music",
                "expected_action": "play",
                "description": "Basic music play request"
            },
            {
                "input": "play Boards of Canada",
                "expected_tool": "play_music", 
                "expected_action": "play",
                "description": "Play specific artist"
            },
            {
                "input": "play jazz music",
                "expected_tool": "play_music",
                "expected_action": "play", 
                "description": "Play genre"
            },
            {
                "input": "pause the music",
                "expected_tool": "play_music",
                "expected_action": "pause",
                "description": "Pause music"
            },
            {
                "input": "next song",
                "expected_tool": "play_music",
                "expected_action": "next",
                "description": "Next song"
            },
            {
                "input": "previous song",
                "expected_tool": "play_music", 
                "expected_action": "previous",
                "description": "Previous song"
            },
            
            # Advanced music_control tool tests
            {
                "input": "go forward 30 seconds",
                "expected_tool": "music_control",
                "expected_action": "forward",
                "description": "Forward with specific time"
            },
            {
                "input": "go back 15 seconds",
                "expected_tool": "music_control",
                "expected_action": "back", 
                "description": "Back with specific time"
            },
            {
                "input": "rewind 45 seconds",
                "expected_tool": "music_control",
                "expected_action": "rewind",
                "description": "Rewind with specific time"
            },
            {
                "input": "like this song",
                "expected_tool": "music_control",
                "expected_action": "like",
                "description": "Like current song"
            },
            {
                "input": "dislike this song",
                "expected_tool": "music_control",
                "expected_action": "dislike",
                "description": "Dislike current song"
            },
            {
                "input": "turn on shuffle",
                "expected_tool": "music_control",
                "expected_action": "shuffle",
                "description": "Enable shuffle mode"
            },
            {
                "input": "toggle shuffle",
                "expected_tool": "music_control",
                "expected_action": "shuffle",
                "description": "Toggle shuffle mode"
            },
            {
                "input": "turn on repeat",
                "expected_tool": "music_control",
                "expected_action": "repeat",
                "description": "Enable repeat mode"
            },
            {
                "input": "search for electronic music",
                "expected_tool": "music_control",
                "expected_action": "search",
                "description": "Search for music"
            },
            
            # Volume control tests
            {
                "input": "turn up the volume",
                "expected_tool": "control_volume",
                "expected_action": "up",
                "description": "Volume up"
            },
            {
                "input": "turn down the volume",
                "expected_tool": "control_volume", 
                "expected_action": "down",
                "description": "Volume down"
            },
            {
                "input": "mute the sound",
                "expected_tool": "control_volume",
                "expected_action": "mute",
                "description": "Mute volume"
            },
            
            # Edge cases and variations
            {
                "input": "skip to next track",
                "expected_tool": "play_music",
                "expected_action": "next",
                "description": "Alternative next song phrasing"
            },
            {
                "input": "fast forward 10 seconds",
                "expected_tool": "music_control",
                "expected_action": "forward",
                "description": "Alternative forward phrasing"
            },
            {
                "input": "I like this song",
                "expected_tool": "music_control",
                "expected_action": "like",
                "description": "Natural like phrasing"
            }
        ]
        
        passed = 0
        total = len(test_cases)
        
        for i, test_case in enumerate(test_cases, 1):
            app_logger.info(f"\n📋 Test {i}/{total}: {test_case['description']}")
            
            success = self.test_voice_command(
                test_case["input"],
                test_case.get("expected_tool"),
                test_case.get("expected_action")
            )
            
            if success:
                passed += 1
                app_logger.info(f"✅ PASSED")
            else:
                app_logger.error(f"❌ FAILED")
        
        # Summary
        app_logger.info(f"\n📊 TEST SUMMARY:")
        app_logger.info(f"✅ Passed: {passed}/{total}")
        app_logger.info(f"❌ Failed: {total - passed}/{total}")
        app_logger.info(f"📈 Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            app_logger.info("🎉 ALL TESTS PASSED! Music control tools are working correctly.")
        else:
            app_logger.warning(f"⚠️ {total - passed} tests failed. Review the failures above.")
            
        return passed == total

    def test_tool_definitions(self):
        """Test that tool definitions are properly structured."""
        app_logger.info("\n🔧 Testing tool definitions structure...")
        
        tools = get_available_tools()
        tool_names = [tool["function"]["name"] for tool in tools]
        
        expected_tools = ["play_music", "music_control", "control_volume", "system_control", "unknown_request"]
        
        for expected_tool in expected_tools:
            if expected_tool in tool_names:
                app_logger.info(f"✅ Tool '{expected_tool}' found")
            else:
                app_logger.error(f"❌ Tool '{expected_tool}' missing")
                return False
        
        # Check music_control tool specifically
        music_control_tool = None
        for tool in tools:
            if tool["function"]["name"] == "music_control":
                music_control_tool = tool
                break
                
        if music_control_tool:
            actions = music_control_tool["function"]["parameters"]["properties"]["action"]["enum"]
            expected_actions = ["forward", "back", "rewind", "like", "dislike", "shuffle", "repeat", "search"]
            
            for action in expected_actions:
                if action in actions:
                    app_logger.info(f"✅ Music control action '{action}' found")
                else:
                    app_logger.error(f"❌ Music control action '{action}' missing")
                    return False
        
        app_logger.info("✅ All tool definitions are properly structured")
        return True

def main():
    """Run the music control tool tests."""
    try:
        tester = MusicControlToolTester()
        
        # Test tool definitions first
        if not tester.test_tool_definitions():
            app_logger.error("❌ Tool definition tests failed")
            return
            
        # Run comprehensive tests
        success = tester.run_comprehensive_tests()
        
        if success:
            app_logger.info("\n🎉 All music control tool tests completed successfully!")
        else:
            app_logger.error("\n❌ Some tests failed. Please review the output above.")
            
    except Exception as e:
        app_logger.error(f"❌ Test execution failed: {e}", exc_info=True)

if __name__ == "__main__":
    main() 