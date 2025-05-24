# Home Assistant Voice Control System

This document provides detailed instructions for setting up, configuring, and testing the Home Assistant voice control system.

## Overview

The Home Assistant voice control system is designed to run on a local machine and provide voice-controlled functionality for:
- Music playback and volume control
- System operations like sending the machine to sleep
- Other configurable actions

### Technology Stack

- **Wake Word Detection**: OpenWakeWord with "hey jarvis" and "alexa" wake words
- **Speech-to-Text**: Whisper-large-v3 on Groq Cloud
- **Natural Language Processing**: LLM via LiteLLM
- **Tools**: AutoHotkey v2 with UIAutomation v2 for system control

## Installation

### Prerequisites

- Python 3.8 or higher
- Working microphone
- Internet connection for cloud services (Groq, LiteLLM)
- AutoHotkey v2 (for tool execution)

### Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd HomeAssistant
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a configuration file by copying the template:

```bash
cp config.template.json config.json
```

4. Edit the `config.json` file to include your API keys and preferences (see Configuration section below)

## Configuration

The system uses a `config.json` file based on `config.template.json`. Key configuration options:

### API Keys
- **groq_api_key**: Your Groq API key for transcription and LLM services
- **litellm_settings**: Configuration for the LLM provider (currently using Groq's qwen-qwq-32b)

### Transcription Settings (NEW)
- **whisper_instructions**: Custom instructions to improve transcription accuracy for voice commands
- **language**: Optional language code for Whisper (e.g., 'en', 'es', 'fr')  
- **temperature**: Sampling temperature for Whisper (0.0 = deterministic)

### Audio Settings

Key audio configuration options in your `config.json`:

- **input_device_index**: Set to `null` for default microphone or specify index
- **input_device_name_keyword**: Set to a keyword to find a microphone by name (e.g., "W2G" or "USB"). This will override `input_device_index` if both are provided.
- **sample_rate**: Audio sample rate (default: 16000 Hz)
- **wake_word_sensitivity**: Threshold for wake word detection (0.0-1.0, default: 0.5)
- **silence_threshold_seconds**: How long to wait for silence before stopping voice recording (default: 4.0 seconds)
  - **Increase this value** (e.g., 6.0-8.0) if you need more time to speak longer commands
  - **Decrease this value** (e.g., 2.0-3.0) for quicker responses to short commands
  - Recommended range: 2.0-8.0 seconds

Example audio settings:
```json
"audio_settings": {
  "input_device_index": null,
  "input_device_name_keyword": "W2G",
  "sample_rate": 16000,
  "wake_word_sensitivity": 0.5,
  "silence_threshold_seconds": 4.0
}
```

### Paths Settings

Edit the `config.json` file to configure the following:

```json
{
  "paths": {
    "audio_output_dir": "./output/audio",
    "openwakeword_models_dir": "./models/wakeword" 
  },
  "audio_settings": {
    "input_device_index": null,
    "input_device_name_keyword": null,
    "sample_rate": 16000,
    "channels": 1,
    "wake_word_sensitivity": 0.5,
    "silence_threshold": 500,
    "silence_duration": 1.5
  },
  "api_keys": {
    "groq": "YOUR_GROQ_API_KEY",
    "litellm": "YOUR_LITELLM_API_KEY"
  },
  "model_settings": {
    "llm_model": "llama3-8b-8192"
  },
  "logging": {
    "level": "INFO"
  }
}
```

- `paths`: Directories for storing audio files and wake word models
- `audio_settings`: 
  - `input_device_index`: Set to `null` for default microphone or specify index
  - `input_device_name_keyword`: Set to a keyword to find a microphone by name (e.g., "USB" or "Headset"). This will override `input_device_index` if both are provided.
  - `sample_rate`: Audio sample rate (default: 16000 Hz)
  - `channels`: Number of audio channels (default: 1)
  - `wake_word_sensitivity`: Threshold for wake word detection (0.0-1.0)
  - `silence_threshold`: Threshold for detecting silence after speech
  - `silence_duration`: Duration of silence to end recording (in seconds)
- `api_keys`: Your API keys for cloud services
- `model_settings`: LLM model configuration
- `logging`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Usage

Run the application:

```bash
python -m src.main
```

Or specify a different config file:

```bash
python -m src.main path/to/config.json
```

The system will:
1. Listen for the wake words "hey jarvis" or "alexa"
2. Capture your speech after the wake word
3. Transcribe the speech
4. Process the transcription with an LLM
5. Execute the appropriate tool based on your request

## Testing

### Testing the Full System

To test the entire system:

```bash
python -m src.main
```

Say "hey jarvis" or "alexa" followed by a command like "play music" or "set volume to 50%".

### Component Testing

#### Wake Word Detection

Test the wake word detector:

```bash
python -c "from src.config.settings import load_settings; from src.audio.wake_word import WakeWordDetector; settings = load_settings(); detector = WakeWordDetector(settings); detector.listen()"
```

Or run the built-in test:

```bash
python -m src.audio.wake_word
```

The detector will listen for "hey jarvis" or "alexa" and log when it detects the wake word.

#### Audio Capture

Test audio capture:

```bash
python -c "from src.config.settings import load_settings; from src.audio.capture import AudioCapturer; settings = load_settings(); capturer = AudioCapturer(settings); capturer.list_available_microphones(); audio_file = capturer.capture_test(); print(f'Audio saved to {audio_file}')"
```

#### Transcription

Test the transcription service with an existing audio file:

```bash
python -c "from src.config.settings import load_settings; from src.transcription.groq_client import GroqTranscriber; settings = load_settings(); transcriber = GroqTranscriber(settings); transcript = transcriber.transcribe_audio('path/to/audio.wav'); print(f'Transcript: {transcript}')"
```

### Selecting a Microphone

You have two ways to select a microphone:

1. **By Index**: Use `input_device_index` in config.json (e.g., `"input_device_index": 1`)

2. **By Name Keyword**: Use `input_device_name_keyword` to match a part of the microphone name (e.g., `"input_device_name_keyword": "USB"` will match any microphone with "USB" in its name)

#### Listing Available Microphones

To find available microphones, run our dedicated microphone listing tool:

```bash
python -m src.list_mics
```

This will display all available microphones with their indices and details. You can also use this tool to automatically update your config.json with a selected microphone:

```bash
python -m src.list_mics --update-config 1  # Replace 1 with your desired microphone index
```

Alternatively, you can list microphones programmatically:

```bash
python -c "from src.config.settings import load_settings; from src.audio.capture import AudioCapturer; settings = load_settings(); capturer = AudioCapturer(settings); capturer.list_available_microphones()"
```

### Debugging

If you encounter issues:

1. **Check Logs**: Logs are printed to the console and may provide error details

2. **Wake Word Detection Issues**:
   - Ensure the "hey jarvis" and "alexa" models are available
   - Try adjusting the `wake_word_sensitivity` in config.json
   - Speak clearly and in a quiet environment

3. **Audio Capture Issues**:
   - Verify your microphone is working
   - Try specifying a different `input_device_index` or `input_device_name_keyword` in config.json
   - Run `python -m src.list_mics` to see available devices

4. **Transcription Issues**:
   - Verify your Groq API key is correct
   - Check your internet connection
   - Ensure the audio file was captured correctly

5. **LLM Processing Issues**:
   - Verify your LiteLLM API key is correct
   - Check if the selected model is available

## Future Scope

Future enhancements may include:
- Integration with Home Assistant for smart home control
- Text-to-speech capabilities using Piper
- Additional tool integrations

## License

[Specify license information here] 