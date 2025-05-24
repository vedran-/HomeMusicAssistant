# Home Assistant Voice Control System - MVP Implementation Plan

## Overview
This document outlines the MVP implementation plan for a voice-controlled system. It listens for "hey jarvis", transcribes speech via Groq Cloud, and executes system commands using AutoHotkey tools. This version prioritizes simplicity, direct installation of `openwakeword` (no Docker), microphone selection, and leverages the existing `music_controller.ahk`.

## Architecture (MVP)

### System Components
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Wake Word     │───▶│   Main App       │───▶│   Tool Engine   │
│ (Direct Install)│    │   (Python)       │    │  (AutoHotkey)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   Groq Cloud     │
                       │  (Whisper LLM)   │
                       └──────────────────┘
```

### Project Structure (MVP)
```
HomeAssistant/
├── docs/
│   ├── TODO.md
│   └── plan.md
├── src/
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── wake_word.py        # openwakeword direct integration
│   │   └── capture.py          # Audio capture with microphone selection
│   ├── transcription/
│   │   ├── __init__.py
│   │   └── groq_client.py      # Groq whisper integration
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py           # LiteLLM integration
│   │   └── prompts.py          # System prompts and tool definitions for LLM
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py         # Tool registration and AHK script execution
│   │   ├── music_controller.ahk  # Existing tool
│   │   └── system_control.ahk  # For sleep, etc. (to be created)
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py         # Configuration management (paths, API keys, mic selection)
│   │   └── validation.py       # Setup validation
│   └── main.py                 # Application entry point & orchestrator
├── tools/
│   └── music_controller.md     # Documentation for existing tool
├── scripts/
│   ├── setup.ps1               # Main installation script (Python, openwakeword, AHK libs if needed)
│   ├── install_dependencies.ps1 # (Potentially merged into setup.ps1 or called by it)
│   └── validate_setup.ps1      # Script to check if all components are ready
├── requirements.txt            # Python dependencies
├── config.template.json        # Configuration template
├── .env.template               # Environment variables template
└── README.md
```

## MVP Implementation Phases

### Phase 1: Core Infrastructure & Setup
**Objective**: Establish the development environment, essential configurations, and install core non-Docker dependencies.

**Tasks**:
- [ ] **Project Setup**:
    - [ ] Initialize Git repository.
    - [ ] Create the directory structure as defined above.
- [ ] **Python Environment**:
    - [ ] Create `requirements.txt` with initial packages:
        - [ ] `litellm`
        - [ ] `pyaudio` (for audio I/O)
        - [ ] `openwakeword` (or its dependencies if it's a direct script/library)
        - [ ] `pydantic` (for configuration)
        - [ ] `python-dotenv` (for .env file handling)
        - [ ] `loguru` (for structured logging)
    - [ ] Create a virtual environment.
    - [ ] Install dependencies from `requirements.txt`.
- [ ] **AutoHotkey Setup**:
    - [ ] Confirm AutoHotkey v2 is installed and path is known. (User confirmed pre-installed)
    - [ ] Confirm `music_controller.ahk` is in `src/tools/`. (User confirmed pre-existing)
    - [ ] Ensure UIAutomation v2 libraries (`Lib\UIA.ahk`, `Lib\UIA_Browser.ahk`) are available to AHK scripts, likely within `src/tools/Lib/`.
- [ ] **Configuration System (`src/config/`)**:
    - [ ] Design `config.template.json` including:
        - [ ] Groq API key placeholder.
        - [ ] LiteLLM provider/model placeholders.
        - [ ] Audio input device index (for microphone selection).
        - [ ] Path to AutoHotkey executable.
        - [ ] Path to `openwakeword` models.
    - [ ] Create `settings.py` to load and validate configuration using Pydantic.
    - [ ] Create `.env.template` for API keys.
- [ ] **Basic Logging**:
    - [ ] Implement initial Loguru setup in `main.py` or a dedicated logging module.
- [ ] **Setup Scripts (`scripts/`)**:
    - [ ] Develop `setup.ps1` to:
        - [ ] Check for Python 3.9+ installation.
        - [ ] Guide user to install Python if not present.
        - [ ] Automate virtual environment creation.
        - [ ] Install Python dependencies from `requirements.txt`.
        - [ ] Guide user for `openwakeword` model downloads if manual.
        - [ ] Verify AutoHotkey installation (path can be prompted or pre-configured).
    - [ ] Develop `validate_setup.ps1` to check:
        - [ ] Python dependencies installed.
        - [ ] `openwakeword` models accessible.
        - [ ] AutoHotkey executable found.
        - [ ] Configuration file exists (copied from template).

### Phase 2: Audio Pipeline & LLM Core
**Objective**: Implement wake word detection, audio capture with microphone selection, transcription, and initial LLM processing.

**Tasks**:
- [ ] **Wake Word Detection (`src/audio/wake_word.py`)**:
    - [ ] Integrate `openwakeword` as a direct Python library/process.
    - [ ] Load "hey jarvis" model.
    - [ ] Implement a function/class to start listening and yield a boolean upon wake word detection.
- [ ] **Audio Capture (`src/audio/capture.py`)**:
    - [ ] Implement microphone listing using PyAudio to get available input devices.
    - [ ] Allow selection of the microphone via `config.json` (device index).
    - [ ] Implement real-time audio capture after wake word.
    - [ ] Implement silence detection to determine end of speech.
    - [ ] Prepare audio data (e.g., WAV format) for transcription.
- [ ] **Transcription (`src/transcription/groq_client.py`)**:
    - [ ] Implement client for Groq Cloud's whisper-large-v3 API.
    - [ ] Send captured audio for transcription.
    - [ ] Handle API responses and errors.
- [ ] **LLM Integration (`src/llm/`)**:
    - [ ] Implement `client.py` for LiteLLM:
        - [ ] Load API keys and model configuration from settings.
        - [ ] Function to send transcription and prompt to LLM.
    - [ ] Develop `prompts.py`:
        - [ ] Create a system prompt that instructs the LLM on its role.
        - [ ] Define available tools (initially `music_controller.ahk` functions, and a placeholder for `system_control.ahk`).
        - [ ] Provide examples of how to format the output for tool calls (e.g., JSON with `tool_name` and `parameters`).
- [ ] **Main Orchestration (Initial) (`src/main.py`)**:
    - [ ] Wire together: Wake Word -> Audio Capture -> Transcription -> LLM.
    - [ ] Print LLM response (tool call request) to console.

### Phase 3: Tool Creation & Execution
**Objective**: Integrate the existing music tool and create the system control tool, enabling the LLM to execute them.

**Tasks**:
- [ ] **Tool Registry & Execution (`src/tools/registry.py`)**:
    - [ ] Implement a function to parse LLM output (expected JSON for tool calls).
    - [ ] Implement a mechanism to call AutoHotkey scripts:
        - [ ] Pass command and parameters to the AHK script (e.g., `AutoHotkey.exe script.ahk command param1 param2`).
        - [ ] Capture output/errors from AHK scripts.
    - [ ] Register the `music_controller.ahk` tool:
        - [ ] Map LLM tool names (e.g., "playMusic", "setVolume") to `music_controller.ahk` commands.
- [ ] **System Control Tool (`src/tools/system_control.ahk`)**:
    - [ ] Create `system_control.ahk` with functions for:
        - [ ] Putting the system to sleep (`Sleep` command or `DllCall("PowrProf.dll", "SetSuspendState", "int", 0, "int", 0, "int", 0)`).
        - [ ] Other potential controls (e.g., shutdown, volume - if not fully covered by music_controller).
    - [ ] Ensure it accepts command-line arguments similar to `music_controller.ahk`.
    - [ ] Register this tool in `src/tools/registry.py` and update `src/llm/prompts.py`.
- [ ] **Main Orchestration (Full) (`src/main.py`)**:
    - [ ] Integrate tool execution: LLM Response -> Tool Parser -> AHK Caller.
    - [ ] Provide feedback to the user (e.g., "Playing music", "Going to sleep").

### Phase 4: MVP Testing & Refinement
**Objective**: Ensure all components work together reliably for the MVP scope.

**Tasks**:
- [ ] **End-to-End Testing**:
    - [ ] Test wake word detection with different microphone settings.
    - [ ] Test transcription accuracy with various phrases.
    - [ ] Test music control commands (play, toggle, volume up/down, mute/unmute via `music_controller.ahk`).
    - [ ] Test system sleep command via `system_control.ahk`.
- [ ] **Error Handling & Robustness**:
    - [ ] Review error handling in each module (audio, transcription, LLM, tool execution).
    - [ ] Ensure graceful recovery or clear error messages for common issues (API errors, AHK script failures, mic issues).
- [ ] **Configuration & Usability**:
    - [ ] Test the `setup.ps1` and `validate_setup.ps1` scripts.
    - [ ] Ensure microphone selection is clear and works.
    - [ ] Document basic usage in `README.md`.
- [ ] **Code Review & Cleanup**:
    - [ ] Review code for clarity, simplicity, and adherence to the plan.
    - [ ] Remove any unused code or placeholders not relevant to MVP.

## Future Scope (Post-MVP)
- Text-to-speech (TTS) feedback (e.g., Piper).
- Home Assistant integration for device control.
- More sophisticated conversation management.
- Expanded toolset.
- GUI for configuration/status.

This revised plan focuses on delivering a functional MVP by simplifying dependencies and leveraging existing components. 