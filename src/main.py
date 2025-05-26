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
from src.utils import GetSystemVolume, SetSystemVolume


def initialize_components(settings: AppSettings):
    """Initialize all components required for the voice assistant."""
    app_logger.info("Initializing components...")
    
    # Configure logging based on settings
    configure_logging(settings.logging.level)
    
    # Initialize components
    wake_detector = WakeWordDetector(settings)
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
    
    return wake_detector, audio_capturer, transcriber, llm_client, tool_registry

def execute_tool_call(tool_registry: ToolRegistry, tool_call: Dict[str, Any]):
    """Execute a tool call and provide user feedback."""
    try:
        result = tool_registry.execute_tool_call(tool_call)
        
        # Log the result
        if result["success"]:
            app_logger.info(f"✅ {result['feedback']}")
            
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
                
        return result
        
    except Exception as e:
        app_logger.error(f"Exception during tool execution: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "feedback": f"Tool execution failed: {str(e)}"
        }

def run_voice_assistant(settings: AppSettings):
    """Main loop for the voice assistant."""
    app_logger.info("Starting Home Assistant voice control system...")
    
    # Initialize components
    wake_detector, audio_capturer, transcriber, llm_client, tool_registry = initialize_components(settings)
    
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
            SetSystemVolume(system_volume/3)

            # Wake word detected, start capturing audio
            audio_file = audio_capturer.capture_audio_after_wake()
            if not audio_file:
                app_logger.error("Audio capture failed. Returning to wake word detection.")
                continue

            SetSystemVolume(system_volume)

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
                execution_result = execute_tool_call(tool_registry, tool_call)
                
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