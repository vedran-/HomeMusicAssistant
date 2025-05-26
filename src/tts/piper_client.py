import os
import threading
import time
import subprocess
import tempfile
from typing import Optional
from playsound3 import playsound

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
        self._speaking_lock = threading.Lock()
        
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
    
    def speak(self, text: str, interrupt_current: bool = True) -> bool:
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
        if interrupt_current and self.is_speaking:
            self.stop_speaking()
        
        # Wait for current speech to finish if not interrupting
        if not interrupt_current:
            while self.is_speaking:
                time.sleep(0.1)
        
        try:
            with self._speaking_lock:
                self.is_speaking = True
                
            app_logger.info(f"🗣️ Speaking: '{text}'")
            self._speak_text(text)
            return True
            
        except Exception as e:
            app_logger.error(f"Error during TTS playback: {e}", exc_info=True)
            return False
        finally:
            with self._speaking_lock:
                self.is_speaking = False
    
    def _speak_text(self, text: str):
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
                
                result = subprocess.run(cmd, input=text, text=True, capture_output=True)
                
                if result.returncode == 0 and os.path.exists(temp_path):
                    # Play the generated audio file
                    playsound(temp_path)
                else:
                    app_logger.error(f"Piper CLI failed: {result.stderr}")
                    raise Exception(f"Piper CLI error: {result.stderr}")
                    
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except:
                        pass  # Ignore cleanup errors
                
        except Exception as e:
            app_logger.error(f"Error in _speak_text: {e}", exc_info=True)
            raise
    
    def speak_async(self, text: str, interrupt_current: bool = True):
        """
        Convert text to speech asynchronously (non-blocking).
        
        Args:
            text: Text to convert to speech
            interrupt_current: Whether to interrupt currently playing speech
        """
        if not self.tts_settings.enabled or not self.voice:
            return
        
        def speak_thread():
            self.speak(text, interrupt_current)
        
        thread = threading.Thread(target=speak_thread, daemon=True)
        thread.start()
    
    def stop_speaking(self):
        """Stop current speech playback."""
        with self._speaking_lock:
            if self.is_speaking:
                app_logger.debug("Stopping current TTS playback")
                self.is_speaking = False
    
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
            print(f"Testing TTS with: '{test_text}'")
            
            success = tts_client.speak(test_text)
            if success:
                print("✅ TTS test completed successfully")
            else:
                print("❌ TTS test failed")
        else:
            print("❌ TTS client is not available")
            
    except Exception as e:
        print(f"Error testing TTS client: {e}") 