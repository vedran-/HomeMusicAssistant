# Home Assistant Voice Control System

This document provides detailed instructions for setting up, configuring, and testing the Home Assistant voice control system.

## Overview

The Home Assistant voice control system is designed to run on a local machine and provide voice-controlled functionality for:
- Music playback and volume control
- System operations like sending the machine to sleep
- Voice responses and feedback using text-to-speech
- Other configurable actions

### Technology Stack

- **Wake Word Detection**: OpenWakeWord with "hey jarvis" and "alexa" wake words
- **Speech-to-Text**: Whisper-large-v3 on Groq Cloud
- **Natural Language Processing**: LLM via LiteLLM
- **Text-to-Speech**: Piper TTS for voice responses
- **Tools**: AutoHotkey v2 with UIAutomation v2 for system control

## Installation

### Prerequisites

- Python 3.8 or higher
- Working microphone and speakers/headphones
- Internet connection for cloud services (Groq, LiteLLM)
- AutoHotkey v2 (for tool execution)
- Piper TTS executable (for voice responses)
- **Ollama** (for local memory/embeddings) - Download from [ollama.com](https://ollama.com/download)

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

3. Install Piper TTS executable:

Download the Piper TTS executable from the [official releases page](https://github.com/rhasspy/piper/releases/tag/2023.11.14-2):

- Download the appropriate release for your platform (Windows, Linux, or macOS)
- Extract the contents to `tools/piper/` directory in your project
- Ensure the executable is named `piper.exe` (Windows) or `piper` (Linux/macOS)
- The directory structure should look like:
  ```
  tools/
  └── piper/
      ├── piper.exe (or piper on Linux/macOS)
      ├── espeak-ng.dll
      ├── onnxruntime.dll
      └── other supporting files...
  ```

4. Download voice models:

Download the voice model files for text-to-speech:
- Download `en_US-amy-medium.onnx` from: https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx
- Download `en_US-amy-medium.onnx.json` from: https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx.json
- Place both files in `models/piper/` directory

5. Create a configuration file by copying the template:

```bash
cp config.template.json config.json
```

6. Edit the `config.json` file to include your API keys and preferences (see Configuration section below)

## Configuration

The system uses a `config.json` file based on `config.template.json`. Key configuration options:

### API Keys
- **groq_api_key**: Your Groq API key for transcription and LLM services
- **litellm_settings**: Configuration for the LLM provider (currently using Groq's qwen-qwq-32b)

### Transcription Settings (NEW)
- **whisper_instructions**: Custom instructions to improve transcription accuracy for voice commands
- **language**: Optional language code for Whisper (e.g., 'en', 'es', 'fr')  
- **temperature**: Sampling temperature for Whisper (0.0 = deterministic)

### TTS (Text-to-Speech) Settings
- **enabled**: Enable/disable voice responses (default: true)
- **voice_model**: Voice model to use (default: "en_US-amy-medium")
- **models_dir**: Directory containing voice model files (default: "models/piper")
- **sample_rate**: Audio sample rate for TTS (default: 22050)
- **use_cuda**: Enable CUDA acceleration if available (default: true)
- **speak_responses**: Whether to speak LLM responses and tool feedback (default: true)

### Memory Configuration (NEW)

The system now features intelligent long-term memory powered by **Ollama** for fully local semantic search. Memory enables the assistant to:
- Remember your preferences and past conversations
- Provide personalized responses based on history
- Learn from interactions over time

**Prerequisites:**
- **Ollama**: Download and install from [ollama.com](https://ollama.com/download)
  - The system will automatically start/stop Ollama as needed
  - No manual management required!

**Configuration:**
```json
"memory_config": {
  "data_path": "./.memory",
  "llm_provider": "litellm",
  "llm_model": "groq/moonshotai/kimi-k2-instruct",
  "llm_api_key": "YOUR_GROQ_API_KEY",
  "embedder_provider": "ollama",
  "embedder_model": "nomic-embed-text",
  "embedder_api_key": null,
  "vector_store_provider": "qdrant",
  "vector_store_embedding_model_dims": 768
}
```

**Key Features:**
- ✅ **Fully Local**: All embeddings generated locally via Ollama (no cloud APIs)
- ✅ **Auto-Managed**: Ollama starts on-demand and stops after 3 minutes of inactivity
- ✅ **Zero Setup**: Embedding model (~274MB) downloads automatically on first use
- ✅ **Semantic Search**: Understands meaning, not just keywords
- ✅ **Efficient**: Minimal resource usage with smart lifecycle management

**First Run:**
- On first memory operation, the system will download the `nomic-embed-text` model (~274MB)
- This is a one-time download that takes 1-2 minutes
- Subsequent operations are fast (<100ms per embedding)

**Optional - Pre-download Model:**
```bash
ollama pull nomic-embed-text
```

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
  "tts_settings": {
    "enabled": true,
    "voice_model": "en_US-amy-medium",
    "models_dir": "models/piper",
    "sample_rate": 22050,
    "use_cuda": true,
    "speak_responses": true
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
6. Provide voice feedback and responses using text-to-speech

## Available Tools

The system includes several built-in tools for system control:

### Music Controller
The Music Controller provides comprehensive YouTube Music control via voice commands, utilizing the [unofficial YouTube Music desktop app](https://github.com/th-ch/youtube-music). It supports playback control, music search, time navigation, and volume management.

**Important:** To use this feature, you must have the YouTube Music (unofficial) desktop application installed and running. Additionally, you need to enable the **`API Server [Beta]`** plugin within the desktop app's settings (usually found under `Plugins` or `Settings -> Plugins`). This allows HomeMusicAssistant to communicate with and control the YouTube Music app.

**Documentation**: See [MUSIC_CONTROLLER.md](MUSIC_CONTROLLER.md) for complete command reference and usage examples.

**Voice Commands Examples**:
- *"Play some jazz music"* - Searches and plays jazz on YouTube Music
- *"Next song"* - Skips to the next track
- *"Go back 30 seconds"* - Rewinds the current song
- *"Turn up the volume"* - Increases system volume
- *"Like this song"* - Likes the currently playing track

### Volume Control
System volume management with relative adjustments and mute functionality.

### System Control
Basic system operations like sleep mode (use with caution in testing).

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

#### Text-to-Speech (TTS)

Test the TTS system:

```bash
python src/test_tts.py
```

Or test TTS programmatically:

```bash
python -c "from src.config.settings import load_settings; from src.tts.piper_client import PiperTTSClient; settings = load_settings(); tts = PiperTTSClient(settings); tts.speak('Hello! This is a test of the text to speech system.')"
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

6. **TTS (Text-to-Speech) Issues**:
   - Ensure Piper executable is installed in `tools/piper/` directory
   - Verify voice model files are downloaded to `models/piper/` directory
   - Check that speakers/headphones are working and volume is up
   - Try running `python src/test_tts.py` to test TTS functionality
   - If TTS fails, check the logs for specific error messages

## Future Scope

Future enhancements may include:
- Integration with Home Assistant for smart home control
- Additional voice models and languages for TTS
- Voice customization and speech rate controls
- Additional tool integrations
- Offline LLM support for complete local operation

## License

[Specify license information here] 