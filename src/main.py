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
from src.memory.memory_manager import MemoryManager
import uuid
from datetime import datetime, timedelta


def initialize_components(settings: AppSettings):
    """Initialize all components required for the voice assistant."""
    app_logger.info("Initializing components...")
    
    # --- Critical: Set API keys as environment variables for library compatibility ---
    if settings.groq_api_key:
        os.environ["GROQ_API_KEY"] = settings.groq_api_key
    # Set this as well, as some libraries might default to checking it
    if settings.litellm_settings and settings.litellm_settings.api_key:
         os.environ["OPENAI_API_KEY"] = settings.litellm_settings.api_key
    elif settings.groq_api_key:
         os.environ["OPENAI_API_KEY"] = settings.groq_api_key


    # Configure logging based on settings
    configure_logging(settings.logging.level)
    
    # Initialize components (TTS client first so wake detector can use it)
    tts_client = PiperTTSClient(settings)
    wake_detector = WakeWordDetector(settings, tts_client)
    audio_capturer = AudioCapturer(settings)
    transcriber = GroqTranscriber(settings)
    llm_client = LiteLLMClient(settings)
    tool_registry = ToolRegistry(settings)
    memory_manager = MemoryManager(settings.mem0_config)
    
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
    
    return wake_detector, audio_capturer, transcriber, llm_client, tool_registry, tts_client, memory_manager

def execute_tool_call(tool_registry: ToolRegistry, tts_client: PiperTTSClient, tool_call: Dict[str, Any], memory_manager: MemoryManager, user_id: str, session_id: str, original_transcript: str):
    """Execute a tool call and provide user feedback."""
    try:
        tool_name = tool_call.get("tool_name")
        parameters = tool_call.get("parameters", {})
        
        # Execute tool calls
        result = tool_registry.execute_tool_call(
            tool_call,
            memory_manager=memory_manager,
            user_id=user_id,
            session_id=session_id,
            original_transcript=original_transcript
        )
        
        # Log the result
        if result["success"]:
            # Only log success with a check to avoid noisy empty messages
            if result.get('feedback'):
                app_logger.info(f"✅ {result['feedback']}")
            
            # Speak tool feedback if TTS is enabled
            if tts_client.is_available() and tts_client.tts_settings.speak_responses:
                feedback_text = result.get('feedback', '')
                if feedback_text:
                    # Handle text length with smart truncation
                    max_length = tts_client.tts_settings.max_speech_length
                    if len(feedback_text) > max_length:
                        # Truncate silently to keep speech concise
                        final_text = feedback_text[:max_length]
                        tts_client.speak_async(final_text, interrupt_current=False)
                    else:
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
    wake_detector, audio_capturer, transcriber, llm_client, tool_registry, tts_client, memory_manager = initialize_components(settings)
    
    # Get the system prompt and available tools for the LLM
    system_prompt = get_system_prompt()
    available_tools = get_available_tools()
    
    # Session management
    USER_ID = "home_user"
    SESSION_TIMEOUT_MINUTES = 10
    last_interaction_time: Optional[datetime] = None
    session_id: str = str(uuid.uuid4())

    if True:
    # Main loop
    #try:
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

            # Check for session timeout
            if last_interaction_time and (datetime.now() - last_interaction_time) > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
                session_id = str(uuid.uuid4())
                app_logger.info(f"New session started with ID: {session_id}")
            last_interaction_time = datetime.now()

            # Gradually restore volume after audio capture
            SetSystemVolume(system_volume, duration=1.0, steps=15)

            # Transcribe captured audio
            transcript = transcriber.transcribe_audio(audio_file)
            if not transcript:
                app_logger.error("Transcription failed. Returning to wake word detection.")
                continue
                
            app_logger.info(f"📝 User said: '{transcript}'")
            
            # --- Memory Integration ---
            memories_str = "No relevant conversation history."
            if memory_manager.enabled:
                # 1. Search for relevant memories
                relevant_memories = memory_manager.search(query=transcript, user_id=USER_ID, session_id=session_id)
                if relevant_memories:
                    # Format memories for the prompt
                    memories_str = "\n".join(f"- {m['memory']}" for m in relevant_memories)
                    app_logger.info(f"Found {len(relevant_memories)} relevant memories.")

            # Process transcript with LLM to determine which tool to call
            tool_call = llm_client.process_transcript(transcript, system_prompt, available_tools, memories=memories_str)
            
            # Handle the tool call result
            if tool_call:
                tool_name = tool_call.get("tool_name")
                parameters = tool_call.get("parameters", {})
                
                app_logger.info(f"🧠 LLM decision: {tool_name} with parameters: {parameters}")
                
                # Execute the tool call
                execution_result = execute_tool_call(
                    tool_registry, 
                    tts_client, 
                    tool_call,
                    memory_manager=memory_manager,
                    user_id=USER_ID,
                    session_id=session_id,
                    original_transcript=transcript
                )
                
                # --- Memory Integration ---
                if memory_manager.enabled:
                    # 2. Add a simplified summary of the exchange to memory
                    assistant_response = execution_result.get('feedback', 'OK.')
                    
                    # Create a natural language summary for the assistant's turn to avoid confusing mem0's internal LLM.
                    if tool_name == 'speak_response':
                        # For direct speech, the assistant's message is the memory.
                        summary = assistant_response
                    else:
                        # For tool calls, create a descriptive summary.
                        summary = f"In response to the user, I executed the '{tool_name}' tool. The result was: {assistant_response}"

                    messages = [
                        {"role": "user", "content": transcript},
                        {"role": "assistant", "content": summary}
                    ]
                    memory_manager.add(messages, user_id=USER_ID, session_id=session_id)

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
                    elif tool_name == "speak_response":
                        app_logger.info("🗣️ Informational response provided")
                    elif tool_name == "unknown_request":
                        app_logger.info("❓ Unknown request handled")
                else:
                    app_logger.error("❌ Command execution failed")
                    
            else:
                app_logger.warning("No tool call was generated from the transcript.")
                
            # Small delay before starting to listen for wake word again
            app_logger.info("⏳ Ready for next command...")
            time.sleep(0.5)
            
    #except KeyboardInterrupt:
    #    app_logger.info("Keyboard interrupt received. Shutting down...")
    #except Exception as e:
    #    app_logger.error(f"Unexpected error in main loop: {e} - {e.__traceback__}", exc_info=True)
    #finally:
   #     app_logger.info("Home Assistant voice control system stopped.")

def main():
    """Entry point for the application."""
    if True:
    #try:
        # Determine config path
        config_path = "config.json"
        if len(sys.argv) > 1:
            config_path = sys.argv[1]
            
        # Load settings
        settings = load_settings(config_path=config_path)
        run_voice_assistant(settings)
        
    #except FileNotFoundError as e:
    #    app_logger.error(f"Configuration error: {e}")
    #    print(f"ERROR: {e}. Please ensure config.json exists and is properly configured.")
    #    sys.exit(1)
    #except Exception as e:
    #    app_logger.error(f"Startup error: {e}", exc_info=True)
    #    print(f"ERROR: Failed to start application: {e}")
    #    sys.exit(1)

if __name__ == "__main__":
    main() 