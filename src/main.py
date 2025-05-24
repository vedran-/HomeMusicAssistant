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
    
    # Log available microphones for user reference
    audio_capturer.list_available_microphones()
    
    return wake_detector, audio_capturer, transcriber, llm_client

def run_voice_assistant(settings: AppSettings):
    """Main loop for the voice assistant."""
    app_logger.info("Starting Home Assistant voice control system...")
    
    # Initialize components
    wake_detector, audio_capturer, transcriber, llm_client = initialize_components(settings)
    
    # Get the system prompt and available tools for the LLM
    system_prompt = get_system_prompt()
    available_tools = get_available_tools()
    
    # Main loop
    try:
        while True:
            app_logger.info("Waiting for wake word ('hey jarvis' or 'alexa')...")
            
            # Wait for wake word
            if not wake_detector.listen():
                app_logger.error("Wake word detection failed. Retrying...")
                time.sleep(1)
                continue
                
            # Wake word detected, start capturing audio
            audio_file = audio_capturer.capture_audio_after_wake()
            if not audio_file:
                app_logger.error("Audio capture failed. Returning to wake word detection.")
                continue
                
            # Transcribe captured audio
            transcript = transcriber.transcribe_audio(audio_file)
            if not transcript:
                app_logger.error("Transcription failed. Returning to wake word detection.")
                continue
                
            # Process transcript with LLM to determine which tool to call
            tool_call = llm_client.process_transcript(transcript, system_prompt, available_tools)
            
            # Handle the tool call result
            if tool_call:
                tool_name = tool_call.get("tool_name")
                parameters = tool_call.get("parameters", {})
                
                # For MVP, just log the tool call
                # In Phase 3, this will actually execute the tool
                app_logger.info(f"Tool call: {tool_name} with parameters: {parameters}")
                app_logger.info("Tool execution will be implemented in Phase 3.")
            else:
                app_logger.warning("No tool call was generated from the transcript.")
                
            # Small delay before starting to listen for wake word again
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