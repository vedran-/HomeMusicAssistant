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
│   ├── plan.md
│   ├── README.md               # Setup and usage documentation
│   └── TESTING_RESULTS.md      # Comprehensive testing results (Phase 2)
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
│   │   ├── music_controller.ahk  # Existing tool (user to place)
│   │   └── system_control.ahk  # For sleep, etc. (to be created)
│   │   └── Lib/                  # For AHK libraries (user to place UIA libs)
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py         # Configuration management (paths, API keys, mic selection)
│   │   └── validation.py       # Setup validation (Not implemented as a Python module)
│   ├── utils/
│   │   ├── __init__.py
│   │   └── logger.py           # Logging setup
│   ├── test_transcription_llm.py   # Comprehensive testing (Phase 2)
│   ├── test_audio_capture.py       # Real audio testing (Phase 2)
│   └── main.py                 # Application entry point & orchestrator
├── tools/ # Top-level tools directory, e.g., for documentation
│   └── music_controller.md     # Documentation for existing tool
├── scripts/
│   ├── setup.ps1               # Main installation script (Python, openwakeword, AHK libs if needed)
│   ├── validate_setup.ps1      # Script to check if all components are ready
│   ├── check_config.py         # Helper for validate_setup.ps1
│   ├── check_deps.py           # Helper for validate_setup.ps1
├── requirements.txt            # Python dependencies
├── config.template.json        # Configuration template
├── .env.template               # Documented structure; user creates .env if needed
└── README.md
```

## MVP Implementation Phases

### Phase 1: Core Infrastructure & Setup ✅ COMPLETE
**Objective**: Establish the development environment, essential configurations, and install core non-Docker dependencies.

**Tasks**:
- [X] **Project Setup**:
    - [X] Initialize Git repository.
    - [X] Create the directory structure as defined above.
- [~] **Python Environment**: *(Partially complete; `setup.ps1` handles venv/installation)*
    - [X] Create `requirements.txt` with initial packages.
    - [ ] Create a Python virtual environment. *(Done by `setup.ps1`, pending user run)*
    - [ ] Install dependencies from `requirements.txt`. *(Done by `setup.ps1`, pending user run)*
- [~] **AutoHotkey Setup**: *(Partially complete; user to place actual files)*
    - [X] Confirm AutoHotkey v2 is installed and path is known. *(User confirmed pre-installed)*
    - [ ] Confirm `music_controller.ahk` is in `src/tools/`. *(Dummy created for validation; actual file pending user action)*
    - [ ] Ensure UIAutomation v2 libraries (`Lib\UIA.ahk`, `Lib\UIA_Browser.ahk`) are in `src/tools/Lib/`. *(Dummy files created for validation; actual files pending user action)*
- [~] **Configuration System (`src/config/`)**: *(Mostly complete)*
    - [X] Design `config.template.json` including API keys, paths, audio settings, mic selection. *(Corrected path format)*
    - [X] Create `settings.py` to load and validate configuration using Pydantic.
    - [ ] Create `.env.template` for API keys. *(Creation blocked by globalignore; user to create `.env` manually if needed, based on documented structure e.g. `GROQ_API_KEY=`, `LITELLM_API_KEY=`)*
    - [X] Create `src/config/__init__.py`.
- [X] **Basic Logging (`src/utils/`)**:
    - [X] Implement initial Loguru setup in `src/utils/logger.py`.
    - [X] Create `src/utils/__init__.py`.
- [X] **Setup Scripts (`scripts/`)**:
    - [X] Develop `setup.ps1` to guide Python env setup, create model dir, remind about config/AHK.
    - [X] Develop `validate_setup.ps1` to check config, Python deps, paths, AHK files (uses helper Python scripts).
    - [X] Develop `scripts/check_config.py` (helper for `validate_setup.ps1`).
    - [X] Develop `scripts/check_deps.py` (helper for `validate_setup.ps1`).

### Phase 2: Audio Pipeline & LLM Core ✅ COMPLETE (2025-05-24)
**Objective**: Implement wake word detection, audio capture with microphone selection, transcription, and initial LLM processing.

**Status**: ✅ **ALL OBJECTIVES MET** - Comprehensive testing completed with 100% success rate across all components.

**Tasks**:
- [X] **Wake Word Detection (`src/audio/wake_word.py`)**:
    - [X] Integrate `openwakeword` as a direct Python library/process.
    - [X] Load "hey jarvis" and "alexa" models (models downloaded by `openwakeword` to path in `config.json`).
    - [X] Implement a function/class to start listening and yield a boolean upon wake word detection.
    - [X] **TESTED**: Working reliably with microphone keyword selection
- [X] **Audio Capture (`src/audio/capture.py`)**:
    - [X] Implement microphone listing using PyAudio to get available input devices.
    - [X] Allow selection of the microphone via `config.json` (device index and keyword matching).
    - [X] Implement real-time audio capture after wake word.
    - [X] Implement silence detection to determine end of speech.
    - [X] Prepare audio data (e.g., WAV format) for transcription.
    - [X] **TESTED**: Microphone selection by keyword ("W2G") working perfectly
- [X] **Transcription (`src/transcription/groq_client.py`)**:
    - [X] Implement client for Groq Cloud's whisper-large-v3 API.
    - [X] Send captured audio for transcription.
    - [X] Handle API responses and errors.
    - [X] **TESTED**: 100% API connectivity, accurate transcription of real speech
- [X] **LLM Integration (`src/llm/`)**:
    - [X] Implement `client.py` for LiteLLM:
        - [X] Load API keys and model configuration from settings.
        - [X] Function to send transcription and prompt to LLM.
    - [X] Develop `prompts.py`:
        - [X] Create a system prompt that instructs the LLM on its role.
        - [X] Define available tools (initially `music_controller.ahk` functions, and a placeholder for `system_control.ahk`).
        - [X] Provide examples of how to format the output for tool calls (e.g., JSON with `tool_name` and `parameters`).
    - [X] **TESTED**: 100% tool selection accuracy, proper parameter extraction
- [X] **Main Orchestration (Initial) (`src/main.py`)**:
    - [X] Create `src/audio/__init__.py`, `src/transcription/__init__.py`, `src/llm/__init__.py`.
    - [X] Wire together: Wake Word -> Audio Capture -> Transcription -> LLM.
    - [X] Print LLM response (tool call request) to console using `app_logger`.
    - [X] **TESTED**: End-to-end integration working with 2-3 second response times
- [X] **Testing Infrastructure**:
    - [X] Create comprehensive test scripts (`src/test_transcription_llm.py`, `src/test_audio_capture.py`)
    - [X] Test real speech capture and processing
    - [X] Validate all tool recognition scenarios
    - [X] Document results in `docs/TESTING_RESULTS.md`

**Phase 2 Results**: All core intelligence components working excellently. System ready for tool execution implementation.

### Phase 3: Tool Creation & Execution 🚧 CURRENT PHASE
**Objective**: Integrate the existing music tool and create the system control tool, enabling the LLM to execute them.

**Tasks**:
- [ ] **Tool Registry & Execution (`src/tools/registry.py`)**:
    - [ ] Create `src/tools/__init__.py`.
    - [ ] Implement a function to parse LLM output (expected JSON for tool calls).
    - [ ] Implement a mechanism to call AutoHotkey scripts:
        - [ ] Use `subprocess` module to run `AutoHotkey.exe script.ahk command param1 param2`.
        - [ ] Capture stdout/stderr from AHK scripts for feedback/logging.
    - [ ] Register the `music_controller.ahk` tool:
        - [ ] Map LLM tool names (e.g., "playMusic", "setVolume") to `music_controller.ahk` commands based on `tools/music_controller.md`.
- [ ] **System Control Tool (`src/tools/system_control.ahk`)**:
    - [ ] Create `system_control.ahk` with functions for:
        - [ ] Putting the system to sleep (`Sleep` command or `DllCall("PowrProf.dll", "SetSuspendState", "int", 0, "int", 0, "int", 0)`).
        - [ ] *Self-correction: Volume control is already in `music_controller.ahk` which handles system volume, so no need to duplicate here unless for different types of volume control.*
    - [ ] Ensure it accepts command-line arguments similar to `music_controller.ahk`.
    - [ ] Register this tool in `src/tools/registry.py` and update `src/llm/prompts.py`.
- [ ] **Main Orchestration (Full) (`src/main.py`)**:
    - [ ] Integrate tool execution: LLM Response -> Tool Parser -> AHK Caller.
    - [ ] Provide feedback to the user (e.g., "Playing music", "Going to sleep") using `app_logger` or TTS in future.

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
    - [ ] Test the `setup.ps1` and `validate_setup.ps1` scripts thoroughly from a clean user perspective.
    - [ ] Ensure microphone selection is clear and works.
    - [ ] Document basic usage and setup in `README.md`.
- [ ] **Code Review & Cleanup**:
    - [ ] Review code for clarity, simplicity, and adherence to the plan.
    - [ ] Remove any unused code or placeholders not relevant to MVP (e.g. dummy AHK files if user has placed actual ones).

## Future Scope (Post-MVP)
- Text-to-speech (TTS) feedback (e.g., Piper).
- Home Assistant integration for device control.
- More sophisticated conversation management.
- Expanded toolset.
- GUI for configuration/status.

This revised plan focuses on delivering a functional MVP by simplifying dependencies and leveraging existing components. 