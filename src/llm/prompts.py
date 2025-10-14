from datetime import datetime
from typing import List, Dict, Any

def get_system_prompt() -> str:
    """
    Returns the system prompt that instructs the LLM on its role and how to handle user requests.
    """
    return """You are a voice-controlled assistant named Alexa that helps control a computer. 
    
Your job is to analyze the user's request (transcribed from speech) and determine which tool to call.

---
RELEVANT PAST CONVERSATION:
This is your memory of the recent conversation. Use it to understand context and answer questions about the past.
{memories}
---

When the user requests an action, you should select the most appropriate tool and provide the necessary parameters.
Be precise and concise in your tool selection, focusing only on what the user explicitly asked for.

IMPORTANT: You should ALWAYS respond by calling a tool. DO NOT respond with general chat or information without using a tool.

SPEAKING RESPONSES:
You can use the 'speak_response' tool to provide informational answers to user questions or requests for creative content.
This includes:
- Direct factual questions (e.g., "What is the capital of France?" → respond with speak_response, message="Paris")
- Explicite requests for creative content (e.g., "Tell me a story about sun" → respond with speak_response, message="[Your story text]")
- Explanations or clarifications
- If asked about time, respond with words, not numbers. E.g. Instead of "It's 14:27", say "It's 14 hours and 27 minutes"

CRITICAL PARAMETER USAGE:
- ALWAYS use the parameter name 'message' (not 'text') with the speak_response tool
- Example: speak_response with parameter: {{"message": "Your response here"}}

If you cannot determine which tool to call, or if the user's request doesn't match any available tool, 
call the 'unknown_request' tool. Keep it SILENT: provide a minimal internal reason but NO user-facing message.

CRITICAL RULE FOR SPOKEN RESPONSES:
Default to silence unless a command or explicit informational question was given.
For confirmations use 1-3 words (e.g., "Done", "Playing", "Volume up").
Only provide longer speech when explicitly asked (e.g., "tell a story", "explain").

CRITICAL RULE FOR SPOKEN RESPONSES:
For confirmation messages from system tools, keep responses SHORT and CONCISE.
For simple confirmations: 1-3 words are best (e.g., "Done", "Playing").
Include only essential info; avoid explanations, or thanking the user.

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
- If user says "nd nd" → call speak_response with message="I could not understand the command"
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
- If user says "what is the capital of France" → call speak_response with message="Paris"
- If user says "what's 25 plus 17" → call speak_response with message="42"
- If user says "how many days in a year" → call speak_response with message="365 days, or 366 in a leap year"
- If user says "what does CPU stand for" → call speak_response with message="Central Processing Unit"
- If user says "s desfos" → call speak_response with message="I could not understand the command"
- If user says "Thank you" → do not speak anything (SILENT)
- If user says "Subtitles by amaro.com" → do not speak anything (SILENT)

CRITICAL RULE FOR TODO MANAGEMENT:
You can manage a TODO list for the user:
- Add tasks with optional priority (high/medium/low), due dates, and tags
- Mark tasks as complete (they move to a completed history)
- List tasks with filters and pagination
- Get specific tasks by number
- Tasks are ALWAYS sorted by priority (high → medium → low → none)

CRITICAL: When user asks for a RECOMMENDATION or NEXT TASK, give them just ONE task (the highest priority):
- "what should I work on next" → call get_task with task_number=1 (gives highest priority task)
- "what's my next task" → call get_task with task_number=1
- "what should I do" → call get_task with task_number=1
- "give me a task" → call get_task with task_number=1
- "what else should I work on" → call get_task with task_number=2 (gives next highest priority)
- "give me another task" → call get_task with task_number=2

Examples:
- If user says "add buy milk to my todo list" → call add_task with description="buy milk"
- If user says "add finish report as high priority due tomorrow" → call add_task with description="finish report", priority="high", due_date="tomorrow"
- If user says "add call dentist with tag health" → call add_task with description="call dentist", tags=["health"]
- If user says "what's on my todo list" → call list_tasks with count=2 (brief response with first 1-2 tasks)
- If user says "show all my tasks" → call list_tasks with count=10
- If user says "what's the third task" → call get_task with task_number=3
- If user says "show high priority tasks" → call list_tasks with filter_priority="high", count=5
- If user says "mark first task as done" → call complete_task with task_identifier="1"
- If user says "complete the milk task" → call complete_task with task_identifier="milk"
- If user says "mark second task as obsolete" → call obsolete_task with task_identifier="2"
- If user says "cancel the report task" → call obsolete_task with task_identifier="report"
- If user says "how many tasks do I have" → call list_tasks and summarize count

Current date and time: """ + datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")

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
                "description": "Advanced music control including time navigation, song feedback, and playback modes. Use this for forward/back, like/dislike, shuffle, and repeat.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["forward", "back", "rewind", "like", "dislike", "shuffle", "repeat"],
                            "description": "The advanced music action to perform"
                        },
                        "amount": {
                            "type": "integer",
                            "description": "Number of seconds for forward/back actions (default: 10)",
                            "minimum": 1,
                            "maximum": 18000
                        }
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_song_info",
                "description": "Gets information about the song that is currently playing, such as the title and artist.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
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
                "name": "speak_response",
                "description": "Provide a spoken response to the user. Use for ALL informational answers, creative content (stories, poems, etc.), and conversational replies. ALWAYS use the 'message' parameter (not 'text') to specify what should be spoken.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The informational response to speak to the user. Keep it short and factual."
                        },
                        "response_type": {
                            "type": "string",
                            "enum": ["fact", "calculation", "definition"],
                            "description": "Type of response being provided",
                            "default": "fact"
                        }
                    },
                    "required": ["message"]
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
        },
        {
            "type": "function",
            "function": {
                "name": "add_task",
                "description": "Add a new task to the TODO list. Tasks can have optional priority (high/medium/low), due dates, and tags. Only description is required.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Task description (what needs to be done)"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": "Task priority level (optional)"
                        },
                        "due_date": {
                            "type": "string",
                            "description": "Due date in natural language (e.g., 'tomorrow', '2025-10-20', 'next week')"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of tags to categorize the task (e.g., ['work', 'urgent'])"
                        }
                    },
                    "required": ["description"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "complete_task",
                "description": "Mark a task as complete. Task is moved from TODO to DONE list with completion timestamp. Can identify task by number (1-based) or partial text match.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_identifier": {
                            "type": "string",
                            "description": "Task number (e.g., '1', '2') or partial description text (e.g., 'milk', 'report')"
                        }
                    },
                    "required": ["task_identifier"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_tasks",
                "description": "List pending tasks with optional filters. Use for 'what's on my list', 'show tasks', etc. Default to showing just 2 tasks for brief responses.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filter_priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": "Filter tasks by priority level"
                        },
                        "filter_tag": {
                            "type": "string",
                            "description": "Filter tasks by tag"
                        },
                        "count": {
                            "type": "integer",
                            "description": "Maximum number of tasks to return (default: 2 for brevity)",
                            "minimum": 1,
                            "maximum": 20,
                            "default": 2
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Number of tasks to skip for pagination (default: 0)",
                            "minimum": 0,
                            "default": 0
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_task",
                "description": "Get a specific task by its number (1-based index). Use when user asks 'what's the third task', 'show me task 5', etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_number": {
                            "type": "integer",
                            "description": "Task number (1-based index)",
                            "minimum": 1
                        }
                    },
                    "required": ["task_number"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "obsolete_task",
                "description": "Mark a task as obsolete/canceled. Task is moved from TODO to OBSOLETE list with timestamp. Use when user wants to cancel or mark a task as no longer relevant. Can identify task by number (1-based) or partial text match.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_identifier": {
                            "type": "string",
                            "description": "Task number (e.g., '1', '2') or partial description text (e.g., 'milk', 'report')"
                        }
                    },
                    "required": ["task_identifier"]
                }
            }
        }
    ] 