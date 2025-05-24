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
        
        # Limit to only supported wake word models - alexa first as default
        self.supported_models = ["alexa", "hey_jarvis"]
        self.active_model = None
        
        # Try to ensure the model directory exists
        os.makedirs(str(self.settings.paths.openwakeword_models_dir), exist_ok=True)
        
        # Configure audio settings
        self.pa = pyaudio.PyAudio()
        self.chunk_size = 1280  # 80 ms @ 16000 Hz
        self.stream = None
        self.sensitivity = self.settings.audio_settings.wake_word_sensitivity
        self.sample_rate = self.settings.audio_settings.sample_rate
        
        if self.sample_rate != 16000:
            app_logger.warning(f"OpenWakeWord typically expects 16000 Hz, but configured sample rate is {self.sample_rate}. This might affect performance.")
        
        # Determine the input device index based on settings
        self.input_device_index = None
        
        # If a device name keyword is provided, try to find a matching device
        if self.settings.audio_settings.input_device_name_keyword:
            self._find_device_by_keyword()
        else:
            # Otherwise, use the specified index or default
            self.input_device_index = self.settings.audio_settings.input_device_index
            
        self._validate_input_device()
        
        # Initialize the wake word model
        self._initialize_model()

    def _find_device_by_keyword(self):
        """Find a microphone device by matching the keyword in its name."""
        keyword = self.settings.audio_settings.input_device_name_keyword.lower()
        app_logger.info(f"Wake word detector searching for microphone with keyword '{keyword}' in its name...")
        
        matched_device = None
        all_devices = []
        
        # First list all available input devices
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            if info.get('maxInputChannels', 0) > 0:  # Check if it's an input device
                device_name = info.get('name', '').lower()
                all_devices.append((i, device_name))
                if keyword in device_name:
                    if matched_device is None:
                        matched_device = (i, device_name)
                        app_logger.info(f"Wake word detector found matching device: Index {i} - '{info.get('name')}'")
                    else:
                        app_logger.info(f"Wake word detector found another matching device: Index {i} - '{info.get('name')}' (using first match)")
        
        if matched_device:
            self.input_device_index = matched_device[0]
            app_logger.info(f"Wake word detector selected microphone with index {self.input_device_index} ('{matched_device[1]}')")
        else:
            app_logger.warning(f"Wake word detector: No microphone found with keyword '{keyword}' in its name. Available devices:")
            for idx, name in all_devices:
                app_logger.warning(f"  Index {idx}: {name}")
            app_logger.warning("Wake word detector falling back to default input device.")
            self.input_device_index = None

    def _validate_input_device(self):
        if self.input_device_index is not None:
            try:
                device_info = self.pa.get_device_info_by_index(self.input_device_index)
                if device_info.get('maxInputChannels', 0) < 1:
                    app_logger.warning(
                        f"Wake word detector: Selected input device index {self.input_device_index} ('{device_info.get('name')}') "
                        f"may not be an input device. Max input channels: {device_info.get('maxInputChannels')}. "
                        f"Attempting to use it anyway."
                    )
                else:
                    app_logger.info(f"Wake word detector using audio input device: '{device_info.get('name')}' (Index: {self.input_device_index})")
            except OSError as e:
                app_logger.error(f"Wake word detector: Invalid input device index {self.input_device_index}. PyAudio error: {e}. Falling back to default input device.")
                self.input_device_index = None # Fallback to default
        
        if self.input_device_index is None:
            try:
                default_device_info = self.pa.get_default_input_device_info()
                self.input_device_index = default_device_info['index']
                app_logger.info(f"Wake word detector using default audio input device: '{default_device_info.get('name')}' (Index: {self.input_device_index})")
            except IOError as e:
                app_logger.error(f"Wake word detector: No default input device found or error accessing it: {e}. Audio capture may fail.")
                raise RuntimeError("Failed to initialize audio input device for wake word detection.") from e

    def _initialize_model(self):
        """Initialize or reinitialize the openwakeword model."""
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

    def _reset_model_state(self):
        """Reset the openwakeword model state to prevent continuous detections."""
        try:
            app_logger.debug("Resetting wake word model state...")
            
            if hasattr(self, 'oww'):
                # Create silent audio to flush the model's internal buffer more thoroughly
                # Use multiple chunks to ensure complete clearing
                silent_chunk = np.zeros(self.chunk_size, dtype=np.int16)
                
                # Process several silent chunks to clear the internal state completely
                # This ensures any residual audio patterns are cleared
                for i in range(5):  # Increased from 2 to 5 for better clearing
                    self.oww.predict(silent_chunk)
                    
                app_logger.debug("Wake word model buffer cleared with 5 silent predictions")
                
        except Exception as e:
            app_logger.error(f"Error resetting model state: {e}")

    def listen(self) -> bool:
        app_logger.info(f"Initializing audio stream for wake word detection (mic_idx: {self.input_device_index or 'default'}, sample_rate: {self.sample_rate} Hz)...")
        try:
            # Ensure any previous stream is closed
            self.stop_listening()
            
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=self.input_device_index
            )
            app_logger.info(f"Listening for wake word '{self.active_model}'...")

            while True:
                audio_chunk = self.stream.read(self.chunk_size, exception_on_overflow=False)
                
                # Convert the audio bytes to the right format
                audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
                
                # Get prediction
                prediction = self.oww.predict(audio_np)

                # Get prediction for the active model
                if self.active_model in prediction and prediction[self.active_model] > self.sensitivity:
                    app_logger.info(f"Wake word '{self.active_model}' detected with score {prediction[self.active_model]:.2f}!")
                    self.stop_listening()
                    
                    # Improved reset to prevent continuous detection
                    self._reset_model_state()
                    
                    # Add a longer cooldown period to prevent immediate re-triggering
                    # This gives time for any residual audio/echo to clear
                    cooldown_time = 0.3  # Increased from 0.05s to 0.3s
                    app_logger.debug(f"Wake word cooldown period: {cooldown_time}s")
                    time.sleep(cooldown_time)
                    
                    return True

        except Exception as e:
            app_logger.error(f"Error during wake word detection: {e}")
            self.stop_listening()
            return False

    def stop_listening(self):
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            except Exception as e:
                app_logger.error(f"Error stopping wake word audio stream: {e}")
            finally:
                self.stream = None

    def __del__(self):
        # Clean up PyAudio instance when the detector is garbage collected
        self.stop_listening()
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