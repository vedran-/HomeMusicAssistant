from litellm import completion
from typing import Dict, Any, Optional, List
import json

from src.config.settings import AppSettings
from src.utils.logger import app_logger

class LiteLLMClient:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.provider = settings.litellm_settings.provider
        self.model = settings.litellm_settings.model
        self.api_key = settings.litellm_settings.api_key
        
        # API key for LiteLLM may be optional if using local models
        if not self.api_key and self.provider not in ["local"]:
            app_logger.warning(f"No API key provided for LiteLLM provider '{self.provider}'. Some providers require an API key.")

    def process_transcript(self, transcript: str, system_prompt: str, tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Send transcribed text to an LLM for processing with provided system prompt and tools.
        
        Args:
            transcript: The transcribed text from the user's speech
            system_prompt: System prompt that instructs the LLM on its role
            tools: List of tool definitions that the LLM can use in its response
            
        Returns:
            Dict containing the tool call information or None if processing failed
        """
        if not transcript:
            app_logger.warning("Empty transcript provided to LLM client.")
            return None
            
        try:
            app_logger.info(f"Sending transcript to LLM ({self.provider}/{self.model}): '{transcript}'")
            
            # Prepare messages for the LLM
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ]
            
            # Make the API call to LiteLLM
            response = completion(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",  # Let the model decide whether to use tools
                api_key=self.api_key if self.api_key else None,
                temperature=0.1  # Lower temperature for more deterministic responses
            )
            
            # Process the response
            if not response or not response.choices:
                app_logger.error("LLM returned an empty response or no choices.")
                return None
                
            first_choice = response.choices[0]
            
            # Check if the LLM used a tool
            if hasattr(first_choice, 'message') and hasattr(first_choice.message, 'tool_calls') and first_choice.message.tool_calls:
                tool_call = first_choice.message.tool_calls[0]  # Get the first tool call
                
                # Parse the function call arguments from JSON string to dict
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    app_logger.error(f"Failed to parse tool arguments: {tool_call.function.arguments}")
                    return None
                
                tool_response = {
                    "tool_name": tool_call.function.name,
                    "parameters": arguments
                }
                
                app_logger.info(f"LLM selected tool: {tool_response['tool_name']} with parameters: {tool_response['parameters']}")
                return tool_response
                
            else:
                # The LLM didn't use a tool, but provided a text response
                text_response = first_choice.message.content if hasattr(first_choice, 'message') and hasattr(first_choice.message, 'content') else None
                app_logger.info(f"LLM provided a text response without tool call: '{text_response}'")
                
                # Return text response for TTS - this allows the assistant to speak responses
                if text_response:
                    return {
                        "tool_name": "speak_response",
                        "parameters": {"text": text_response}
                    }
                return None
                
        except Exception as e:
            app_logger.error(f"Error processing transcript with LLM: {e}", exc_info=True)
            return None


if __name__ == "__main__":
    # Basic test for the LiteLLMClient
    from src.config.settings import load_settings
    import os
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(current_dir, "..", "..", "config.json")
    
    if not os.path.exists(config_file_path):
        print(f"ERROR: config.json not found at {config_file_path}. Please create it from config.template.json.")
        config_file_path = "config.json" 
        if not os.path.exists(config_file_path):
             print(f"ERROR: config.json not found at {os.path.abspath(config_file_path)} either. Aborting test.")
             exit(1)
        else:
            print(f"Found config.json at {os.path.abspath(config_file_path)}")
    
    try:
        settings = load_settings(config_path=config_file_path)
        app_logger.info("Settings loaded for LiteLLMClient test.")
        
        if not settings.litellm_settings.api_key and settings.litellm_settings.provider not in ["local"]:
            app_logger.warning(f"No API key provided for LiteLLM provider '{settings.litellm_settings.provider}'. Test may fail.")
        
        # Sample test data
        sample_prompt = "You are an assistant that helps control a computer. When the user speaks, determine which tool to call based on their request."
        sample_tools = [
            {
                "type": "function",
                "function": {
                    "name": "play_music",
                    "description": "Play, pause, or control music playback",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string", 
                                "enum": ["play", "pause", "next", "previous", "volume_up", "volume_down"],
                                "description": "The action to perform on music playback"
                            }
                        },
                        "required": ["action"]
                    }
                }
            }
        ]
        
        # Test with a simple transcript
        llm_client = LiteLLMClient(settings)
        test_transcript = "Play some music please"
        
        app_logger.info(f"Testing LiteLLMClient with transcript: '{test_transcript}'")
        result = llm_client.process_transcript(test_transcript, sample_prompt, sample_tools)
        
        if result:
            app_logger.info(f"LLM test successful: {result}")
        else:
            app_logger.warning("LLM test did not return a tool call result.")
            
    except Exception as e:
        app_logger.error(f"An error occurred during LiteLLMClient test: {e}", exc_info=True) 