import os
import sys
import time
from typing import Optional, Dict, Any

from src.config.settings import load_settings, AppSettings
from src.utils.logger import app_logger, configure_logging
from src.audio.wake_word import WakeWordDetector
from src.audio.capture import AudioCapturer
from src.transcription.groq_client import GroqTranscriber
from src.llm.client import LiteLLMClient
from src.llm.prompts import get_system_prompt, get_available_tools
from src.tools.registry import ToolRegistry
from src.tools.utils import GetSystemVolume, SetSystemVolume
from src.tts.piper_client import PiperTTSClient


def initialize_components(settings: AppSettings):
    """Initialize all components required for the voice assistant."""
    app_logger.info("Initializing components...")
    
    # Configure logging based on settings
    configure_logging(settings.logging.level)
    
    # Initialize components (TTS client first so wake detector can use it)
    tts_client = PiperTTSClient(settings)
    wake_detector = WakeWordDetector(settings, tts_client)
    audio_capturer = AudioCapturer(settings)
    transcriber = GroqTranscriber(settings)
    llm_client = LiteLLMClient(settings)
    tool_registry = ToolRegistry(settings)
    
    # Log available microphones for user reference
    audio_capturer.list_available_microphones()
    
    # Test AutoHotkey connection
    if tool_registry.test_autohotkey_connection():
        app_logger.info("✅ AutoHotkey connection verified")
    else:
        app_logger.warning("⚠️ AutoHotkey connection test failed - tool execution may not work")
    
    # List available scripts
    available_scripts = tool_registry.list_available_scripts()
    app_logger.info(f"Available AutoHotkey scripts: {available_scripts}")
    
    # Test TTS initialization
    if tts_client.is_available():
        app_logger.info("✅ TTS (Piper) initialized successfully")
        voice_info = tts_client.get_voice_info()
        app_logger.info(f"Voice model: {voice_info.get('model', 'Unknown')}")
    else:
        app_logger.warning("⚠️ TTS (Piper) initialization failed or disabled")
    
    return wake_detector, audio_capturer, transcriber, llm_client, tool_registry, tts_client

def execute_tool_call(tool_registry: ToolRegistry, tts_client: PiperTTSClient, tool_call: Dict[str, Any]):
    """Execute a tool call and provide user feedback."""
    try:
        tool_name = tool_call.get("tool_name")
        parameters = tool_call.get("parameters", {})
        
        # Handle special TTS tool for speaking responses
        if tool_name == "speak_response":
            text_to_speak = parameters.get("text", "")
            if text_to_speak and tts_client.is_available():
                app_logger.info(f"🗣️ Assistant response: '{text_to_speak}'")
                tts_client.speak_async(text_to_speak)
                return {
                    "success": True,
                    "feedback": "Response spoken",
                    "output": text_to_speak
                }
            else:
                app_logger.info(f"📝 Assistant response: '{text_to_speak}'")
                return {
                    "success": True,
                    "feedback": "Response provided (TTS unavailable)",
                    "output": text_to_speak
                }
        
        # Execute regular tool calls
        result = tool_registry.execute_tool_call(tool_call)
        
        # Log the result
        if result["success"]:
            app_logger.info(f"✅ {result['feedback']}")
            
            # Speak tool feedback if TTS is enabled
            if tts_client.is_available() and tts_client.tts_settings.speak_responses:
                feedback_text = result.get('feedback', '')
                if feedback_text and len(feedback_text) < 200:  # Don't speak very long feedback
                    tts_client.speak_async(feedback_text, interrupt_current=False)
            
            # Make tool output more prominent in console/log
            if result.get("output"):
                app_logger.info("=" * 50)
                app_logger.info("🔧 TOOL OUTPUT:")
                app_logger.info(f"{result['output']}")
                app_logger.info("=" * 50)
            
        else:
            app_logger.error(f"❌ Tool execution failed: {result['feedback']}")
            if result.get("error"):
                app_logger.error(f"Error details: {result['error']}")
            
            # Speak error feedback if TTS is enabled
            if tts_client.is_available() and tts_client.tts_settings.speak_responses:
                error_text = f"Sorry, {result.get('feedback', 'command failed')}"
                tts_client.speak_async(error_text, interrupt_current=False)
                
        return result
        
    except Exception as e:
        app_logger.error(f"Exception during tool execution: {e}", exc_info=True)
        error_result = {
            "success": False,
            "error": str(e),
            "feedback": f"Tool execution failed: {str(e)}"
        }
        
        # Speak error if TTS is available
        if tts_client.is_available() and tts_client.tts_settings.speak_responses:
            tts_client.speak_async("Sorry, there was an error executing that command", interrupt_current=False)
        
        return error_result

def run_voice_assistant(settings: AppSettings):
    """Main loop for the voice assistant."""
    app_logger.info("Starting Home Assistant voice control system...")
    
    # Initialize components
    wake_detector, audio_capturer, transcriber, llm_client, tool_registry, tts_client = initialize_components(settings)
    
    # Get the system prompt and available tools for the LLM
    system_prompt = get_system_prompt()
    available_tools = get_available_tools()
    
    # Main loop
    try:
        app_logger.info("🎤 Voice control system ready! Say 'alexa' or 'hey jarvis' to activate.")
        
        while True:
            app_logger.info("Waiting for wake word ('alexa' or 'hey jarvis')...")
            
            # Wait for wake word
            if not wake_detector.listen():
                app_logger.error("Wake word detection failed. Retrying...")
                time.sleep(1)
                continue
                
            app_logger.info("🎯 Wake word detected! Listening for command...")

            system_volume = GetSystemVolume()
            app_logger.info(f"🔊 System volume: {system_volume}%")
            
            # Gradually lower volume for better wake word detection
            SetSystemVolume(system_volume/3, duration=1.0, steps=10)

            # Wake word detected, start capturing audio
            audio_file = audio_capturer.capture_audio_after_wake()
            if not audio_file:
                app_logger.error("Audio capture failed. Returning to wake word detection.")
                # Restore volume even if audio capture failed
                SetSystemVolume(system_volume, duration=1.0, steps=15)
                continue

            # Gradually restore volume after audio capture
            SetSystemVolume(system_volume, duration=1.0, steps=15)

            # Transcribe captured audio
            transcript = transcriber.transcribe_audio(audio_file)
            if not transcript:
                app_logger.error("Transcription failed. Returning to wake word detection.")
                continue
                
            app_logger.info(f"📝 User said: '{transcript}'")
            
            # Process transcript with LLM to determine which tool to call
            tool_call = llm_client.process_transcript(transcript, system_prompt, available_tools)
            
            # Handle the tool call result
            if tool_call:
                tool_name = tool_call.get("tool_name")
                parameters = tool_call.get("parameters", {})
                
                app_logger.info(f"🧠 LLM decision: {tool_name} with parameters: {parameters}")
                
                # Execute the tool call
                execution_result = execute_tool_call(tool_registry, tts_client, tool_call)
                
                # Provide additional feedback based on the tool
                if execution_result["success"]:
                    if tool_name == "play_music":
                        app_logger.info("🎵 Music control command executed")
                    elif tool_name == "music_control":
                        app_logger.info("🎶 Advanced music control command executed")
                    elif tool_name == "control_volume":
                        app_logger.info("🔊 Volume control command executed")
                    elif tool_name == "system_control":
                        app_logger.info("💻 System control command executed")
                    elif tool_name == "unknown_request":
                        app_logger.info("❓ Unknown request handled")
                else:
                    app_logger.error("❌ Command execution failed")
                    
            else:
                app_logger.warning("No tool call was generated from the transcript.")
                
            # Small delay before starting to listen for wake word again
            app_logger.info("⏳ Ready for next command...")
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        app_logger.info("Keyboard interrupt received. Shutting down...")
    except Exception as e:
        app_logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
    finally:
        app_logger.info("Home Assistant voice control system stopped.")

def main():
    """Entry point for the application."""
    try:
        # Determine config path
        config_path = "config.json"
        if len(sys.argv) > 1:
            config_path = sys.argv[1]
            
        # Load settings
        settings = load_settings(config_path=config_path)
        run_voice_assistant(settings)
        
    except FileNotFoundError as e:
        app_logger.error(f"Configuration error: {e}")
        print(f"ERROR: {e}. Please ensure config.json exists and is properly configured.")
        sys.exit(1)
    except Exception as e:
        app_logger.error(f"Startup error: {e}", exc_info=True)
        print(f"ERROR: Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 