import pyaudio
import wave
import numpy as np
import time
import os
import tempfile
from typing import Optional, List, Dict

from src.config.settings import AppSettings
from src.utils.logger import app_logger

class AudioCapturer:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.pa = pyaudio.PyAudio()
        self.sample_rate = self.settings.audio_settings.sample_rate
        self.chunk_size = 1024  # Smaller chunk for faster silence detection responsiveness
        self.channels = 1
        self.format = pyaudio.paInt16  # Corresponds to 2 bytes per sample
        self.silence_threshold_seconds = self.settings.audio_settings.silence_threshold_seconds
        self.initial_silence_allowance_seconds = self.settings.audio_settings.initial_silence_allowance_seconds
        
        # Audio energy threshold for silence detection. This might need tuning.
        # It's a heuristic. Lower values are more sensitive to noise.
        self.silence_rms_threshold = 500  # Example value, assuming 16-bit audio. Max is 32767.

        # Determine the input device index based on settings
        self.input_device_index = None
        
        # If a device name keyword is provided, try to find a matching device
        if self.settings.audio_settings.input_device_name_keyword:
            self._find_device_by_keyword()
        else:
            # Otherwise, use the specified index or default
            self.input_device_index = self.settings.audio_settings.input_device_index
            
        self._validate_input_device()

    def _find_device_by_keyword(self):
        """Find a microphone device by matching the keyword in its name."""
        keyword = self.settings.audio_settings.input_device_name_keyword.lower()
        app_logger.info(f"Searching for microphone with keyword '{keyword}' in its name...")
        
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
                        app_logger.info(f"Found matching device: Index {i} - '{info.get('name')}'")
                    else:
                        app_logger.info(f"Found another matching device: Index {i} - '{info.get('name')}' (using first match)")
        
        if matched_device:
            self.input_device_index = matched_device[0]
            app_logger.info(f"Selected microphone with index {self.input_device_index} ('{matched_device[1]}')")
        else:
            app_logger.warning(f"No microphone found with keyword '{keyword}' in its name. Available devices:")
            for idx, name in all_devices:
                app_logger.warning(f"  Index {idx}: {name}")
            app_logger.warning("Falling back to default input device.")
            self.input_device_index = None

    def _validate_input_device(self):
        if self.input_device_index is not None:
            try:
                device_info = self.pa.get_device_info_by_index(self.input_device_index)
                if device_info.get('maxInputChannels', 0) < 1:
                    app_logger.warning(
                        f"Selected input device index {self.input_device_index} ('{device_info.get('name')}') "
                        f"may not be an input device. Max input channels: {device_info.get('maxInputChannels')}. "
                        f"Attempting to use it anyway."
                    )
                else:
                    app_logger.info(f"Using audio input device: '{device_info.get('name')}' (Index: {self.input_device_index})")
            except OSError as e:
                app_logger.error(f"Invalid input device index {self.input_device_index}. PyAudio error: {e}. Falling back to default input device.")
                self.input_device_index = None # Fallback to default
        
        if self.input_device_index is None:
            try:
                default_device_info = self.pa.get_default_input_device_info()
                self.input_device_index = default_device_info['index']
                app_logger.info(f"Using default audio input device: '{default_device_info.get('name')}' (Index: {self.input_device_index})")
            except IOError as e:
                app_logger.error(f"No default input device found or error accessing it: {e}. Audio capture may fail.")
                raise RuntimeError("Failed to initialize audio input device.") from e


    def list_available_microphones(self) -> List[Dict[str, any]]:
        app_logger.info("Available audio input devices:")
        devices = []
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            if info.get('maxInputChannels', 0) > 0: # Check if it's an input device
                device_info = {
                    "index": info.get('index'),
                    "name": info.get('name'),
                    "hostApiName": self.pa.get_host_api_info_by_index(info.get('hostApi')).get('name'),
                    "maxInputChannels": info.get('maxInputChannels'),
                    "defaultSampleRate": info.get('defaultSampleRate')
                }
                app_logger.info(
                    f"  Index {device_info['index']}: {device_info['name']} "
                    f"(API: {device_info['hostApiName']}, Max Channels: {device_info['maxInputChannels']}, Default SR: {device_info['defaultSampleRate']})"
                )
                devices.append(device_info)
        if not devices:
            app_logger.warning("No input devices found. Audio capture will likely fail.")
        return devices

    def _is_silent(self, audio_chunk: bytes) -> bool:
        """Checks if the audio chunk is silent based on RMS."""
        audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
        if audio_np.size == 0: # handle empty chunk case
            return True # Or False, depending on desired behavior for empty inputs
        rms = np.sqrt(np.mean(audio_np.astype(np.float64)**2)) # Use float64 for mean to avoid overflow with large int16 squares
        return rms < self.silence_rms_threshold

    def capture_audio_after_wake(self, output_filename_base: str = "captured_audio") -> Optional[str]:
        app_logger.info("Wake word detected. Starting audio capture...")
        
        stream = None
        try:
            stream = self.pa.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=self.input_device_index
            )
        except Exception as e:
            app_logger.error(f"Failed to open audio stream: {e}", exc_info=True)
            return None

        app_logger.info("Recording... Speak now.")

        frames = []
        speech_detected = False  # Track if we've detected any speech
        initial_silent_chunks_count = 0
        post_speech_silent_chunks_count = 0
        
        # Calculate chunk thresholds
        max_initial_silent_chunks = int(self.initial_silence_allowance_seconds * self.sample_rate / self.chunk_size)
        max_post_speech_silent_chunks = int(self.silence_threshold_seconds * self.sample_rate / self.chunk_size)
        
        if max_initial_silent_chunks == 0:
            max_initial_silent_chunks = 1
            app_logger.warning(f"Initial silence allowance ({self.initial_silence_allowance_seconds}s) is very short relative to chunk size. Effective duration might be up to one chunk time ({self.chunk_size/self.sample_rate:.2f}s).")
        
        if max_post_speech_silent_chunks == 0:
            max_post_speech_silent_chunks = 1 
            app_logger.warning(f"Silence threshold ({self.silence_threshold_seconds}s) is very short relative to chunk size. Effective silence duration might be up to one chunk time ({self.chunk_size/self.sample_rate:.2f}s).")

        recording_started_time = time.time()
        max_recording_duration = 30

        while True:
            try:
                audio_chunk = stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(audio_chunk)

                is_silent = self._is_silent(audio_chunk)
                
                if not speech_detected:
                    # We're in the initial phase - waiting for first speech
                    if is_silent:
                        initial_silent_chunks_count += 1
                        if initial_silent_chunks_count >= max_initial_silent_chunks:
                            app_logger.info(f"Initial silence timeout ({self.initial_silence_allowance_seconds}s) reached before any speech detected. Stopping recording.")
                            break
                    else:
                        # First non-silent chunk detected - speech has started
                        speech_detected = True
                        post_speech_silent_chunks_count = 0
                        app_logger.info("Speech detected. Now monitoring for end-of-speech silence.")
                else:
                    # We're in the post-speech phase - waiting for end silence
                    if is_silent:
                        post_speech_silent_chunks_count += 1
                        if post_speech_silent_chunks_count >= max_post_speech_silent_chunks:
                            app_logger.info(f"End-of-speech silence detected for {self.silence_threshold_seconds} seconds. Stopping recording.")
                            break
                    else:
                        # Reset silence counter when we detect more speech
                        post_speech_silent_chunks_count = 0
                
                if time.time() - recording_started_time > max_recording_duration:
                    app_logger.warning(f"Max recording duration of {max_recording_duration}s reached. Stopping.")
                    break

            except IOError as e:
                app_logger.error(f"IOError during audio capture: {e}", exc_info=True)
                break
            except Exception as e:
                app_logger.error(f"Unexpected error during audio capture: {e}", exc_info=True)
                break
        
        app_logger.info("Recording finished.")

        if stream:
            try:
                stream.stop_stream()
                stream.close()
            except Exception as e:
                app_logger.error(f"Error closing audio stream: {e}", exc_info=True)
        
        if not frames:
            app_logger.warning("No audio was recorded.")
            return None
        
        # Check if we never detected any speech (entire recording was silence)
        if not speech_detected:
            app_logger.info("No speech detected in the entire recording (silence-only). Skipping processing.")
            return None

        temp_dir = tempfile.gettempdir()
        safe_output_filename_base = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in output_filename_base)
        wav_filename = os.path.join(temp_dir, f"{safe_output_filename_base}_{int(time.time())}.wav")

        try:
            with wave.open(wav_filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.pa.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(frames))
            app_logger.info(f"Audio saved to temporary file: {wav_filename}")
            return wav_filename
        except Exception as e:
            app_logger.error(f"Failed to save audio to WAV file {wav_filename}: {e}", exc_info=True)
            return None

    def capture_test(self, duration: float = 5.0, output_filename_base: str = "test_audio") -> Optional[str]:
        """
        Capture audio for testing purposes for a fixed duration.
        
        Args:
            duration: Recording duration in seconds
            output_filename_base: Base name for the output file
            
        Returns:
            Path to the saved audio file or None if capture failed
        """
        app_logger.info(f"Starting test audio capture for {duration} seconds...")
        
        stream = None
        try:
            stream = self.pa.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=self.input_device_index
            )
        except Exception as e:
            app_logger.error(f"Failed to open audio stream for test capture: {e}", exc_info=True)
            return None

        app_logger.info(f"Recording for {duration} seconds... Speak now.")

        frames = []
        chunks_to_record = int((self.sample_rate / self.chunk_size) * duration)
        
        for _ in range(chunks_to_record):
            try:
                audio_chunk = stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(audio_chunk)
            except IOError as e:
                app_logger.error(f"IOError during test audio capture: {e}", exc_info=True)
                break
            except Exception as e:
                app_logger.error(f"Unexpected error during test audio capture: {e}", exc_info=True)
                break
        
        app_logger.info("Test recording finished.")

        if stream:
            try:
                stream.stop_stream()
                stream.close()
            except Exception as e:
                app_logger.error(f"Error closing test audio stream: {e}", exc_info=True)
        
        if not frames:
            app_logger.warning("No audio was recorded during test.")
            return None

        # Save to either the configured output directory or temp directory
        if hasattr(self.settings.paths, 'audio_output_dir') and self.settings.paths.audio_output_dir:
            os.makedirs(self.settings.paths.audio_output_dir, exist_ok=True)
            output_dir = self.settings.paths.audio_output_dir
        else:
            output_dir = tempfile.gettempdir()
            
        safe_output_filename_base = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in output_filename_base)
        wav_filename = os.path.join(output_dir, f"{safe_output_filename_base}_{int(time.time())}.wav")

        try:
            with wave.open(wav_filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.pa.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(frames))
            app_logger.info(f"Test audio saved to file: {wav_filename}")
            return wav_filename
        except Exception as e:
            app_logger.error(f"Failed to save test audio to WAV file {wav_filename}: {e}", exc_info=True)
            return None

    def __del__(self):
        if self.pa:
            try:
                self.pa.terminate()
                app_logger.debug("PyAudio instance terminated for AudioCapturer.")
            except Exception as e:
                app_logger.error(f"Error terminating PyAudio instance in AudioCapturer: {e}", exc_info=True)


if __name__ == '__main__':
    from src.config.settings import load_settings
    
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
        app_logger.info("Settings loaded for AudioCapturer test.")

        capturer = AudioCapturer(settings)
        
        app_logger.info("Listing microphones (call this once, e.g. at app start or for setup):")
        capturer.list_available_microphones()
        
        if settings.audio_settings.input_device_index is None:
            app_logger.warning("No input_device_index specified in config.json/audio_settings. Using default.")

        # Test the fixed duration audio capture
        app_logger.info("Starting fixed duration test capture (5 seconds)...")
        test_file = capturer.capture_test(duration=5.0)
        
        if test_file:
            app_logger.info(f"Fixed duration test capture saved to: {test_file}")
        else:
            app_logger.error("Fixed duration test capture failed or no audio recorded.")
            
        # Test the silence-based audio capture
        app_logger.info("Starting capture test (simulating wake word detected)...")
        output_file = capturer.capture_audio_after_wake(output_filename_base="test_capture")
        
        if output_file:
            app_logger.info(f"Test capture saved to: {output_file}")
        else:
            app_logger.error("Test capture failed or no audio recorded.")

    except RuntimeError as e:
        app_logger.error(f"Failed to initialize AudioCapturer: {e}")
    except FileNotFoundError as e:
        app_logger.error(f"Configuration file error: {e}")
    except Exception as e:
        app_logger.error(f"An error occurred during AudioCapturer test: {e}", exc_info=True)
    finally:
        if 'capturer' in locals() and capturer and capturer.pa:
            capturer.pa.terminate()
        app_logger.info("AudioCapturer test finished.") 