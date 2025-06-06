"""
Audio Effects Utility Module

This module handles playing sound effects for the voice assistant system.
"""

import os
import threading
from pathlib import Path
from typing import Optional

from audioplayer import AudioPlayer
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
            if not os.path.exists(sound_file_path):
                app_logger.warning(f"Sound effect file not found: {sound_file_path}")
                return
                
            player = None
            try:
                player = AudioPlayer(sound_file_path)
                # Convert volume from 0.0-1.0 to 0-100 for AudioPlayer
                player_volume = int(max(0, min(100, volume * 100)))
                player.volume = player_volume
                app_logger.debug(f"Playing sound effect: {sound_file_path} at volume {player.volume} ({volume*100:.0f}%)")
                player.play(block=True) # Block this thread until sound is done
                app_logger.debug(f"Sound effect finished: {sound_file_path}")
            finally:
                if player:
                    player.close()
                
        except ImportError:
            app_logger.warning("audioplayer not available - sound effects disabled. Please install it.")
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