from pydantic import BaseModel, DirectoryPath, FilePath, validator, Field
from typing import Optional, Dict
import json
import os
from dotenv import load_dotenv

load_dotenv() # Load .env file

class YouTubeMusicAPISettings(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=9863) # Default port from template

class LiteLLMSettings(BaseModel):
    provider: str = Field(default="openai")
    model: str = Field(default="gpt-3.5-turbo")
    api_key: Optional[str] = Field(default=None)
    debug_mode: bool = Field(default=False, description="Enable LiteLLM debug mode for detailed error logging")

class TranscriptionSettings(BaseModel):
    whisper_instructions: Optional[str] = Field(default=None, description="Instructions to provide to Whisper for better transcription accuracy")
    language: Optional[str] = Field(default=None, description="Language code for Whisper (e.g., 'en', 'es', 'fr')")
    temperature: float = Field(default=0.0, description="Sampling temperature for Whisper (0.0 = deterministic)")

class AudioSettings(BaseModel):
    input_device_index: Optional[int] = Field(default=None)
    input_device_name_keyword: Optional[str] = Field(default=None, description="Keyword to match in the device name. If provided, will override input_device_index.")
    sample_rate: int = Field(default=16000)
    wake_word_sensitivity: float = Field(default=0.5)
    silence_threshold_seconds: float = Field(default=4.0, description="How long to wait for silence before stopping voice recording (in seconds). Increase for longer speech, decrease for quicker responses.")
    initial_silence_allowance_seconds: float = Field(default=5.0, description="How long to allow initial silence at the start of recording before the user speaks (in seconds). This gives users time to think before speaking.")

class PathsSettings(BaseModel):
    autohotkey_exe: FilePath
    openwakeword_models_dir: DirectoryPath
    autohotkey_scripts_dir: DirectoryPath

    @validator('autohotkey_exe', 'openwakeword_models_dir', 'autohotkey_scripts_dir', pre=True, always=True)
    def resolve_path(cls, v):
        return os.path.abspath(v)

class LoggingSettings(BaseModel):
    level: str = Field(default="INFO")
    format: str = Field(default="{time} | {level} | {message}")

class TTSSettings(BaseModel):
    enabled: bool = Field(default=True, description="Enable text-to-speech functionality")
    voice_model: str = Field(default="en_US-amy-medium", description="Piper voice model to use")
    use_cuda: bool = Field(default=True, description="Use CUDA for GPU acceleration")
    models_dir: DirectoryPath = Field(default="./models/piper", description="Directory to store Piper voice models")
    sample_rate: int = Field(default=22050, description="Audio sample rate for TTS output")
    speak_responses: bool = Field(default=True, description="Speak LLM responses and tool feedback")
    max_speech_length: int = Field(default=10000, description="Maximum character length for TTS speech (will truncate longer text)")

    @validator('models_dir', pre=True, always=True)
    def resolve_models_dir(cls, v):
        return os.path.abspath(v)

class AppSettings(BaseModel):
    groq_api_key: str
    litellm_settings: LiteLLMSettings = Field(default_factory=LiteLLMSettings)
    transcription_settings: TranscriptionSettings = Field(default_factory=TranscriptionSettings)
    audio_settings: AudioSettings = Field(default_factory=AudioSettings)
    paths: PathsSettings
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    youtube_music_api: YouTubeMusicAPISettings = Field(default_factory=YouTubeMusicAPISettings)
    tts_settings: TTSSettings = Field(default_factory=TTSSettings)

def load_settings(config_path: str = "config.json") -> AppSettings:
    # Try to load GROQ_API_KEY from environment first
    groq_env_key = os.getenv("GROQ_API_KEY")
    litellm_env_key = os.getenv("LITELLM_API_KEY")

    config_file_path = os.path.abspath(config_path)

    if not os.path.exists(config_file_path):
        raise FileNotFoundError(f"Configuration file not found: {config_file_path}. Please copy config.template.json to {config_path} and fill it out.")

    with open(config_file_path, 'r') as f:
        config_data = json.load(f)

    # Override API keys from environment if present
    if groq_env_key:
        config_data['groq_api_key'] = groq_env_key
    elif not config_data.get('groq_api_key'):
        raise ValueError("groq_api_key not found in config file or environment variables.")

    if 'litellm_settings' not in config_data:
        config_data['litellm_settings'] = {}
    
    if litellm_env_key:
        config_data['litellm_settings']['api_key'] = litellm_env_key
    # If api_key is not in JSON and not in ENV, it will remain None (as per Pydantic model default)
    # If it is required by a specific provider, LiteLLM will handle that error.

    # Ensure paths are created if they are relative and don't exist
    # This is now handled by Pydantic DirectoryPath for openwakeword_models_dir and autohotkey_scripts_dir if they are part of the model directly
    # However, we might want to create them if they don't exist after path resolution.
    
    # Create directories if they don't exist (Pydantic validates existence for FilePath, DirectoryPath but doesn't create)
    paths_settings_data = config_data.get('paths', {})
    for key, value in paths_settings_data.items():
        abs_path = os.path.abspath(value)
        if key.endswith('_dir') and not os.path.exists(abs_path):
            os.makedirs(abs_path, exist_ok=True)
            print(f"Created directory: {abs_path}")
        config_data['paths'][key] = abs_path # Ensure paths in config_data are absolute before Pydantic validation

    # Create TTS models directory if it doesn't exist
    tts_settings_data = config_data.get('tts_settings', {})
    if 'models_dir' in tts_settings_data:
        tts_models_dir = os.path.abspath(tts_settings_data['models_dir'])
        if not os.path.exists(tts_models_dir):
            os.makedirs(tts_models_dir, exist_ok=True)
            print(f"Created TTS models directory: {tts_models_dir}")
        config_data['tts_settings']['models_dir'] = tts_models_dir

    return AppSettings(**config_data)

# Example usage (for testing, will be used in main.py)
if __name__ == "__main__":
    print(f"Looking for config.json in: {os.path.abspath('config.json')}")
    # Create a dummy config.json for testing if it doesn't exist in the current execution directory
    # This is primarily for a developer running settings.py directly.
    # The main application should rely on a config.json being present.
    if not os.path.exists("config.json"):
        print("config.json not found. Creating a dummy one for testing settings.py.")
        print(f"Please ensure your actual config.json is in: {os.getcwd()} or specify its path.")
        dummy_template_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.template.json")
        dummy_target_path = "config.json"
        
        if os.path.exists(dummy_template_path):
            with open(dummy_template_path, 'r') as f_template:
                dummy_config_content = json.load(f_template)
            # Customize dummy for local testing if needed, e.g. ensure AHK path is valid for the current system
            # For GITHUB_ACTIONS or CI, might need to mock the AHK path
            if not os.path.exists(dummy_config_content["paths"]["autohotkey_exe"]):
                print(f"Warning: Default AHK path {dummy_config_content['paths']['autohotkey_exe']} in template does not exist.")
                # Provide a placeholder that won't crash Pydantic's FilePath if file doesn't exist for test run
                # For actual use, this path must be valid.
                # One option for testing is to create a dummy file if not os.name == 'nt'
                # However, Pydantic's FilePath will check for existence. So this path needs to be valid or mocked for tests.
                # For now, we assume user sets it correctly in their actual config.json.

            with open(dummy_target_path, "w") as f_dummy:
                json.dump(dummy_config_content, f_dummy, indent=2)
            print(f"Created dummy {dummy_target_path} from template for testing settings.py. Please review and update it, especially API keys.")
        else:
            print(f"Could not find config.template.json at {dummy_template_path} to create a dummy config.json")

    try:
        settings = load_settings()
        print("\nSettings loaded successfully!")
        print(f"Groq Key: {'*' * len(settings.groq_api_key) if settings.groq_api_key else 'Not set'}")
        print(f"LiteLLM Provider: {settings.litellm_settings.provider}")
        print(f"LiteLLM Model: {settings.litellm_settings.model}")
        print(f"LiteLLM API Key: {'*' * len(settings.litellm_settings.api_key) if settings.litellm_settings.api_key else 'Not set'}")
        print(f"YouTube Music API Host: {settings.youtube_music_api.host}")
        print(f"YouTube Music API Port: {settings.youtube_music_api.port}")
        print(f"AHK Path: {settings.paths.autohotkey_exe}")
        print(f"OpenWakeWord Models Path: {settings.paths.openwakeword_models_dir}")
        print(f"AutoHotkey Scripts Path: {settings.paths.autohotkey_scripts_dir}")
        print(f"Log Level: {settings.logging.level}")

        # Test that paths were created if they didn't exist
        if not os.path.exists(settings.paths.openwakeword_models_dir):
            print(f"ERROR: openwakeword_models_dir was not created: {settings.paths.openwakeword_models_dir}")
        if not os.path.exists(settings.paths.autohotkey_scripts_dir):
            print(f"ERROR: autohotkey_scripts_dir was not created: {settings.paths.autohotkey_scripts_dir}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}") 