import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

util_logger = logging.getLogger(__name__)

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
