from typing import List, Dict, Any

def get_system_prompt() -> str:
    """
    Returns the system prompt that instructs the LLM on its role and how to handle user requests.
    """
    return """You are a voice-controlled assistant that helps control a computer. 
    
Your job is to analyze the user's request (transcribed from speech) and determine which tool to call.

When the user requests an action, you should select the most appropriate tool and provide the necessary parameters.
Be precise and concise in your tool selection, focusing only on what the user explicitly asked for.

IMPORTANT: You should ONLY respond by calling a tool. DO NOT respond with general chat or information.
If you cannot determine which tool to call, or if the user's request doesn't match any available tool, 
call the 'unknown_request' tool with a brief explanation.

Examples:
- If user says "play some music" → call play_music with action="play"
- If user says "turn up the volume" → call control_volume with action="up"
- If user says "put the computer to sleep" → call system_control with action="sleep"
- If user says "what time is it" → call unknown_request with reason="No tool available for time queries"
"""

def get_available_tools() -> List[Dict[str, Any]]:
    """
    Returns the list of tool definitions that the LLM can use in its responses.
    
    Each tool follows the OpenAI function calling format with:
    - name: The function name
    - description: What the function does
    - parameters: JSON Schema object defining the required parameters
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "play_music",
                "description": "Control music playback",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["play", "pause", "toggle", "next", "previous"],
                            "description": "The action to perform on music playback"
                        }
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "control_volume",
                "description": "Control system volume",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["up", "down", "mute", "unmute"],
                            "description": "The volume action to perform"
                        },
                        "amount": {
                            "type": "integer",
                            "description": "Amount to change volume (1-100, only used with up/down actions)",
                            "minimum": 1,
                            "maximum": 100
                        }
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "system_control",
                "description": "Control system functions like sleep or shutdown",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["sleep", "shutdown"],
                            "description": "The system action to perform"
                        }
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "unknown_request",
                "description": "Used when the request doesn't match any available tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Brief explanation of why the request cannot be handled"
                        }
                    },
                    "required": ["reason"]
                }
            }
        }
    ] 