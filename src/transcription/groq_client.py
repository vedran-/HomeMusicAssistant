from groq import Groq
import os
from typing import Optional

from src.config.settings import AppSettings
from src.utils.logger import app_logger

class GroqTranscriber:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        if not self.settings.groq_api_key:
            app_logger.error("Groq API key is not configured. Transcription will fail.")
            raise ValueError("Groq API key is missing. Please set GROQ_API_KEY or add to config.json.")
        
        self.client = Groq(
            api_key=self.settings.groq_api_key
        )
        self.model = "whisper-large-v3" # As per TODO.md

    def transcribe_audio(self, audio_file_path: str) -> Optional[str]:
        if not os.path.exists(audio_file_path):
            app_logger.error(f"Audio file not found: {audio_file_path}")
            return None

        app_logger.info(f"Transcribing {audio_file_path} using Groq ({self.model})...")

        try:
            with open(audio_file_path, "rb") as audio_file:
                # The Groq SDK expects the file content to be read and passed.
                # The 'file' parameter should be a tuple: (filename, file_content_bytes)
                file_content = audio_file.read()
                
                transcription_response = self.client.audio.transcriptions.create(
                    file=(os.path.basename(audio_file_path), file_content),
                    model=self.model
                    # language="en", # Optional
                    # response_format="json", # Default is json with a "text" field
                )
            
            app_logger.info("Transcription successful.")
            return transcription_response.text

        except Exception as e:
            app_logger.error(f"Groq API transcription failed: {e}", exc_info=True)
            return None

if __name__ == '__main__':
    # This is for basic testing of the GroqTranscriber
    # It requires a config.json with a valid GROQ_API_KEY and a dummy audio file.
    from src.config.settings import load_settings
    import tempfile
    import wave

    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(current_dir, "..", "..", "config.json")

    if not os.path.exists(config_file_path):
        print(f"ERROR: config.json not found at {config_file_path}")
        config_file_path = "config.json"
        if not os.path.exists(config_file_path):
             print(f"ERROR: config.json also not found at {os.path.abspath(config_file_path)}. Aborting test.")
             exit(1)
        else:
            print(f"Found config.json at {os.path.abspath(config_file_path)}")

    # Create a dummy WAV file for testing
    dummy_wav_path = None
    try:
        settings = load_settings(config_path=config_file_path)
        app_logger.info("Settings loaded for GroqTranscriber test.")

        if not settings.groq_api_key:
            app_logger.error("GROQ_API_KEY not set. Skipping transcription test.")
        else:
            transcriber = GroqTranscriber(settings)
            
            # Create a very short, silent WAV file for the test to avoid actual speech processing costs/time
            # and to ensure the API call structure is correct.
            # A real test would use a known audio sample.
            fd, dummy_wav_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd) # close file descriptor from mkstemp
            
            app_logger.info(f"Creating dummy WAV: {dummy_wav_path}")
            with wave.open(dummy_wav_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2) # 2 bytes = 16-bit
                wf.setframerate(16000)
                # A very short audio clip (e.g., 0.1 seconds of silence)
                # 16000 frames/sec * 0.1 sec = 1600 frames
                # Each frame is 2 bytes (16-bit mono)
                num_frames = 1600
                silent_frame = b'\x00\x00' # 2 bytes of silence
                frames_data = silent_frame * num_frames
                wf.writeframes(frames_data)
            app_logger.info(f"Dummy WAV created.")

            app_logger.info("Attempting to transcribe dummy audio file...")
            # Note: Transcribing pure silence might result in an empty string or specific model behavior.
            # This test primarily checks API connectivity and request format.
            transcription = transcriber.transcribe_audio(dummy_wav_path)

            if transcription is not None:
                # Groq Whisper with silence often returns an empty string or a string with just a space/newline.
                # This is expected for silent audio.
                app_logger.info(f"Test Transcription: '{transcription}'")
                if transcription.strip() == "":
                    app_logger.info("Empty transcription for silent audio: OK.")
                else:
                    app_logger.warning(f"Non-empty transcription for silent audio: '{transcription}'.")
            else:
                app_logger.error("Test transcription failed.")

    except ValueError as e: # Catch API key error from constructor
        app_logger.error(f"Init error: {e}")
    except FileNotFoundError as e:
        app_logger.error(f"Config file error: {e}")
    except Exception as e:
        app_logger.error(f"GroqTranscriber test error: {e}", exc_info=True)
    finally:
        if dummy_wav_path and os.path.exists(dummy_wav_path):
            try:
                os.remove(dummy_wav_path)
                app_logger.info(f"Cleaned dummy WAV: {dummy_wav_path}")
            except Exception as e:
                app_logger.error(f"Error cleaning dummy WAV {dummy_wav_path}: {e}")
        app_logger.info("GroqTranscriber test finished.") 