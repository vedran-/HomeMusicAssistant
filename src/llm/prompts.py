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

CRITICAL RULE FOR SPOKEN RESPONSES:
When tools provide feedback that will be spoken aloud via text-to-speech, keep the feedback text SHORT and CONCISE.
Aim for 1-3 words when possible (e.g., "Done", "Playing music", "Volume up"), but include essential information.
Avoid long explanations or technical details in spoken feedback - users prefer quick confirmations.
However, don't make responses so short that they lose important information (e.g., "Volume set to 75%" is better than just "Done").

CRITICAL RULE FOR VOLUME CONTROL:
- STRONGLY PREFER RELATIVE CHANGES: Almost all volume requests should use action="up" or "down"
- For RELATIVE changes (increase/decrease BY X): use action="up" or "down" with amount=X
- For ABSOLUTE settings (set TO X): use action="set" with amount=X ONLY when explicitly requested
- Pay attention to keywords: "by", "increase by", "decrease by", "up by", "down by" = relative change
- Mathematical expressions: "half", "double", "quarter" = relative change (50%, 100%, 25%)
- Pay attention to keywords: "to", "set to", "volume to", "make it exactly" = absolute setting
- DEFAULT TO RELATIVE: When in doubt, use "up" or "down" rather than "set"

CRITICAL RULE FOR MUSIC: 
Whenever the user says "play" followed by a search query, always use the play_music tool with action="play" and the search_term.
If the user explicitly mentions "radio" (e.g., "play Pink Floyd radio"), set play_type="radio".
Otherwise, for general play requests (e.g., "play Pink Floyd"), use play_type="default" or omit it.
Do NOT use unknown_request for play commands - the music system can search for anything.

CRITICAL RULE FOR TIME:
When the user asks for the current time, date, or "what time is it", use the get_time tool.

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
- If user says "increase volume by 20" → call control_volume with action="up", amount=20
- If user says "turn volume up 30%" → call control_volume with action="up", amount=30
- If user says "make it louder by 15" → call control_volume with action="up", amount=15
- If user says "turn down the volume" → call control_volume with action="down"
- If user says "decrease volume by 25" → call control_volume with action="down", amount=25
- If user says "lower volume by 10%" → call control_volume with action="down", amount=10
- If user says "decrease the volume on half" → call control_volume with action="down", amount=50
- If user says "cut the volume in half" → call control_volume with action="down", amount=50
- If user says "make it half as loud" → call control_volume with action="down", amount=50
- If user says "double the volume" → call control_volume with action="up", amount=100
- If user says "quarter the volume" → call control_volume with action="down", amount=75
- If user says "reduce volume to half" → call control_volume with action="down", amount=50
- If user says "set volume to exactly 50" → call control_volume with action="set", amount=50
- If user says "make volume exactly 75%" → call control_volume with action="set", amount=75
- If user says "put the computer to sleep" → call system_control with action="sleep"
- If user says "restart the computer" → call system_control with action="restart"
- If user says "what time is it" → call get_time
- If user says "what's the current time" → call get_time
- If user says "tell me the time" → call get_time
- If user says "what's today's date" → call get_time with include_date=true
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
                "description": "Control system volume. PREFER 'up'/'down' for RELATIVE changes (increase/decrease BY amount). Use 'set' for ABSOLUTE levels ONLY when explicitly requested with words like 'exactly', 'set to', etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["up", "down", "set", "mute", "unmute"],
                            "description": "The volume action: 'up' = increase BY amount, 'down' = decrease BY amount, 'set' = set TO absolute level, 'mute'/'unmute' = toggle mute"
                        },
                        "amount": {
                            "type": "integer",
                            "description": "For 'up'/'down': amount to change volume BY (1-100). For 'set': absolute volume level to set TO (0-100). Not used for mute/unmute.",
                            "minimum": 0,
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
                "description": "Control system functions like sleep, shutdown, or restart",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["sleep", "shutdown", "restart"],
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
                "name": "get_time",
                "description": "Get the current system time and optionally the date in human-friendly format (e.g., '14 hours and 27 minutes'). Use this when user asks for time, current time, or date.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_date": {
                            "type": "boolean",
                            "description": "Whether to include the current date along with time. Default: false (time only).",
                            "default": False
                        },
                        "format": {
                            "type": "string",
                            "enum": ["12hour", "24hour", "auto"],
                            "description": "Time format preference. 'auto' uses 24-hour format (default). Default: 'auto'.",
                            "default": "auto"
                        }
                    },
                    "required": []
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