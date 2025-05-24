#!/usr/bin/env python3
"""
A simple test script to record audio from the microphone and save it to a file.
"""

import os
import sys
import time
from src.config.settings import load_settings
from src.audio.capture import AudioCapturer
from src.utils.logger import app_logger, configure_logging

def main():
    # Load settings
    try:
        config_path = "config.json"
        settings = load_settings(config_path=config_path)
        configure_logging(settings.logging.level)
        app_logger.info("Settings loaded successfully.")
    except Exception as e:
        print(f"Error loading settings: {e}")
        sys.exit(1)
    
    # Initialize audio capturer
    try:
        capturer = AudioCapturer(settings)
        app_logger.info("Audio capturer initialized successfully.")
    except Exception as e:
        app_logger.error(f"Failed to initialize audio capturer: {e}")
        sys.exit(1)
    
    # List available microphones
    mics = capturer.list_available_microphones()
    app_logger.info(f"Found {len(mics)} microphones.")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Record audio
    app_logger.info("Recording test audio (5 seconds)...")
    audio_file = capturer.capture_test(duration=5.0, output_filename_base="test_recording")
    
    if audio_file:
        app_logger.info(f"Audio saved to: {audio_file}")
        
        # Try to play the audio file if on Windows
        if sys.platform == 'win32':
            try:
                import winsound
                app_logger.info("Playing recorded audio...")
                winsound.PlaySound(audio_file, winsound.SND_FILENAME)
            except Exception as e:
                app_logger.error(f"Failed to play audio: {e}")
    else:
        app_logger.error("Failed to record audio.")

if __name__ == "__main__":
    main() 