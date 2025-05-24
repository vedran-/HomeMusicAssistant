import openwakeword
import pyaudio
import time
import os
import numpy as np
from src.config.settings import AppSettings
from src.utils.logger import app_logger

class WakeWordDetector:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        
        # Supported wake word models
        self.supported_models = ["hey_jarvis", "alexa"]
        self.active_model = None
        
        # Try to ensure the model directory exists
        os.makedirs(str(self.settings.paths.openwakeword_models_dir), exist_ok=True)
        
        # Use ONNX inference
        try:
            from openwakeword.model import Model
            
            # First try to load models individually
            for model_name in self.supported_models:
                try:
                    app_logger.info(f"Attempting to load '{model_name}' wake word model...")
                    
                    # Use ONNX backend
                    self.oww = Model(
                        wakeword_models=[model_name],
                        inference_framework="onnx"  # Explicitly use ONNX
                    )
                    self.active_model = model_name
                    app_logger.info(f"Successfully loaded wake word model: {model_name}")
                    break
                except Exception as e:
                    app_logger.warning(f"Could not load '{model_name}' model: {e}")
            
            # If no models loaded, try to download them
            if not self.active_model:
                app_logger.warning("No supported wake word models loaded. Attempting to download...")
                try:
                    # Try to download supported models
                    from openwakeword.utils import download_models
                    download_models(model_names=self.supported_models)
                    
                    # Try loading again after download
                    for model_name in self.supported_models:
                        try:
                            self.oww = Model(
                                wakeword_models=[model_name],
                                inference_framework="onnx"  # Explicitly use ONNX
                            )
                            self.active_model = model_name
                            app_logger.info(f"Successfully loaded wake word model after download: {model_name}")
                            break
                        except Exception as model_e:
                            app_logger.warning(f"Failed to load model after download: {model_e}")
                    
                    if not self.active_model:
                        raise ValueError(f"Failed to load any supported wake word models ({', '.join(self.supported_models)}).")
                        
                except Exception as dl_error:
                    app_logger.error(f"Failed to download wake word models: {dl_error}")
                    raise ValueError(f"Could not load or download wake word models. Please check your internet connection and try again.")
            
        except ImportError as e:
            app_logger.error(f"Error importing openwakeword modules: {e}")
            raise ImportError(f"Failed to import required openwakeword modules. Please ensure openwakeword is installed correctly.")
        
        # Configure audio settings
        self.pa = pyaudio.PyAudio()
        self.chunk_size = 1280  # 80 ms @ 16000 Hz
        self.stream = None
        self.sensitivity = self.settings.audio_settings.wake_word_sensitivity
        self.sample_rate = self.settings.audio_settings.sample_rate
        
        if self.sample_rate != 16000:
            app_logger.warning(f"OpenWakeWord typically expects 16000 Hz, but configured sample rate is {self.sample_rate}. This might affect performance.")

    def listen(self) -> bool:
        app_logger.info(f"Initializing audio stream for wake word detection (mic_idx: {self.settings.audio_settings.input_device_index or 'default'}, sample_rate: {self.sample_rate} Hz)...")
        try:
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=self.settings.audio_settings.input_device_index
            )
            app_logger.info(f"Listening for wake word '{self.active_model}'...")

            while True:
                audio_chunk = self.stream.read(self.chunk_size)
                
                # Convert the audio bytes to the right format
                audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
                
                # Get prediction
                prediction = self.oww.predict(audio_np)

                # Get prediction for the active model
                if self.active_model in prediction and prediction[self.active_model] > self.sensitivity:
                    app_logger.info(f"Wake word '{self.active_model}' detected with score {prediction[self.active_model]:.2f}!")
                    self.stop_listening()
                    return True

        except Exception as e:
            app_logger.error(f"Error during wake word detection: {e}")
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.stream = None
            return False
        finally:
            self.stop_listening()

    def stop_listening(self):
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                app_logger.error(f"Error stopping wake word audio stream: {e}")
            finally:
                self.stream = None

    def __del__(self):
        # Clean up PyAudio instance when the detector is garbage collected
        if hasattr(self, 'pa') and self.pa:
            try:
                self.pa.terminate()
                app_logger.debug("PyAudio instance terminated for WakeWordDetector.")
            except Exception as e:
                app_logger.error(f"Error terminating PyAudio instance in WakeWordDetector: {e}")

if __name__ == '__main__':
    # This is for basic testing of the WakeWordDetector
    # It requires a config.json to be present and correctly configured.
    from src.config.settings import load_settings
    import os

    # Determine config path relative to this script file for robust testing
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(current_dir, "..", "..", "config.json")
    
    if not os.path.exists(config_file_path):
        print(f"ERROR: config.json not found at {config_file_path}. Please create it from config.template.json.")
        config_file_path = "config.json" 
        if not os.path.exists(config_file_path):
             print(f"ERROR: config.json not found at {os.path.abspath(config_file_path)} either. Aborting test.")
             exit(1)
        else:
            print(f"Found config.json at {os.path.abspath(config_file_path)}")

    try:
        settings = load_settings(config_path=config_file_path)
        app_logger.info("Settings loaded for WakeWordDetector test.")
        
        # Ensure openwakeword_models_dir exists
        if not os.path.exists(settings.paths.openwakeword_models_dir):
             os.makedirs(settings.paths.openwakeword_models_dir, exist_ok=True)
             app_logger.info(f"Created openwakeword_models_dir at {settings.paths.openwakeword_models_dir}")

        detector = WakeWordDetector(settings)
        app_logger.info("WakeWordDetector initialized. Starting to listen...")
        
        if detector.listen():
            app_logger.info("Wake word detected by test!")
        else:
            app_logger.info("Wake word not detected or an error occurred during test.")
            
    except FileNotFoundError as e:
        app_logger.error(f"Configuration file error: {e}")
    except Exception as e:
        app_logger.error(f"An error occurred during WakeWordDetector test: {e}", exc_info=True)
    finally:
        # Explicitly delete detector to trigger __del__ for PyAudio cleanup if detector was created
        if 'detector' in locals() and detector and hasattr(detector, 'pa') and detector.pa:
            detector.pa.terminate() # Ensure PyAudio is terminated in test
        app_logger.info("WakeWordDetector test finished.")