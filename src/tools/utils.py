import subprocess
import logging
import threading
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

# Global variables to track active volume transition thread
_active_volume_thread: Optional[threading.Thread] = None
_volume_thread_lock = threading.Lock()
_volume_transition_cancelled = threading.Event()

# Windows volume control imports
try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    import pythoncom
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False

util_logger = logging.getLogger(__name__)

def GetSystemVolume() -> Optional[int]:
    """
    Get the current system volume percentage using pycaw (Windows).
    
    Returns:
        Current volume percentage (0-100) or None if failed
    """
    if not PYCAW_AVAILABLE:
        util_logger.error("pycaw library not available. Install with: pip install pycaw comtypes")
        return None
        
    try:
        pythoncom.CoInitialize()
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        volume_scalar = volume.GetMasterVolumeLevelScalar()
        volume_percentage = int(round(volume_scalar * 100))
        
        util_logger.debug(f"Current system volume: {volume_percentage}%")
        return volume_percentage
        
    except Exception as e:
        util_logger.error(f"Failed to get system volume: {e}")
        return None
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass

def SetSystemVolume(percentage: Union[int, float], duration: Optional[float] = None, steps: int = 20) -> bool:
    """
    Set the system volume to a specific percentage using pycaw (Windows).
    
    Args:
        percentage: Volume percentage (0-100)
        duration: If provided, gradually change volume over this duration (seconds).
                 If None, change volume instantly.
        steps: Number of intermediate steps for gradual change (default: 20)
        
    Returns:
        True if successful, False otherwise
    """
    if not PYCAW_AVAILABLE:
        util_logger.error("pycaw library not available. Install with: pip install pycaw comtypes")
        return False
        
    # Convert to float and validate range
    try:
        volume_percent = float(percentage)
        if volume_percent < 0 or volume_percent > 100:
            util_logger.error(f"Invalid volume percentage: {volume_percent}. Must be 0-100.")
            return False
    except (ValueError, TypeError):
        util_logger.error(f"Invalid volume percentage: {percentage}. Must be a number 0-100.")
        return False
    
    # If no duration specified, use instant volume change
    if duration is None or duration <= 0:
        return _set_volume_instant(volume_percent)
    
    # Use gradual volume change in a separate thread
    with _volume_thread_lock:
        # Cancel any existing volume transition
        global _active_volume_thread, _volume_transition_cancelled
        if _active_volume_thread and _active_volume_thread.is_alive():
            util_logger.debug("Cancelling previous volume transition")
            _volume_transition_cancelled.set()
            # Give the previous thread a moment to notice cancellation
            time.sleep(0.05)
        
        # Reset cancellation flag for new transition
        _volume_transition_cancelled.clear()
        
        thread = threading.Thread(
            target=_gradual_volume_change,
            args=(volume_percent, duration, steps),
            daemon=True,
            name="VolumeTransition"
        )
        _active_volume_thread = thread
        thread.start()
    
    util_logger.debug(f"Started gradual volume transition to {volume_percent}% over {duration}s")
    return True

def _set_volume_instant(percentage: float) -> bool:
    """
    Internal function to set volume instantly.
    
    Args:
        percentage: Volume percentage (0-100), already validated
        
    Returns:
        True if successful, False otherwise
    """
    try:
        pythoncom.CoInitialize()
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        
        # Convert percentage to scalar (0.0 - 1.0)
        volume_scalar = percentage / 100.0
        volume.SetMasterVolumeLevelScalar(volume_scalar, None)
        
        util_logger.debug(f"System volume set to {percentage}%")
        return True
        
    except Exception as e:
        util_logger.error(f"Failed to set system volume: {e}")
        return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass

def _gradual_volume_change(target_percentage: float, duration: float, steps: int) -> None:
    """
    Internal function to gradually change volume over time.
    Runs in a separate thread.
    
    Args:
        target_percentage: Target volume percentage (0-100)
        duration: Duration of the transition in seconds
        steps: Number of intermediate steps
    """
    try:
        # Get current volume
        current_volume = GetSystemVolume()
        if current_volume is None:
            util_logger.error("Could not get current volume for gradual change")
            return
        
        # Check if we're already at the target volume
        if abs(current_volume - target_percentage) < 1:
            util_logger.debug(f"Already at target volume {target_percentage}%, skipping transition")
            return
        
        # Calculate step parameters
        volume_diff = target_percentage - current_volume
        step_size = volume_diff / steps
        step_duration = duration / steps
        
        util_logger.debug(f"Gradual volume change: {current_volume}% → {target_percentage}% "
                         f"over {duration}s in {steps} steps")
        
        # Perform gradual change
        for i in range(1, steps + 1):
            # Check for cancellation
            if _volume_transition_cancelled.is_set():
                util_logger.debug("Volume transition cancelled")
                return
            
            intermediate_volume = current_volume + (step_size * i)
            
            # Ensure we don't exceed bounds due to floating point precision
            intermediate_volume = max(0, min(100, intermediate_volume))
            
            if not _set_volume_instant(intermediate_volume):
                util_logger.error(f"Failed to set intermediate volume at step {i}")
                return
            
            # Sleep between steps (except after the last step)
            if i < steps:
                # Use cancellation-aware sleep
                if _volume_transition_cancelled.wait(step_duration):
                    util_logger.debug("Volume transition cancelled during sleep")
                    return
        
        util_logger.debug(f"Gradual volume change completed: {target_percentage}%")
        
    except Exception as e:
        util_logger.error(f"Error during gradual volume change: {e}", exc_info=True)

def _SetSystemVolumeGradual(percentage: Union[int, float], duration: float = 2.0, steps: int = 20) -> bool:
    """
    Internal convenience function to set system volume with gradual transition.
    
    Args:
        percentage: Target volume percentage (0-100)
        duration: Duration of the transition in seconds (default: 2.0)
        steps: Number of intermediate steps (default: 20)
        
    Returns:
        True if transition started successfully, False otherwise
    """
    return SetSystemVolume(percentage, duration=duration, steps=steps)

def _CancelVolumeTransition() -> bool:
    """
    Internal function to cancel any active volume transition.
    
    Returns:
        True if a transition was cancelled, False if no transition was active
    """
    global _active_volume_thread, _volume_transition_cancelled
    
    with _volume_thread_lock:
        if _active_volume_thread and _active_volume_thread.is_alive():
            util_logger.debug("Cancelling active volume transition")
            _volume_transition_cancelled.set()
            return True
        else:
            util_logger.debug("No active volume transition to cancel")
            return False

def run_ahk_script(
    script_path: Union[str, Path],
    args: Optional[List[str]] = None,
    autohotkey_exe_path: Union[str, Path] = "AutoHotkey.exe",
    timeout: Optional[int] = 30,
    cwd: Optional[Union[str, Path]] = None,
    logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """
    Runs an AutoHotkey script with the given parameters.

    Args:
        script_path: Absolute path to the .ahk script.
        args: List of arguments to pass to the script.
        autohotkey_exe_path: Path to the AutoHotkey executable.
                             Defaults to "AutoHotkey.exe" (assumes it's in PATH).
        timeout: Timeout in seconds for the script execution. Defaults to 30.
                 Set to None for no timeout.
        cwd: The working directory for the script execution.
             Defaults to the script's parent directory if None.
        logger: Optional logger instance. If None, a default util_logger is used.

    Returns:
        A dictionary containing:
        - "success" (bool): True if the script ran without errors (exit code 0), False otherwise.
        - "exit_code" (Optional[int]): The exit code of the script.
        - "stdout" (str): The standard output from the script.
        - "stderr" (str): The standard error from the script.
        - "error_message" (Optional[str]): A high-level error message in case of
                                           issues like script not found, timeout, etc.
        - "feedback" (str): A user-friendly feedback message.
    """
    if logger is None:
        logger = util_logger

    if args is None:
        args = []

    script_path_obj = Path(script_path)
    autohotkey_exe_path_obj = Path(autohotkey_exe_path)

    if not script_path_obj.exists():
        error_msg = f"AHK script not found: {script_path_obj}"
        logger.error(error_msg)
        return {
            "success": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error_message": error_msg,
            "feedback": f"Script file not found: {script_path_obj.name}"
        }

    if cwd is None:
        effective_cwd = script_path_obj.parent
    else:
        effective_cwd = Path(cwd)

    command = [str(autohotkey_exe_path_obj), str(script_path_obj)] + args
    logger.info(f"Executing AHK command: {' '.join(command)} in CWD: {effective_cwd}")

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=timeout,
            cwd=str(effective_cwd),
            check=False
        )

        logger.info(f"AHK script '{script_path_obj.name}' exit code: {result.returncode}")
        if result.stdout:
            logger.debug(f"AHK script stdout: {result.stdout.strip()}")
        if result.stderr:
            logger.warning(f"AHK script stderr: {result.stderr.strip()}")

        success = result.returncode == 0
        feedback_msg = f"AHK script '{script_path_obj.name}' executed successfully." if success \
                       else f"AHK script '{script_path_obj.name}' failed with exit code {result.returncode}."
        
        if not success and result.stderr.strip():
            feedback_msg += f" Error: {result.stderr.strip()}"

        return {
            "success": success,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip() if result.stdout else "",
            "stderr": result.stderr.strip() if result.stderr else "",
            "error_message": None if success else f"Script execution failed with exit code {result.returncode}",
            "feedback": feedback_msg
        }

    except subprocess.TimeoutExpired:
        error_msg = f"AHK script '{script_path_obj.name}' execution timed out after {timeout} seconds."
        logger.error(error_msg)
        return {
            "success": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error_message": error_msg,
            "feedback": "AHK command timed out."
        }
    except FileNotFoundError:
        error_msg = f"AutoHotkey executable not found at '{autohotkey_exe_path_obj}'. Ensure it's installed and in PATH or path is correct."
        logger.error(error_msg)
        return {
            "success": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error_message": error_msg,
            "feedback": "AutoHotkey executable not found."
        }
    except Exception as e:
        error_msg = f"An unexpected error occurred while running AHK script '{script_path_obj.name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error_message": error_msg,
            "feedback": f"AHK script execution failed: {str(e)}"
        }
