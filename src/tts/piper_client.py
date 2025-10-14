import os
import wave
import threading
import uuid # For unique speech IDs
import time
import subprocess
import tempfile
from typing import Optional
from audioplayer import AudioPlayer

from src.config.settings import AppSettings
from src.utils.logger import app_logger


class PiperTTSClient:
    """
    Piper TTS client for converting text to speech using the Piper CLI executable.
    Uses the piper.exe from tools/piper directory for text-to-speech conversion.
    """
    
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.tts_settings = settings.tts_settings
        self.voice = None
        self.is_speaking = False
        self._speaking_lock = threading.Lock() # Lock for is_speaking state
        self.current_player = None
        self._player_lock = threading.Lock() # Lock for current_player access and modification
        self._current_speech_id = None # To track the ID of the speech being played by current_player
        
        if self.tts_settings.enabled:
            self._initialize_voice()
    
    def _initialize_voice(self):
        """Initialize the Piper voice model."""
        try:
            # Use the piper.exe from tools/piper directory
            self.piper_exe_path = os.path.abspath(os.path.join("tools", "piper", "piper.exe"))
            
            if not os.path.exists(self.piper_exe_path):
                raise Exception(f"Piper executable not found at: {self.piper_exe_path}")
            
            # Test if piper.exe works
            result = subprocess.run([self.piper_exe_path, '--help'], capture_output=True, text=True)
            if result.returncode == 0:
                app_logger.info(f"✅ Piper executable found at: {self.piper_exe_path}")
                self.voice = "command_line"  # Use string to indicate CLI mode
                
                # Ensure model is downloaded
                model_path = self._get_model_path()
                if not os.path.exists(model_path):
                    app_logger.warning(f"Voice model not found: {model_path}")
                    app_logger.info("Please download the voice model manually:")
                    app_logger.info(f"1. Download: https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx")
                    app_logger.info(f"2. Download: https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx.json")
                    app_logger.info(f"3. Place both files in: {self.tts_settings.models_dir}")
                
                app_logger.info("✅ Piper TTS initialized successfully (CLI mode)")
            else:
                raise Exception(f"Piper executable test failed: {result.stderr}")
            
        except Exception as e:
            app_logger.error(f"Failed to initialize Piper TTS: {e}", exc_info=True)
            self.voice = None
    
    def _get_model_path(self) -> str:
        """Get the full path to the voice model file."""
        model_filename = f"{self.tts_settings.voice_model}.onnx"
        return os.path.abspath(os.path.join(self.tts_settings.models_dir, model_filename))
    
    def speak(self, text: str, interrupt_current: bool = True, volume: float = 1.0, speech_id: Optional[str] = None) -> bool:
        speech_id = speech_id or str(uuid.uuid4())
        app_logger.debug(f"[TTS Speak ID: {speech_id}] Speak request received. Text: '{text[:30]}...', Interrupt: {interrupt_current}, Volume: {volume}")
        """
        Convert text to speech and play it.
        
        Args:
            text: Text to convert to speech
            interrupt_current: Whether to interrupt currently playing speech
            
        Returns:
            True if speech was successful, False otherwise
        """
        if not self.tts_settings.enabled or not self.voice:
            app_logger.debug("TTS is disabled or not initialized")
            return False
        
        if not text or not text.strip():
            app_logger.debug("Empty text provided to TTS")
            return False
        
        # Handle interruption
        if interrupt_current:
            if self.is_speaking: # Quick check
                with self._speaking_lock: # Lock for consistent check and call
                    if self.is_speaking: # Double check
                        app_logger.debug("Interrupting current speech...")
                        self.stop_speaking() # Signal stop
                # Wait for the interrupted speak to clean up and clear is_speaking
                # app_logger.debug("Waiting for interrupted speech to clear is_speaking flag...")
                while True:
                    with self._speaking_lock:
                        if not self.is_speaking:
                            # app_logger.debug("is_speaking is now False after interruption.")
                            break
                    time.sleep(0.05)
        
        # Wait for current speech to finish if not interrupting
        # Wait for current speech to finish if not interrupting (and still speaking)
        if not interrupt_current:
            # app_logger.debug("Not interrupting, checking if already speaking...")
            while True:
                with self._speaking_lock:
                    if not self.is_speaking:
                        # app_logger.debug("Not speaking, can proceed.")
                        break
                # app_logger.debug("Still speaking, waiting...")
                time.sleep(0.05)
        
        try:
            with self._speaking_lock:
                self.is_speaking = True
            
            app_logger.info(f"🗣️ Speaking: '{text}'")
            audio_file_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            self._speak_text(text, audio_file_path, volume, speech_id, interrupt_current)
            return True
            
        except Exception as e:
            app_logger.error(f"Error during TTS playback: {e}", exc_info=True)
            return False
        finally:
            with self._speaking_lock:
                self.is_speaking = False
    
    def _get_wav_duration(self, wav_file_path: str) -> float:
        """Get the duration of a WAV file by parsing its header."""
        try:
            with wave.open(wav_file_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                duration = frames / float(sample_rate)
                return duration
        except Exception as e:
            app_logger.warning(f"Failed to parse WAV duration: {e}")
            return 2.0  # fallback duration

    def _speak_text(self, text: str, audio_file_path: str, volume: float = 1.0, speech_id: Optional[str] = None, interrupt_current: bool = True):
        """Internal method to handle the actual text-to-speech conversion and playback."""
        try:
            # Use Piper CLI to generate audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Run piper command
                model_path = self._get_model_path()
                cmd = [
                    self.piper_exe_path,
                    '--model', model_path,
                    '--output-file', temp_path
                ]
                
                result = subprocess.run(
                    cmd, 
                    input=text, 
                    encoding='utf-8',
                    errors='replace',
                    capture_output=True
                )
                
                if result.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    player = AudioPlayer(temp_path)
                    player.volume = int(volume * 100) # audioplayer uses 0-100 for volume

                    with self._player_lock:
                        # If another thread initiated a stop or a new speech after we released _speaking_lock but before we acquired _player_lock
                        if self.current_player and self._current_speech_id != speech_id and interrupt_current: # This check might be complex due to interrupt logic
                            app_logger.warning(f"[TTS Speak ID: {speech_id}] Another player (ID: {self._current_speech_id}) became active before this one could start. Aborting playback for this speech_id.")
                            # Clean up the newly created player for this call since it won't be used
                            player.close() # Release the audio file
                            return # Don't assign self.current_player or play
                        
                        app_logger.debug(f"[TTS Speak ID: {speech_id}] Setting current_player.")
                        self.current_player = player
                        self._current_speech_id = speech_id

                    app_logger.debug(f"[TTS Speak ID: {speech_id}] Generating TTS audio for: '{text[:30]}...' at volume {volume}")
                    
                    # Use non-blocking play for immediate interruption capability
                    player.play(block=False)
                    
                    # Get accurate duration by parsing WAV header
                    start_time = time.time()
                    actual_duration = self._get_wav_duration(temp_path)
                    app_logger.debug(f"[TTS Speak ID: {speech_id}] Audio duration: {actual_duration:.2f} seconds")
                    
                    # Wait for actual playback duration while checking for stop signals
                    while time.time() - start_time < actual_duration:
                        # Check if we should stop (current_player was changed or cleared)
                        with self._player_lock:
                            if self.current_player != player or self._current_speech_id != speech_id:
                                app_logger.debug(f"[TTS Speak ID: {speech_id}] Playback interrupted - stopping.")
                                try:
                                    player.stop()
                                except Exception as stop_err:
                                    app_logger.debug(f"[TTS Speak ID: {speech_id}] Error stopping player: {stop_err}")
                                break
                        
                        # Small sleep to avoid busy waiting
                        time.sleep(0.05)
                    
                    app_logger.debug(f"[TTS Speak ID: {speech_id}] TTS playback finished.")
                elif result.returncode != 0:
                    app_logger.error(f"Piper CLI failed: {result.stderr}")
                    raise Exception(f"Piper CLI error: {result.stderr}")
                elif not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                    app_logger.error(f"Piper CLI produced an empty or missing audio file: {temp_path}")
                    raise Exception(f"Piper CLI produced an empty or missing audio file.")
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except Exception as e_unlink: 
                        app_logger.warning(f"Failed to delete temp audio file {temp_path}: {e_unlink}")
                
        except Exception as e:
            app_logger.error(f"[TTS Speak ID: {speech_id}] Error in _speak_text: {e}", exc_info=True)
        finally:
            # Clean up player and clear current player if this speech is still active
            with self._player_lock:
                if self.current_player and self._current_speech_id == speech_id:
                    try:
                        self.current_player.close() # Close the player to release the file
                        app_logger.debug(f"[TTS Speak ID: {speech_id}] Closed current player in finally block.")
                    except Exception as close_err:
                        app_logger.error(f"[TTS Speak ID: {speech_id}] Error closing current player: {close_err}")
                    self.current_player = None
                    self._current_speech_id = None
                    
            # Also ensure the local 'player' instance is closed if it was created
            if 'player' in locals() and player is not None:
                try:
                    # Always close the local player instance to release the file
                    player.close()
                    app_logger.debug(f"[TTS Speak ID: {speech_id}] Closed local player instance in finally block.")
                except Exception as local_close_err:
                    app_logger.error(f"[TTS Speak ID: {speech_id}] Error closing local player instance: {local_close_err}")
    
    def speak_async(self, text: str, interrupt_current: bool = True, volume: float = 0.5):
        """Speaks the given text asynchronously without blocking."""
        speech_id = str(uuid.uuid4())
        app_logger.debug(f"[TTS Async ID: {speech_id}] Speak_async request. Text: '{text[:30]}...', Interrupt: {interrupt_current}, Volume: {volume}")
        if not self.is_available():
            app_logger.warning(f"[TTS Async ID: {speech_id}] TTS is not available or disabled. Cannot speak.")
            return
            
        thread = threading.Thread(target=self.speak, args=(text, interrupt_current, volume, speech_id))
        thread.daemon = True  # Allow main program to exit even if threads are running
        thread.start()
        app_logger.debug(f"[TTS Async ID: {speech_id}] Thread started for speak method.")
    
    def stop_speaking(self):
        """Stop current speech playback by stopping the AudioPlayer."""
        player_to_stop = None
        speech_id_to_stop = None
        
        with self._player_lock:
            player_to_stop = self.current_player
            speech_id_to_stop = self._current_speech_id
            # Clear current player to signal interruption to the playback loop
            self.current_player = None
            self._current_speech_id = None

        if player_to_stop:
            app_logger.debug(f"Attempting to stop current TTS playback (ID: {speech_id_to_stop}) via AudioPlayer.stop().")
            try:
                player_to_stop.stop()
                # Don't close here - let _speak_text handle cleanup
            except Exception as e:
                app_logger.error(f"Error stopping audioplayer: {e}", exc_info=True)
        else:
            app_logger.debug("stop_speaking called but no current player instance to stop.")
    
    def is_available(self) -> bool:
        """Check if TTS is available and ready to use."""
        return self.tts_settings.enabled and self.voice is not None
    
    def get_voice_info(self) -> dict:
        """Get information about the current voice model."""
        if not self.voice:
            return {"available": False}
        
        return {
            "available": True,
            "model": self.tts_settings.voice_model,
            "mode": "command_line",
            "sample_rate": self.tts_settings.sample_rate,
            "use_cuda": self.tts_settings.use_cuda,
            "models_dir": self.tts_settings.models_dir,
            "piper_exe": self.piper_exe_path
        }


# Test function for the TTS client
if __name__ == "__main__":
    from src.config.settings import load_settings
    
    try:
        settings = load_settings()
        tts_client = PiperTTSClient(settings)
        
        if tts_client.is_available():
            print("TTS client initialized successfully!")
            print(f"Voice info: {tts_client.get_voice_info()}")
            
            # Test speech
            test_text = "Hello! This is a test of the Piper text to speech system. The voice assistant is now ready to speak responses."
            print(f"Testing TTS with: '{test_text}' at default volume (1.0)")
            success = tts_client.speak(test_text)
            if success:
                print("✅ TTS test (default volume) completed successfully")
            else:
                print("❌ TTS test (default volume) failed")

            time.sleep(1) # Pause between tests

            print(f"\nTesting TTS with: '{test_text}' at 50% volume (0.5)")
            success_low_vol = tts_client.speak(test_text, volume=0.5)
            if success_low_vol:
                print("✅ TTS test (50% volume) completed successfully")
            else:
                print("❌ TTS test failed")
        else:
            print("❌ TTS client is not available")
            
    except Exception as e:
        print(f"Error testing TTS client: {e}") 