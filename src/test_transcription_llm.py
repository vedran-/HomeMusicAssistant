#!/usr/bin/env python3
"""
Comprehensive test script for transcription and LLM communication components.

This script tests:
1. Groq transcription with test audio files
2. LiteLLM communication with sample transcripts
3. End-to-end integration of transcription -> LLM -> tool calls

Usage:
    python src/test_transcription_llm.py
    python src/test_transcription_llm.py --test-mode [transcription|llm|integration|all]
    python src/test_transcription_llm.py --transcript "play some music"
"""

import os
import sys
import argparse
import tempfile
import wave
from typing import Optional, Dict, Any

# Add src to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.config.settings import load_settings
from src.transcription.groq_client import GroqTranscriber
from src.llm.client import LiteLLMClient
from src.llm.prompts import get_system_prompt, get_available_tools
from src.utils.logger import app_logger, configure_logging

class TranscriptionLLMTester:
    def __init__(self, config_path: str = "config.json"):
        """Initialize the tester with configuration."""
        try:
            self.settings = load_settings(config_path=config_path)
            configure_logging(self.settings.logging.level)
            app_logger.info("✅ Configuration loaded successfully")
        except Exception as e:
            app_logger.error(f"❌ Failed to load configuration: {e}")
            sys.exit(1)
            
        # Initialize components
        self.transcriber = None
        self.llm_client = None
        
        # Test data
        self.sample_transcripts = [
            "play some music",
            "pause the music", 
            "turn up the volume",
            "turn down the volume by 20",
            "put the computer to sleep",
            "what time is it",  # Should trigger get_time
            "hello how are you"  # Should trigger unknown_request
        ]

    def initialize_transcriber(self) -> bool:
        """Initialize the Groq transcriber."""
        try:
            self.transcriber = GroqTranscriber(self.settings)
            app_logger.info("✅ Groq transcriber initialized")
            return True
        except Exception as e:
            app_logger.error(f"❌ Failed to initialize transcriber: {e}")
            return False

    def initialize_llm_client(self) -> bool:
        """Initialize the LiteLLM client."""
        try:
            self.llm_client = LiteLLMClient(self.settings)
            app_logger.info("✅ LiteLLM client initialized")
            return True
        except Exception as e:
            app_logger.error(f"❌ Failed to initialize LLM client: {e}")
            return False

    def create_test_audio_file(self, duration_seconds: float = 1.0) -> Optional[str]:
        """Create a test WAV file with silence for transcription testing."""
        try:
            fd, temp_path = tempfile.mkstemp(suffix=".wav", prefix="test_audio_")
            os.close(fd)
            
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(16000)  # 16kHz
                
                # Create silence
                num_frames = int(16000 * duration_seconds)
                silent_frame = b'\x00\x00'  # 2 bytes of silence
                frames_data = silent_frame * num_frames
                wf.writeframes(frames_data)
            
            app_logger.info(f"✅ Created test audio file: {temp_path}")
            return temp_path
            
        except Exception as e:
            app_logger.error(f"❌ Failed to create test audio file: {e}")
            return None

    def test_transcription(self) -> bool:
        """Test the transcription component."""
        app_logger.info("🧪 Testing transcription component...")
        
        if not self.initialize_transcriber():
            return False
        
        # Test with dummy audio file
        test_audio = self.create_test_audio_file()
        if not test_audio:
            return False
            
        try:
            transcript = self.transcriber.transcribe_audio(test_audio)
            
            # Clean up test file
            os.remove(test_audio)
            
            if transcript is not None:
                app_logger.info(f"✅ Transcription test successful")
                app_logger.info(f"📝 Transcript: '{transcript}' (empty expected for silence)")
                return True
            else:
                app_logger.error("❌ Transcription returned None")
                return False
                
        except Exception as e:
            app_logger.error(f"❌ Transcription test failed: {e}")
            # Clean up test file
            if test_audio and os.path.exists(test_audio):
                os.remove(test_audio)
            return False

    def test_llm_communication(self) -> bool:
        """Test the LLM communication component."""
        app_logger.info("🧪 Testing LLM communication component...")
        
        if not self.initialize_llm_client():
            return False
        
        system_prompt = get_system_prompt()
        available_tools = get_available_tools()
        
        app_logger.info(f"📋 System prompt: {system_prompt[:100]}...")
        app_logger.info(f"🔧 Available tools: {[tool['function']['name'] for tool in available_tools]}")
        
        success_count = 0
        total_tests = len(self.sample_transcripts)
        
        for i, transcript in enumerate(self.sample_transcripts, 1):
            app_logger.info(f"🧪 Test {i}/{total_tests}: '{transcript}'")
            
            try:
                result = self.llm_client.process_transcript(transcript, system_prompt, available_tools)
                
                if result:
                    tool_name = result.get("tool_name")
                    parameters = result.get("parameters", {})
                    app_logger.info(f"✅ Tool call: {tool_name} with parameters: {parameters}")
                    success_count += 1
                else:
                    app_logger.warning(f"⚠️ No tool call generated for: '{transcript}'")
                    
            except Exception as e:
                app_logger.error(f"❌ LLM test failed for '{transcript}': {e}")
        
        success_rate = (success_count / total_tests) * 100
        app_logger.info(f"📊 LLM communication test results: {success_count}/{total_tests} successful ({success_rate:.1f}%)")
        
        return success_count > 0

    def test_integration(self) -> bool:
        """Test end-to-end integration of transcription -> LLM -> tool calls."""
        app_logger.info("🧪 Testing end-to-end integration...")
        
        if not self.initialize_transcriber() or not self.initialize_llm_client():
            return False
        
        # For integration test, we'll simulate with a transcript since we can't generate meaningful speech
        test_transcript = "play some music please"
        app_logger.info(f"🔄 Simulating integration with transcript: '{test_transcript}'")
        
        try:
            system_prompt = get_system_prompt()
            available_tools = get_available_tools()
            
            # Process with LLM
            tool_call = self.llm_client.process_transcript(test_transcript, system_prompt, available_tools)
            
            if tool_call:
                app_logger.info("✅ Integration test successful!")
                app_logger.info(f"🎯 Full flow result: {tool_call}")
                return True
            else:
                app_logger.error("❌ Integration test failed - no tool call generated")
                return False
                
        except Exception as e:
            app_logger.error(f"❌ Integration test failed: {e}")
            return False

    def test_with_custom_transcript(self, transcript: str) -> bool:
        """Test LLM communication with a custom transcript."""
        app_logger.info(f"🧪 Testing with custom transcript: '{transcript}'")
        
        if not self.initialize_llm_client():
            return False
        
        try:
            system_prompt = get_system_prompt()
            available_tools = get_available_tools()
            
            result = self.llm_client.process_transcript(transcript, system_prompt, available_tools)
            
            if result:
                app_logger.info(f"✅ Custom transcript test successful!")
                app_logger.info(f"🎯 Result: {result}")
                return True
            else:
                app_logger.warning(f"⚠️ No tool call generated for custom transcript")
                return False
                
        except Exception as e:
            app_logger.error(f"❌ Custom transcript test failed: {e}")
            return False

    def run_all_tests(self) -> None:
        """Run all available tests."""
        app_logger.info("🚀 Starting comprehensive transcription and LLM tests...")
        app_logger.info("=" * 60)
        
        results = {}
        
        # Test transcription
        results['transcription'] = self.test_transcription()
        app_logger.info("=" * 60)
        
        # Test LLM communication
        results['llm'] = self.test_llm_communication() 
        app_logger.info("=" * 60)
        
        # Test integration
        results['integration'] = self.test_integration()
        app_logger.info("=" * 60)
        
        # Summary
        app_logger.info("📋 Test Summary:")
        for test_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            app_logger.info(f"  {test_name.capitalize()}: {status}")
        
        total_passed = sum(results.values())
        total_tests = len(results)
        app_logger.info(f"📊 Overall: {total_passed}/{total_tests} tests passed")
        
        if total_passed == total_tests:
            app_logger.info("🎉 All tests passed! System is ready for voice control.")
        else:
            app_logger.warning("⚠️ Some tests failed. Please check configuration and API keys.")

def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test transcription and LLM communication components")
    parser.add_argument("--test-mode", choices=["transcription", "llm", "integration", "all"], 
                       default="all", help="Which test mode to run")
    parser.add_argument("--transcript", type=str, help="Test with a custom transcript")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config file")
    
    args = parser.parse_args()
    
    tester = TranscriptionLLMTester(config_path=args.config)
    
    if args.transcript:
        # Test with custom transcript
        tester.test_with_custom_transcript(args.transcript)
    elif args.test_mode == "transcription":
        tester.test_transcription()
    elif args.test_mode == "llm":
        tester.test_llm_communication()
    elif args.test_mode == "integration":
        tester.test_integration()
    else:  # "all"
        tester.run_all_tests()

if __name__ == "__main__":
    main() 