"""
Audio Effects Utility Module

This module handles playing sound effects for the voice assistant system.
"""

import os
import threading
from pathlib import Path
from typing import Optional

from src.utils.logger import app_logger

def play_sound_effect_async(sound_file_path: str, volume: float = 0.7) -> None:
    """
    Play a sound effect asynchronously without blocking the main thread.
    
    Args:
        sound_file_path: Path to the sound file to play
        volume: Volume level (0.0 to 1.0)
    """
    def _play_sound():
        try:
            import pygame
            
            # Initialize pygame mixer if not already initialized
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                
            # Load and play the sound
            if os.path.exists(sound_file_path):
                sound = pygame.mixer.Sound(sound_file_path)
                sound.set_volume(volume)
                sound.play()
                
                # Wait for the sound to finish playing
                while pygame.mixer.get_busy():
                    pygame.time.wait(100)
                    
                app_logger.debug(f"Sound effect played: {sound_file_path}")
            else:
                app_logger.warning(f"Sound effect file not found: {sound_file_path}")
                
        except ImportError:
            app_logger.warning("pygame not available - sound effects disabled")
        except Exception as e:
            app_logger.error(f"Error playing sound effect: {e}")
    
    # Play sound in a separate thread to avoid blocking
    sound_thread = threading.Thread(target=_play_sound, daemon=True)
    sound_thread.start()

def play_wake_word_accepted_sound(audio_dir: Optional[str] = None) -> None:
    """
    Play the wake word accepted sound effect.
    
    Args:
        audio_dir: Directory containing the audio files. If None, uses default path.
    """
    if audio_dir is None:
        # Default path relative to the project structure
        current_dir = Path(__file__).parent.parent
        audio_dir = current_dir / "audio"
    else:
        audio_dir = Path(audio_dir)
    
    sound_file = audio_dir / "WakeWordAccepted.mp3"
    
    app_logger.debug("Playing wake word accepted sound effect")
    play_sound_effect_async(str(sound_file), volume=0.5) 