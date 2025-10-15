#!/usr/bin/env python3
"""
Audio capture test script for testing transcription with real audio.

This script:
1. Records a short audio clip using the configured microphone
2. Tests transcription of the recorded audio
3. Tests LLM processing of the transcription
4. Shows the complete flow with real user speech

Usage:
    python src/test_audio_capture.py
    python src/test_audio_capture.py --duration 5
"""

import os
import sys
import argparse
import time
from typing import Optional

# Add src to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.config.settings import load_settings
from src.audio.capture import AudioCapturer
from src.transcription.groq_client import GroqTranscriber
from src.llm.client import LiteLLMClient
from src.llm.prompts import get_system_prompt, get_available_tools
from src.utils.logger import app_logger, configure_logging

class AudioCaptureTranscriptionTester:
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
        self.audio_capturer = AudioCapturer(self.settings)
        self.transcriber = GroqTranscriber(self.settings)
        self.llm_client = LiteLLMClient(self.settings)

    def test_capture_and_transcription(self, duration: int = 3) -> bool:
        """Test capturing real audio and transcribing it."""
        app_logger.info("🎤 Testing audio capture and transcription with real speech...")
        
        try:
            # List available microphones
            app_logger.info("📋 Available microphones:")
            self.audio_capturer.list_available_microphones()
            
            # Capture audio
            app_logger.info(f"🔴 Recording {duration} seconds of audio...")
            app_logger.info("🗣️ Please speak now! Try saying something like:")
            app_logger.info("   - 'play some music'")
            app_logger.info("   - 'turn up the volume'") 
            app_logger.info("   - 'put the computer to sleep'")
            
            # Count down
            for i in range(3, 0, -1):
                app_logger.info(f"Starting in {i}...")
                time.sleep(1)
            app_logger.info("🎙️ Recording now! Speak clearly...")
            
            # Record audio using the correct method name
            audio_file = self.audio_capturer.capture_test(duration=duration)
            
            if not audio_file:
                app_logger.error("❌ Audio capture failed")
                return False
                
            app_logger.info(f"✅ Audio recorded: {audio_file}")
            
            # Transcribe
            app_logger.info("🔄 Transcribing audio...")
            transcript = self.transcriber.transcribe_audio(audio_file)
            
            if not transcript:
                app_logger.error("❌ Transcription failed")
                return False
                
            transcript = transcript.strip()
            app_logger.info(f"📝 Transcription: '{transcript}'")
            
            if not transcript:
                app_logger.warning("⚠️ Empty transcription - please speak louder or check microphone")
                return False
                
            # Process with LLM
            app_logger.info("🧠 Processing with LLM...")
            system_prompt = get_system_prompt(self.settings)
            available_tools = get_available_tools()
            
            tool_call = self.llm_client.process_transcript(transcript, system_prompt, available_tools)
            
            if tool_call:
                app_logger.info("✅ Complete flow successful!")
                app_logger.info(f"🎯 Final result: {tool_call}")
                
                # Provide user feedback
                tool_name = tool_call.get("tool_name")
                parameters = tool_call.get("parameters", {})
                
                if tool_name == "play_music":
                    action = parameters.get("action", "unknown")
                    app_logger.info(f"🎵 Music control: {action}")
                elif tool_name == "control_volume":
                    action = parameters.get("action", "unknown")
                    amount = parameters.get("amount", "")
                    amount_str = f" by {amount}" if amount else ""
                    app_logger.info(f"🔊 Volume control: {action}{amount_str}")
                elif tool_name == "system_control":
                    action = parameters.get("action", "unknown")
                    app_logger.info(f"💻 System control: {action}")
                elif tool_name == "unknown_request":
                    reason = parameters.get("reason", "No reason provided")
                    app_logger.info(f"❓ Unknown request: {reason}")
                    
                return True
            else:
                app_logger.error("❌ LLM processing failed")
                return False
                
        except Exception as e:
            app_logger.error(f"❌ Test failed: {e}", exc_info=True)
            return False

    def test_multiple_phrases(self) -> None:
        """Test multiple phrases in sequence."""
        app_logger.info("🎤 Testing multiple voice commands...")
        
        phrases_to_test = [
            "Say: 'play some music'",
            "Say: 'turn up the volume'",
            "Say: 'pause the music'",
            "Say: 'put the computer to sleep'"
        ]
        
        results = []
        
        for i, phrase in enumerate(phrases_to_test, 1):
            app_logger.info(f"📢 Test {i}/{len(phrases_to_test)}: {phrase}")
            input("Press Enter when ready to record...")
            
            success = self.test_capture_and_transcription(duration=3)
            results.append(success)
            
            if i < len(phrases_to_test):
                app_logger.info("⏸️ Pausing for 2 seconds...")
                time.sleep(2)
        
        # Summary
        successful = sum(results)
        total = len(results)
        app_logger.info(f"📊 Results: {successful}/{total} successful ({successful/total*100:.1f}%)")

def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test audio capture and transcription with real speech")
    parser.add_argument("--duration", type=int, default=3, help="Duration in seconds to record")
    parser.add_argument("--multiple", action="store_true", help="Test multiple phrases")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config file")
    
    args = parser.parse_args()
    
    tester = AudioCaptureTranscriptionTester(config_path=args.config)
    
    if args.multiple:
        tester.test_multiple_phrases()
    else:
        tester.test_capture_and_transcription(duration=args.duration)

if __name__ == "__main__":
    main() 