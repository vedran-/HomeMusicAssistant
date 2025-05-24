#!/usr/bin/env python3
"""
Full System End-to-End Test Script - Phase 4

This script tests the complete voice control pipeline:
1. Wake word detection (simulated and real)
2. Audio capture
3. Transcription 
4. LLM processing
5. Tool execution
6. Error handling and recovery

Usage:
    python src/test_full_system.py
    python src/test_full_system.py --simulation-mode
    python src/test_full_system.py --real-wake-word
"""

import os
import sys
import argparse
import time
from typing import Dict, Any, List

# Add src to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.config.settings import load_settings
from src.audio.wake_word import WakeWordDetector
from src.audio.capture import AudioCapturer
from src.transcription.groq_client import GroqTranscriber
from src.llm.client import LiteLLMClient
from src.llm.prompts import get_system_prompt, get_available_tools
from src.tools.registry import ToolRegistry
from src.utils.logger import app_logger

class FullSystemTester:
    def __init__(self):
        """Initialize the full system tester."""
        try:
            self.settings = load_settings()
            
            # Initialize all components
            self.wake_detector = WakeWordDetector(self.settings)
            self.audio_capturer = AudioCapturer(self.settings)
            self.transcriber = GroqTranscriber(self.settings)
            self.llm_client = LiteLLMClient(self.settings)
            self.tool_registry = ToolRegistry(self.settings)
            
            # Get system prompt and tools
            self.system_prompt = get_system_prompt()
            self.available_tools = get_available_tools()
            
            app_logger.info("✅ Full system tester initialized successfully")
            
        except Exception as e:
            app_logger.error(f"❌ Failed to initialize full system tester: {e}")
            raise

    def test_component_initialization(self) -> Dict[str, bool]:
        """Test that all components initialize correctly."""
        app_logger.info("🔧 Testing component initialization...")
        
        results = {}
        
        # Test wake word detector
        try:
            results["wake_detector"] = self.wake_detector.active_model is not None
            app_logger.info(f"Wake detector: {'✅' if results['wake_detector'] else '❌'} (model: {self.wake_detector.active_model})")
        except Exception as e:
            results["wake_detector"] = False
            app_logger.error(f"Wake detector failed: {e}")
        
        # Test audio capturer
        try:
            self.audio_capturer.list_available_microphones()
            results["audio_capturer"] = True
            app_logger.info("Audio capturer: ✅")
        except Exception as e:
            results["audio_capturer"] = False
            app_logger.error(f"Audio capturer failed: {e}")
        
        # Test transcriber
        try:
            # Create a simple test audio file
            import tempfile
            import wave
            import numpy as np
            
            # Create temporary file that we can properly cleanup
            temp_fd, temp_path = tempfile.mkstemp(suffix=".wav")
            try:
                # Close the file descriptor first to avoid issues on Windows
                os.close(temp_fd)
                
                # Create a short silent audio file
                sample_rate = 16000
                duration = 0.1  # 100ms
                samples = np.zeros(int(sample_rate * duration), dtype=np.int16)
                
                with wave.open(temp_path, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(samples.tobytes())
                
                # Test transcription
                transcript = self.transcriber.transcribe_audio(temp_path)
                results["transcriber"] = transcript is not None
                app_logger.info(f"Transcriber: {'✅' if results['transcriber'] else '❌'}")
                
            finally:
                # Clean up the temporary file
                try:
                    os.unlink(temp_path)
                except (OSError, PermissionError):
                    app_logger.warning(f"Could not delete temporary file {temp_path}")
                
        except Exception as e:
            results["transcriber"] = False
            app_logger.error(f"Transcriber failed: {e}")
        
        # Test LLM client
        try:
            test_response = self.llm_client.process_transcript(
                "test", self.system_prompt, self.available_tools
            )
            results["llm_client"] = test_response is not None
            app_logger.info(f"LLM client: {'✅' if results['llm_client'] else '❌'}")
        except Exception as e:
            results["llm_client"] = False
            app_logger.error(f"LLM client failed: {e}")
        
        # Test tool registry
        try:
            test_call = {"tool_name": "unknown_request", "parameters": {"reason": "test"}}
            test_result = self.tool_registry.execute_tool_call(test_call)
            results["tool_registry"] = test_result["success"]
            app_logger.info(f"Tool registry: {'✅' if results['tool_registry'] else '❌'}")
        except Exception as e:
            results["tool_registry"] = False
            app_logger.error(f"Tool registry failed: {e}")
        
        return results

    def simulate_voice_command(self, command: str) -> Dict[str, Any]:
        """Simulate a voice command without wake word detection."""
        app_logger.info(f"🎭 Simulating voice command: '{command}'")
        
        try:
            # Step 1: Skip wake word (simulated)
            app_logger.info("🎯 Wake word detected (simulated)")
            
            # Step 2: Skip audio capture (simulated)
            app_logger.info("🎤 Audio captured (simulated)")
            
            # Step 3: Skip transcription (use provided command)
            transcript = command
            app_logger.info(f"📝 Transcription: '{transcript}' (simulated)")
            
            # Step 4: Process with LLM
            app_logger.info("🧠 Processing with LLM...")
            tool_call = self.llm_client.process_transcript(
                transcript, self.system_prompt, self.available_tools
            )
            
            if not tool_call:
                return {"success": False, "error": "No tool call generated"}
            
            # Step 5: Execute tool
            app_logger.info("⚙️ Executing tool...")
            execution_result = self.tool_registry.execute_tool_call(tool_call)
            
            # Step 6: Report results
            if execution_result["success"]:
                app_logger.info(f"✅ Command executed successfully: {execution_result['feedback']}")
            else:
                app_logger.error(f"❌ Command failed: {execution_result['feedback']}")
            
            return {
                "success": execution_result["success"],
                "transcript": transcript,
                "tool_call": tool_call,
                "execution_result": execution_result
            }
            
        except Exception as e:
            app_logger.error(f"❌ Simulation failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def test_error_handling(self) -> Dict[str, bool]:
        """Test error handling scenarios."""
        app_logger.info("🛠️ Testing error handling scenarios...")
        
        results = {}
        
        # Test invalid tool name
        try:
            invalid_call = {"tool_name": "invalid_tool", "parameters": {}}
            result = self.tool_registry.execute_tool_call(invalid_call)
            results["invalid_tool"] = not result["success"]  # Should fail gracefully
            app_logger.info(f"Invalid tool handling: {'✅' if results['invalid_tool'] else '❌'}")
        except Exception as e:
            results["invalid_tool"] = False
            app_logger.error(f"Invalid tool test failed: {e}")
        
        # Test empty transcript
        try:
            result = self.llm_client.process_transcript("", self.system_prompt, self.available_tools)
            results["empty_transcript"] = result is None  # Should return None for empty transcripts
            app_logger.info(f"Empty transcript handling: {'✅' if results['empty_transcript'] else '❌'}")
        except Exception as e:
            results["empty_transcript"] = False
            app_logger.error(f"Empty transcript test failed: {e}")
        
        # Test malformed parameters
        try:
            malformed_call = {"tool_name": "control_volume", "parameters": {"action": "invalid_action"}}
            result = self.tool_registry.execute_tool_call(malformed_call)
            results["malformed_params"] = not result["success"]  # Should fail gracefully
            app_logger.info(f"Malformed parameters handling: {'✅' if results['malformed_params'] else '❌'}")
        except Exception as e:
            results["malformed_params"] = False
            app_logger.error(f"Malformed parameters test failed: {e}")
        
        return results

    def test_performance(self) -> Dict[str, float]:
        """Test system performance metrics."""
        app_logger.info("⚡ Testing system performance...")
        
        results = {}
        
        # Test LLM response time
        start_time = time.time()
        try:
            self.llm_client.process_transcript(
                "turn up the volume", self.system_prompt, self.available_tools
            )
            results["llm_response_time"] = time.time() - start_time
            app_logger.info(f"LLM response time: {results['llm_response_time']:.2f}s")
        except Exception as e:
            results["llm_response_time"] = float('inf')
            app_logger.error(f"LLM performance test failed: {e}")
        
        # Test tool execution time
        start_time = time.time()
        try:
            test_call = {"tool_name": "unknown_request", "parameters": {"reason": "performance test"}}
            self.tool_registry.execute_tool_call(test_call)
            results["tool_execution_time"] = time.time() - start_time
            app_logger.info(f"Tool execution time: {results['tool_execution_time']:.2f}s")
        except Exception as e:
            results["tool_execution_time"] = float('inf')
            app_logger.error(f"Tool execution performance test failed: {e}")
        
        return results

    def run_comprehensive_test_suite(self):
        """Run the complete test suite for Phase 4."""
        app_logger.info("🚀 Starting Phase 4 comprehensive test suite...")
        app_logger.info("=" * 60)
        
        # Test 1: Component initialization
        init_results = self.test_component_initialization()
        init_success = all(init_results.values())
        app_logger.info(f"Component initialization: {'✅ PASSED' if init_success else '❌ FAILED'}")
        
        if not init_success:
            app_logger.error("❌ Component initialization failed. Cannot proceed with full tests.")
            return
        
        # Test 2: Simulated voice commands
        app_logger.info("\n" + "=" * 60)
        app_logger.info("Testing simulated voice commands...")
        
        test_commands = [
            "alexa turn up the volume",
            "alexa play some music", 
            "alexa mute the volume",
            "alexa what time is it"
        ]
        
        simulation_results = []
        for command in test_commands:
            result = self.simulate_voice_command(command)
            simulation_results.append(result)
            time.sleep(1)  # Brief pause between tests
        
        simulation_success = sum(1 for r in simulation_results if r["success"])
        app_logger.info(f"\nSimulation tests: {simulation_success}/{len(test_commands)} passed")
        
        # Test 3: Error handling
        app_logger.info("\n" + "=" * 60)
        error_results = self.test_error_handling()
        error_success = all(error_results.values())
        app_logger.info(f"Error handling: {'✅ PASSED' if error_success else '❌ FAILED'}")
        
        # Test 4: Performance
        app_logger.info("\n" + "=" * 60)
        performance_results = self.test_performance()
        
        # Final summary
        app_logger.info("\n" + "=" * 60)
        app_logger.info("PHASE 4 TEST SUMMARY")
        app_logger.info("=" * 60)
        app_logger.info(f"✅ Component initialization: {'PASSED' if init_success else 'FAILED'}")
        app_logger.info(f"✅ Voice command simulation: {simulation_success}/{len(test_commands)} passed")
        app_logger.info(f"✅ Error handling: {'PASSED' if error_success else 'FAILED'}")
        app_logger.info(f"⚡ Performance:")
        app_logger.info(f"   - LLM response: {performance_results.get('llm_response_time', 'N/A'):.2f}s")
        app_logger.info(f"   - Tool execution: {performance_results.get('tool_execution_time', 'N/A'):.2f}s")
        
        overall_success = init_success and (simulation_success == len(test_commands)) and error_success
        app_logger.info(f"\n🎯 Overall: {'✅ MVP READY' if overall_success else '❌ NEEDS WORK'}")
        
        return overall_success

def main():
    """Main function for the full system test."""
    parser = argparse.ArgumentParser(description="Full system testing for Phase 4")
    parser.add_argument("--simulation-mode", action="store_true", help="Run simulation tests only")
    parser.add_argument("--real-wake-word", action="store_true", help="Test real wake word detection (interactive)")
    
    args = parser.parse_args()
    
    try:
        tester = FullSystemTester()
        
        if args.real_wake_word:
            app_logger.info("🎤 Real wake word testing not implemented yet - requires user interaction")
            app_logger.info("💡 Use --simulation-mode for automated testing")
        else:
            # Run comprehensive test suite
            success = tester.run_comprehensive_test_suite()
            
            if success:
                app_logger.info("\n🎉 Phase 4 testing completed successfully! MVP is ready.")
            else:
                app_logger.error("\n⚠️ Phase 4 testing found issues. Please review and fix before MVP release.")
                sys.exit(1)
        
    except Exception as e:
        app_logger.error(f"❌ Full system test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 