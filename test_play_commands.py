#!/usr/bin/env python3
"""
Test script for enhanced play command handling.
Tests that the LLM now properly routes ANY "play <something>" command to the play_music tool.
"""

import os
import sys

# Add src to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.config.settings import load_settings
from src.llm.client import LiteLLMClient
from src.llm.prompts import get_system_prompt, get_available_tools
from src.utils.logger import app_logger

def test_enhanced_play_commands():
    """Test the enhanced play command handling."""
    print("=== Testing Enhanced Play Command Handling ===")
    
    # Initialize components
    settings = load_settings()
    llm_client = LiteLLMClient(settings)
    system_prompt = get_system_prompt()
    available_tools = get_available_tools()
    
    # Test cases that should all work now
    test_cases = [
        "play Magazines",           # The original failing case
        "play rock music", 
        "play jazz",
        "play The Beatles",
        "play something random",
        "play that song from yesterday",
        "play anything",
        "play classical music",
        "play Metallica",
        "play Taylor Swift"
    ]
    
    success_count = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}/{total_tests}: '{test_case}'")
        
        try:
            result = llm_client.process_transcript(test_case, system_prompt, available_tools)
            
            if result:
                tool_name = result.get("tool_name")
                parameters = result.get("parameters", {})
                
                # Check if it's the expected play_music tool
                if tool_name == "play_music" and parameters.get("action") == "play":
                    search_term = parameters.get("search_term", "")
                    print(f"✅ SUCCESS: {tool_name} with action='play', search_term='{search_term}'")
                    success_count += 1
                else:
                    print(f"❌ WRONG TOOL: Got {tool_name} with {parameters} (expected play_music)")
            else:
                print("❌ FAILED: No tool call generated")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    # Summary
    success_rate = (success_count / total_tests) * 100
    print(f"\n📊 Test Results: {success_count}/{total_tests} successful ({success_rate:.1f}%)")
    
    if success_count == total_tests:
        print("🎉 All tests passed! The LLM now properly handles all play commands.")
    else:
        print("⚠️ Some tests failed. The LLM communication may need further adjustment.")
    
    return success_count == total_tests

if __name__ == "__main__":
    test_enhanced_play_commands() 