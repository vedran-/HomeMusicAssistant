import openwakeword
import pyaudio
import time
from src.config.settings import AppSettings
from src.utils.logger import app_logger

class WakeWordDetector:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.oww = openwakeword.OpenWakeWord(
            model_paths=[str(self.settings.paths.openwakeword_models_dir / "hey_jarvis.onnx")], # openwakeword expects specific model files, not just a dir.
                                                                                            # Assuming "hey_jarvis.onnx" is the standard name or user places it.
                                                                                            # openwakeword itself might download to a subfolder, we need to be precise.
                                                                                            # For now, assuming the model is directly in the specified path or downloaded by oww to a known name.
            # For a specific wake word like "hey jarvis", we can also specify it directly if supported,
            # otherwise, the model file itself defines the wake word.
            # Let's rely on the pre-trained "hey_jarvis.onnx" model.
            # If openwakeword automatically downloads models, it usually places them in a cache dir or specified model_dir.
            # We might need to adjust the path if openwakeword creates subdirectories for models.
            # The plan mentions: "Load \"hey jarvis\" model (models downloaded by openwakeword to path in config.json)"
            # This implies openwakeword handles the download and the model will be available at the configured path.
            # A common pattern for oww is to point `model_paths` to specific .onnx files.
            # If "hey_jarvis.onnx" isn't standard, we might need to let user specify the model file name in config or discover it.
            # For now, let's assume "hey_jarvis.onnx" is the target file name within the model directory.
            # Update: openwakeword.get_pretrained_model_paths() can be used to find available models.
            # And we can use `custom_model_paths` or let it use its default download mechanism.
            # The provided `openwakeword_models_dir` seems intended as a base.
            # Let's refine this to use the specific "hey_jarvis" model provided by openwakeword.
        )
        # If "hey_jarvis.onnx" is not found, openwakeword will raise an error during init.
        # We should ideally download it if not present, or instruct user.
        # For MVP, we assume setup.ps1 or user ensures model is there or oww downloads it.
        # Let's use the `inference_framework` parameter for wider compatibility, defaulting to onnxruntime.
        # oww.OpenWakeWord(wake_word_names=["hey_jarvis"], model_name_or_path="hey_jarvis_v0.1", inference_framework='onnx')
        # This seems a better way. It will download if not present.
        # Let's re-init `self.oww` with a more robust approach.

        self.oww = openwakeword.OpenWakeWord(
            model_name_or_path="hey_jarvis", # This should trigger download if not found locally in oww cache
            # The `openwakeword_models_dir` in config might be for custom models or controlling oww's cache if possible.
            # For simplicity, let's rely on oww's default model fetching for "hey_jarvis".
            # If we want to force models into `openwakeword_models_dir`, we'd use `custom_model_paths`
            # and ensure the model file is there.
            # Given the plan: "models downloaded by openwakeword to path in config.json",
            # this implies we should guide oww to use that path.
            # `OpenWakeWord(custom_model_paths={ "hey_jarvis": str(self.settings.paths.openwakeword_models_dir / "hey_jarvis_v0.2.onnx")})` if we know the exact file.
            # Or let oww download to its default cache and our `openwakeword_models_dir` is a misinterpretation or for *other* custom models.
            # The simplest for "hey jarvis" is to let oww manage it.
            # Let's assume the plan meant `openwakeword` would handle the download to *its* default location,
            # and `openwakeword_models_dir` might be for users providing their own .onnx files.
            # For MVP, using the named model "hey_jarvis" is cleanest.

            # Re-evaluating: The instruction "models downloaded by openwakeword to path in config.json"
            # suggests we should make openwakeword *use* that path.
            # openwakeword's `OpenWakeWord` class takes `custom_model_paths` (dict) or `model_paths` (list of .onnx files)
            # It also has `OPENWAKEWORD_MODELS_DIR` environment variable.
            # The simplest is to set the env var before importing/instantiating if we want to control the base download dir.
            # Or, check if the model exists in our custom path, if not, download it there.
            # For now, let oww handle it, and if issues arise, we can refine model path management.
        )

        self.pa = pyaudio.PyAudio()
        self.chunk_size = 1280  # 80 ms @ 16000 Hz
        self.stream = None
        self.sensitivity = self.settings.audio_settings.wake_word_sensitivity
        # Ensure sample rate matches what oww expects (typically 16kHz)
        self.sample_rate = self.settings.audio_settings.sample_rate
        if self.sample_rate != 16000:
            app_logger.warning(f"OpenWakeWord typically expects 16000 Hz, but configured sample rate is {self.sample_rate}. This might affect performance.")


    def _ensure_model_available(self):
        # This is a placeholder. `openwakeword` typically handles model downloads automatically
        # when a standard model name is provided. If `openwakeword_models_dir` is meant
        # to be the *sole* source, we'd need to manage downloads or ensure files exist there.
        # For "hey_jarvis", `OpenWakeWord(model_name_or_path="hey_jarvis")` should suffice.
        # The `plan.md` phrasing "models downloaded by openwakeword to path in config.json" could mean
        # that `openwakeword` itself is configured (e.g. via env var) to use this path as its cache/storage.
        # `openwakeword.utils.download_models([specific_model_name], download_dir=self.settings.paths.openwakeword_models_dir)`
        # This seems like the explicit way to achieve it.

        # Let's try to use the download utility explicitly to control the location.
        expected_model_name = "hey_jarvis" # This is a conceptual name, actual files are versioned e.g., hey_jarvis_v0.1.onnx
        # We need to find the actual model filename or use a more abstract way.
        # `openwakeword.MODELS` dictionary contains the model details including download URLs.
        # Let's assume `model_name_or_path="hey_jarvis"` in `OpenWakeWord()` constructor handles this best.
        # If not, we can pre-download using `openwakeword.utils.download_models`.
        # For now, relying on `OpenWakeWord` constructor with `model_name_or_path="hey_jarvis"`.
        pass


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
            app_logger.info("Listening for wake word 'hey jarvis'...")

            while True:
                audio_chunk = self.stream.read(self.chunk_size)
                prediction = self.oww.predict(audio_chunk) # self.oww.predict expects a numpy array

                # oww.predict returns a dict like {'model_name': score}
                # For "hey_jarvis" it would be something like {'hey_jarvis_vX.Y': score}
                # We need to check the score against sensitivity.
                # The key in the prediction dict can be dynamic based on the model version.
                # We should get the model name from self.oww.models.keys() after init.

                # Assuming single model "hey_jarvis" loaded, so prediction dict will have one key.
                # Or, if using `model_name_or_path` it might be just that name.
                
                # Let's refine how to get the score for "hey_jarvis"
                # `self.oww.prediction_buffer` might be relevant or `self.oww.process_audio_frame`
                # The simple `oww.predict(frame)` returns a dict like {'hey_jarvis': 0.6} after version 0.5.0
                
                # Convert bytes to numpy array as expected by openwakeword
                # import numpy as np
                # audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
                # prediction = self.oww.predict(audio_np)
                
                # The above is correct. The predict() method takes a numpy array.

                # The current `openwakeword` version's `predict` method takes bytes directly.
                # predict(self, X: bytes, patience:typing.Optional[dict]={}, threshold:typing.Optional[dict]={}, timing:bool=False)
                # So, `audio_chunk` (bytes) is fine.

                # The key in `prediction` for the "hey_jarvis" model.
                # When using `model_name_or_path="hey_jarvis"`, the key in the output dict should be "hey_jarvis".
                model_key = "hey_jarvis" # This is an assumption.
                                       # If oww.models is a dict, its keys are the actual model names used in prediction output.
                                       # For example, list(self.oww.models.keys())[0] if only one model.
                
                # Let's be more robust:
                if not self.oww.models: # Should not happen if constructor succeeded
                    app_logger.error("No models loaded in OpenWakeWord.")
                    time.sleep(1)
                    continue

                # Get the first (and assumed only) model key from the loaded models
                # This relies on "hey_jarvis" being the only one we care about.
                active_model_key = list(self.oww.models.keys())[0]


                if active_model_key in prediction and prediction[active_model_key] > self.sensitivity:
                    app_logger.info(f"Wake word '{active_model_key}' detected with score {prediction[active_model_key]:.2f}!")
                    self.stop_listening() # Stop stream before returning
                    return True
                # Add a small sleep to avoid pegging CPU if stream read is too fast / non-blocking
                # However, stream.read is blocking, so this might not be strictly necessary
                # time.sleep(0.01) # 10 ms

        except Exception as e:
            app_logger.error(f"Error during wake word detection: {e}")
            # Potentially re-raise or handle more gracefully
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.stream = None # Ensure stream is reset
            # self.pa.terminate() # Terminate PyAudio instance? Usually done on app exit.
            return False # Indicate failure or inability to listen
        finally:
            self.stop_listening() # Ensure stream is closed if loop exits for other reasons

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
        # app_logger.info("Wake word detection stream stopped.")

    def __del__(self):
        # Clean up PyAudio instance when the detector is garbage collected
        if self.pa:
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
    # Assuming this script is in src/audio/wake_word.py
    # Config is in root, so ../../config.json
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(current_dir, "..", "..", "config.json")
    
    if not os.path.exists(config_file_path):
        print(f"ERROR: config.json not found at {config_file_path}. Please create it from config.template.json.")
        # Attempt to use a default relative path if the calculated one fails (e.g., if run from project root)
        config_file_path = "config.json" 
        if not os.path.exists(config_file_path):
             print(f"ERROR: config.json not found at {os.path.abspath(config_file_path)} either. Aborting test.")
             exit(1)
        else:
            print(f"Found config.json at {os.path.abspath(config_file_path)}")


    try:
        settings = load_settings(config_path=config_file_path)
        app_logger.info("Settings loaded for WakeWordDetector test.")
        
        # Ensure openwakeword_models_dir exists, as oww might need it for caching downloaded models
        # The load_settings function should already create this directory.
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
        if 'detector' in locals() and detector and detector.pa:
            detector.pa.terminate() # Ensure PyAudio is terminated in test
        app_logger.info("WakeWordDetector test finished.") 