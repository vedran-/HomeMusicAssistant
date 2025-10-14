from litellm import completion
import litellm
from typing import Dict, Any, Optional, List
import json
import time
import random
import re

from src.config.settings import AppSettings
from src.utils.logger import app_logger

class LiteLLMClient:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.provider = settings.litellm_settings.provider
        self.model = settings.litellm_settings.model
        self.api_key = settings.litellm_settings.api_key
        
        app_logger.info("LiteLLMClient initialized with model: %s", self.model)
        
        # Retry configuration
        self.max_retries = 3
        self.base_delay = 2.0  # Base delay in seconds (quick retries for real-time feel)
        self.max_delay = 10.0  # Maximum delay in seconds (keep it short for UX)
        self.rate_limit_delay = 5.0  # Quick delay for rate limit errors (real-time UX)
        
        # Enable debug mode if needed (can be controlled via environment or config)
        self.debug_mode = getattr(settings.litellm_settings, 'debug_mode', False)
        if self.debug_mode:
            litellm.set_verbose = True
            app_logger.info("LiteLLM debug mode enabled")
        
        # API key for LiteLLM may be optional if using local models
        if not self.api_key and self.provider not in ["local"]:
            app_logger.warning(f"No API key provided for LiteLLM provider '{self.provider}'. Some providers require an API key.")

    def _calculate_delay(self, attempt: int, is_rate_limit: bool = False) -> float:
        """Calculate exponential backoff delay with jitter"""
        if is_rate_limit:
            # For rate limit errors, use a shorter fixed delay with jitter for real-time UX
            base_delay = self.rate_limit_delay
            jitter = random.uniform(0.1, 0.3) * base_delay  # Reduced jitter for shorter delays
            return base_delay + jitter
        else:
            # Standard exponential backoff
            delay = min(self.base_delay * (2 ** attempt), self.max_delay)
            # Add jitter to prevent thundering herd
            jitter = random.uniform(0.1, 0.2) * delay  # Reduced jitter for shorter delays
            return delay + jitter

    def _is_rate_limit_error(self, exception: Exception) -> bool:
        """Check if the exception is a rate limit error"""
        error_str = str(exception).lower()
        return any(phrase in error_str for phrase in [
            'rate limit', 'ratelimit', 'rate_limit', 
            'too many requests', 'quota exceeded',
            'tokens per minute', 'tpm'
        ])

    def _create_rate_limit_fallback_response(self) -> Dict[str, Any]:
        """Create a fallback response when rate limits are exceeded"""
        fallback_messages = [
            "I'm experiencing high demand right now. Please wait a few seconds and try again.",
            "The AI service is temporarily busy. Please try your request again in a moment.",
            "I'm currently rate limited. Please wait a few seconds before making another request.",
            "The system is experiencing high traffic. Please try again shortly."
        ]
        
        # Pick a random message to avoid repetition
        message = random.choice(fallback_messages)
        
        return {
            "tool_name": "speak_response",
            "parameters": {"message": message}
        }

    def _make_llm_call(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]) -> Any:
        """Make a single LiteLLM API call with proper error handling"""
        try:
            response = completion(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",  # Let the model decide whether to use tools
                api_key=self.api_key if self.api_key else None,
                temperature=0.1  # Lower temperature for more deterministic responses
            )
            return response
        except Exception as e:
            # Log the specific error for debugging
            app_logger.error(f"LiteLLM API call failed: {type(e).__name__}: {e}")
            raise

    @staticmethod
    def extract_tool_call_info(tool_call_rsp: str):
        if '<|tool_calls_section_begin|>' not in tool_call_rsp:
            return []
        pattern = r"<\|tool_calls_section_begin\|>(.*?)<\|tool_calls_section_end\|>"
        tool_calls_sections = re.findall(pattern, tool_call_rsp, re.DOTALL)
        func_call_pattern = r"(?P<tool_call_id>[\w\.]+\:\d+)\s*<\|tool_call_argument_begin\|>\s*(?P<function_arguments>.*?)\s*<\|tool_call_end\|>"
        tool_calls = []
        for match in re.findall(func_call_pattern, tool_calls_sections[0], re.DOTALL):
            function_id, function_args = match
            function_name = function_id.split('.')[1].split(':')[0]
            tool_calls.append(
                {
                    "id": function_id,
                    "type": "function",
                    "function": {
                        "name": function_name,
                        "arguments": function_args
                    }
                }
            )  
        return tool_calls

    def process_transcript(self, transcript: str, system_prompt: str, tools: List[Dict[str, Any]], memories: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Send transcribed text to an LLM for processing with provided system prompt and tools.
        Includes retry logic for robustness.
        
        Args:
            transcript: The transcribed text from the user's speech
            system_prompt: System prompt that instructs the LLM on its role
            tools: List of tool definitions that the LLM can use in its response
            memories: Optional string containing relevant past conversation snippets.
            
        Returns:
            Dict containing the tool call information or None if processing failed
        """
        app_logger.info("Entering process_transcript with transcript: %s", transcript[:50])
        if not transcript:
            app_logger.warning("Empty transcript provided to LLM client.")
            return None
        
        # Format the system prompt with memories if they exist
        final_system_prompt = system_prompt.format(memories=memories or "No relevant conversation history.")
            
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": final_system_prompt},
            {"role": "user", "content": f"Transcript: {transcript}\n\nRelevant memories:\n{memories}\n\nBased on this, decide which tool to call. If it's a user preference or something to remember long-term, note it in your response."}
        ]
        
        # Retry logic with exponential backoff
        last_exception = None
        rate_limit_failures = 0  # Track consecutive rate limit failures
        for attempt in range(self.max_retries):
            try:
                app_logger.info(f"Sending transcript to LLM ({self.provider}/{self.model}) - Attempt {attempt + 1}/{self.max_retries}: '{transcript}'")
                
                # Make the API call to LiteLLM
                response = self._make_llm_call(messages, tools)
                
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
                        return None
                        #return {
                        #    "tool_name": "speak_response",
                        #    "parameters": {"message": text_response}
                        #}
                    return None
                    
            except Exception as e:
                last_exception = e
                is_rate_limit = self._is_rate_limit_error(e)
                
                if is_rate_limit:
                    rate_limit_failures += 1
                    app_logger.warning(f"LLM call attempt {attempt + 1}/{self.max_retries} failed due to rate limiting: {e}")
                    
                    # If we've had multiple rate limit failures, return fallback response immediately
                    if rate_limit_failures >= 2:
                        app_logger.info("Multiple rate limit failures detected. Returning fallback response for better UX.")
                        return self._create_rate_limit_fallback_response()
                else:
                    app_logger.warning(f"LLM call attempt {attempt + 1}/{self.max_retries} failed: {type(e).__name__}: {e}")
                    
                    error_str = str(e).lower()
                    if 'badrequesterror' in error_str and 'failed_generation' in error_str:
                        # Extract failed_generation from error message
                        try:
                            failed_gen_start = error_str.find('"failed_generation":"') + 21
                            failed_gen_end = error_str.rfind('"}')
                            if failed_gen_start > 20 and failed_gen_end > 0:
                                failed_generation = error_str[failed_gen_start:failed_gen_end].replace('\\', '')
                                tool_calls = self.extract_tool_call_info(failed_generation)
                                if tool_calls:
                                    # Take first tool call
                                    tc = tool_calls[0]
                                    arguments = json.loads(tc['function']['arguments'])
                                    tool_response = {
                                        "tool_name": tc['function']['name'],
                                        "parameters": arguments
                                    }
                                    app_logger.info(f"Parsed Kimi tool call: {tool_response}")
                                    return tool_response
                        except Exception as parse_e:
                            app_logger.error(f"Failed to parse Kimi failed_generation: {parse_e}")
                
                # If this is the last attempt, check if it's a rate limit issue
                if attempt >= self.max_retries - 1:
                    if is_rate_limit:
                        app_logger.info("Final attempt failed due to rate limiting. Returning fallback response.")
                        return self._create_rate_limit_fallback_response()
                    else:
                        app_logger.error(f"All {self.max_retries} LLM call attempts failed. Last error:", exc_info=True)
                        break
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt, is_rate_limit)
                if is_rate_limit:
                    app_logger.info(f"Rate limit detected. Retrying in {delay:.2f} seconds...")
                else:
                    app_logger.info(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
        
        # If we get here, all retries failed
        app_logger.error(f"Failed to process transcript after {self.max_retries} attempts.", exc_info=True)
        return None

    def get_completion(self, messages: List[Dict[str, Any]], temperature: float = 0.3, max_tokens: int = 1000) -> Optional[str]:
        """
        Get a simple text completion without tool calling.
        Used by agentic tools that need multi-step LLM processing.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (default 0.3 for focused answers)
            max_tokens: Maximum response length
            
        Returns:
            Text response or None on failure
        """
        app_logger.info(f"Getting LLM completion (multi-step agentic call) with {len(messages)} messages")
        
        try:
            response = completion(
                model=self.model,
                messages=messages,
                api_key=self.api_key if self.api_key else None,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if not response or not response.choices:
                app_logger.error("LLM completion returned empty response")
                return None
            
            first_choice = response.choices[0]
            
            if hasattr(first_choice, 'message') and hasattr(first_choice.message, 'content'):
                text_response = first_choice.message.content
                app_logger.info(f"LLM completion successful: {len(text_response)} characters")
                return text_response
            else:
                app_logger.error("LLM completion response missing content")
                return None
                
        except Exception as e:
            app_logger.error(f"LLM completion failed: {type(e).__name__}: {e}", exc_info=True)
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