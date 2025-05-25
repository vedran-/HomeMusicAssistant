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

CRITICAL RULE FOR MUSIC: 
Whenever the user says "play" followed by a search query, always use the play_music tool with action="play" and the search_term.
If the user explicitly mentions "radio" (e.g., "play Pink Floyd radio"), set play_type="radio".
Otherwise, for general play requests (e.g., "play Pink Floyd"), use play_type="default" or omit it.
Do NOT use unknown_request for play commands - the music system can search for anything.

Examples:
- If user says "play some music" → call play_music with action="play" (play_type can be omitted or "default")
- If user says "play Boards of Canada" → call play_music with action="play", search_term="Boards of Canada" (play_type can be omitted or "default")
- If user says "play Boards of Canada radio" → call play_music with action="play", search_term="Boards of Canada", play_type="radio"
- If user says "start radio for The Cure" → call play_music with action="play", search_term="The Cure", play_type="radio"
- If user says "play Magazines" → call play_music with action="play", search_term="Magazines", play_type="default"
- If user says "play rock music radio" → call play_music with action="play", search_term="rock music", play_type="radio"
- If user says "play that song from the movie" → call play_music with action="play", search_term="that song from the movie", play_type="default"
- If user says "play anything radio" → call play_music with action="play", search_term="anything", play_type="radio"
- If user says "play The Beatles" → call play_music with action="play", search_term="The Beatles" (play_type can be omitted or "default")
- If user says "next song" → call play_music with action="next"
- If user says "skip next three songs" → call play_music with action="next", count=3
- If user says "previous song" → call play_music with action="previous" 
- If user says "go back two songs" → call play_music with action="previous", count=2
- If user says "go back 30 seconds" → call music_control with action="back", amount=30
- If user says "like this song" → call music_control with action="like"
- If user says "turn on shuffle" → call music_control with action="shuffle"
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
                "description": "Play music or start a radio based on user request. Accepts ANY search term. Use 'play_type' to specify if a radio should be started. ALWAYS use this tool when user says 'play' followed by a search query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["play", "pause", "toggle", "next", "previous"],
                            "description": "The action to perform. For playing content or starting a radio with a search term, always use 'play'."
                        },
                        "search_term": {
                            "type": "string",
                            "description": "What to play or base the radio on - can be ANYTHING: artist name, song title, genre, album, etc."
                        },
                        "play_type": {
                            "type": "string",
                            "enum": ["default", "radio"],
                            "description": "Specifies the playback mode. Use 'radio' if the user explicitly asks for a radio (e.g., 'play X radio'). Otherwise, use 'default' or omit for standard playback (usually shuffle/play).",
                            "default": "default"
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of songs to skip (only for next/previous actions). Default: 1.",
                            "minimum": 1,
                            "maximum": 10
                        }
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "music_control",
                "description": "Advanced music control including time navigation, song feedback, and playback modes. Use this for forward/back, like/dislike, shuffle, repeat, and other advanced controls.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["forward", "back", "rewind", "like", "dislike", "shuffle", "repeat", "search"],
                            "description": "The advanced music action to perform"
                        },
                        "amount": {
                            "type": "integer",
                            "description": "Number of seconds for forward/back actions (default: 10)",
                            "minimum": 1,
                            "maximum": 300
                        },
                        "search_term": {
                            "type": "string",
                            "description": "Search term for music search action"
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