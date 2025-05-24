#!/usr/bin/env python3
"""
A test script to verify wake word detection.
This helps diagnose wake word recognition issues.
"""

import os
import sys
import time
from src.config.settings import load_settings
from src.audio.wake_word import WakeWordDetector
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
    
    # Initialize wake word detector
    try:
        detector = WakeWordDetector(settings)
        app_logger.info("Wake word detector initialized successfully.")
    except Exception as e:
        app_logger.error(f"Failed to initialize wake word detector: {e}")
        sys.exit(1)
    
    app_logger.info(f"Wake word model: {detector.active_model}")
    app_logger.info(f"Wake word sensitivity: {detector.sensitivity}")
    app_logger.info(f"Sample rate: {detector.sample_rate}")
    
    try:
        app_logger.info("Starting wake word detection test...")
        app_logger.info(f"Say '{detector.active_model}' to trigger detection.")
        app_logger.info("Press Ctrl+C to stop the test.")
        
        # Test the detector for up to 10 wake word detections or until interrupted
        for i in range(10):
            if detector.listen():
                app_logger.info(f"Wake word detected! (#{i+1})")
                # Add a delay to make the test more interactive
                time.sleep(2)
            else:
                app_logger.warning("Wake word detection failed or was interrupted.")
                break
    
    except KeyboardInterrupt:
        app_logger.info("Test interrupted by user.")
    except Exception as e:
        app_logger.error(f"Error during wake word test: {e}")
    finally:
        app_logger.info("Wake word detection test finished.")

if __name__ == "__main__":
    main() 