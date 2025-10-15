import ctypes
import platform
import subprocess
import sys
from typing import Optional, List, Tuple
from src.utils.logger import app_logger

try:
    # Settings are optional at import time to avoid circulars in some contexts
    from src.config.settings import PowerSettings
except Exception:
    PowerSettings = None  # type: ignore

class WindowsPowerManager:
    """Windows power management utility to control sleep behavior."""
    
    # Windows SetThreadExecutionState constants
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    ES_AWAYMODE_REQUIRED = 0x00000040
    
    def __init__(self, power_settings: Optional["PowerSettings"] = None):
        self.is_windows = platform.system() == "Windows"
        self.previous_state: Optional[int] = None
        self.power_settings = power_settings
        self.system_idle_timeout_minutes = -1  # Will be set during startup

        if not self.is_windows:
            app_logger.warning("PowerManager: Not running on Windows, power management features disabled")
            return

        # Windows 10 specific: Ensure admin rights and get system timeout
        if self._is_windows_10():
            self._ensure_admin_rights_and_get_system_timeout()

        # Optionally run diagnostics on startup
        try:
            if self.power_settings and getattr(self.power_settings, 'diagnose_on_startup', False):
                self._diagnose_and_optionally_override()
        except Exception as e:
            app_logger.warning(f"PowerManager: Startup diagnostics failed: {e}")

    def _ensure_admin_rights_and_get_system_timeout(self):
        """Ensure we have admin rights on Windows 10 and get system idle timeout."""
        # Check if we're already elevated (avoids infinite elevation loops)
        if self._is_elevated():
            app_logger.debug("PowerManager: Already running with administrator privileges")
        elif not self._is_elevated():
            app_logger.warning("PowerManager: Windows 10 sleep management requires administrator privileges")
            app_logger.warning("PowerManager: Requesting elevation...")

            # Try to elevate the process
            if not self._elevate_process():
                app_logger.error("PowerManager: Failed to elevate process - Windows 10 sleep management disabled")
                return

        # Get and log system idle timeout
        system_timeout = self.get_system_idle_timeout_minutes()
        if system_timeout >= 0:
            if system_timeout == 0:
                app_logger.info("PowerManager: Windows 10 sleep is disabled in system settings")
            else:
                app_logger.info(f"PowerManager: Windows 10 system idle timeout detected: {system_timeout} minutes")
            self.system_idle_timeout_minutes = system_timeout
        else:
            app_logger.warning(f"PowerManager: Could not determine system idle timeout (got {system_timeout})")
            # Use a reasonable default
            self.system_idle_timeout_minutes = 10

    def _elevate_process(self) -> bool:
        """Try to elevate the current process to administrator using a separate launcher approach."""
        try:
            import sys
            import os

            app_logger.info("PowerManager: Creating admin launcher...")

            # Create a temporary launcher script that runs as admin
            launcher_code = f'''
import sys
import os
import subprocess

# This launcher runs as administrator and starts the main application
print("Admin launcher: Starting main application...")

# Get the directory of this launcher script
launcher_dir = os.path.dirname(os.path.abspath(__file__))
main_script = os.path.join(launcher_dir, "main.py")

# Run the main application
try:
    result = subprocess.run([sys.executable, main_script] + sys.argv[1:])
    print(f"Admin launcher: Main application exited with code: {{result.returncode}}")
    sys.exit(result.returncode)
except Exception as e:
    print(f"Admin launcher: Error running main application: {{e}}")
    sys.exit(1)
'''

            # Write the launcher script to a temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(launcher_code)
                launcher_file = f.name

            app_logger.debug(f"PowerManager: Created launcher script: {launcher_file}")

            # Use ShellExecute to run the launcher as administrator
            import ctypes

            app_logger.info(f"PowerManager: Executing admin launcher: {launcher_file}")

            result = ctypes.windll.shell32.ShellExecuteW(
                None,  # hwnd
                "runas",  # operation (run as admin)
                sys.executable,  # python executable
                f'"{launcher_file}"',  # launcher script
                None,  # directory
                1  # show window
            )

            # Clean up the temporary launcher file
            try:
                os.unlink(launcher_file)
            except:
                pass

            if result > 32:  # ShellExecuteW returns > 32 on success
                app_logger.info("PowerManager: Admin launcher executed successfully")
                app_logger.info("PowerManager: Original process exiting")
                sys.exit(0)
            else:
                error_code = ctypes.windll.kernel32.GetLastError()
                app_logger.error(f"PowerManager: Admin launcher execution failed with error code: {error_code}")
                return False

        except Exception as e:
            app_logger.error(f"PowerManager: Failed to create admin launcher: {e}")
            return False

    # --- Diagnostics and Overrides (Windows 10 specific) ---
    def _is_windows_10(self) -> bool:
        try:
            # platform.release() returns '10' for Windows 10, '11' for Windows 11
            return platform.release() == "10"
        except Exception:
            return False

    def _is_elevated(self) -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _powercfg_requests(self) -> str:
        try:
            completed = subprocess.run(["powercfg", "/requests"], capture_output=True, text=True, shell=False)

            # Check if command failed due to lack of admin rights
            if completed.returncode != 0 and "administrator privileges" in completed.stderr.lower():
                app_logger.warning("PowerManager: powercfg /requests requires administrator privileges.")
                app_logger.warning("PowerManager: Sleep management disabled - cannot detect if other apps are blocking sleep.")
                app_logger.warning("PowerManager: Run as administrator for full sleep management functionality.")
                return ""

            return (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
        except Exception as e:
            app_logger.warning(f"PowerManager: Failed to run powercfg /requests: {e}")
            return ""

    def _extract_section_blockers(self, requests_output: str, section_name: str) -> List[str]:
        """
        Extract blockers from any section of powercfg output.
        Args:
            requests_output: Raw output from powercfg /requests
            section_name: Section header to parse (e.g., "SYSTEM:", "EXECUTION:")
        Returns:
            List of blocker strings from that section
        """
        lines = requests_output.splitlines()
        blockers: List[str] = []
        in_section = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                # Blank line resets section
                in_section = False
                continue
            if stripped.upper().endswith(":"):
                # Section header
                in_section = stripped.upper() == section_name.upper()
                continue
            if in_section and stripped.lower() != "none.":
                blockers.append(stripped)
        return blockers

    def _extract_system_driver_blockers(self, requests_output: str) -> List[str]:
        """Extract SYSTEM section blockers from powercfg output."""
        return self._extract_section_blockers(requests_output, "SYSTEM:")

    def _extract_execution_blockers(self, requests_output: str) -> List[str]:
        """Extract EXECUTION section blockers from powercfg output."""
        return self._extract_section_blockers(requests_output, "EXECUTION:")

    def _diagnose_and_optionally_override(self) -> None:
        if not self.is_windows:
            return
        if self.power_settings and getattr(self.power_settings, 'log_power_requests', False):
            dump = self._powercfg_requests()
            if dump:
                app_logger.info("PowerManager: powercfg /requests\n" + dump)
        if not self._is_windows_10():
            return
        output = self._powercfg_requests()
        if not output:
            return
        blockers = self._extract_system_driver_blockers(output)
        if not blockers:
            return
        app_logger.warning("PowerManager: Windows 10 detected driver-level SYSTEM sleep blockers:")
        for b in blockers:
            app_logger.warning(f"  - {b}")

        auto_override = bool(self.power_settings and getattr(self.power_settings, 'auto_override_windows10_audio_blockers', False))
        if not auto_override:
            # Provide copy-paste suggestions
            for b in blockers:
                safe = b.replace('"', "'")
                app_logger.warning(f"To override: run as Administrator -> powercfg /requestsoverride DRIVER \"{safe}\" SYSTEM")
            return

        if not self._is_elevated():
            for b in blockers:
                safe = b.replace('"', "'")
                app_logger.warning(f"Admin required to auto-override. Copy/paste: powercfg /requestsoverride DRIVER \"{safe}\" SYSTEM")
            return

        # Attempt to auto-override each detected blocker
        for b in blockers:
            safe = b.replace('"', "'")
            try:
                cmd = ["powercfg", "/requestsoverride", "DRIVER", safe, "SYSTEM"]
                completed = subprocess.run(cmd, capture_output=True, text=True, shell=False)
                if completed.returncode == 0:
                    app_logger.info(f"PowerManager: Applied override for DRIVER '{b}' (SYSTEM)")
                else:
                    app_logger.warning(f"PowerManager: Failed to apply override for '{b}': {completed.stdout or completed.stderr}")
            except Exception as e:
                app_logger.warning(f"PowerManager: Error applying override for '{b}': {e}")
    
    def get_system_idle_time(self) -> float:
        """
        Get the system idle time in minutes using GetLastInputInfo API.
        Returns the number of minutes since the last user input (mouse/keyboard).
        """
        if not self.is_windows:
            return 0.0
        
        try:
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]
            
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            
            if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                app_logger.warning("PowerManager: Failed to get last input info")
                return 0.0
            
            # Get current tick count and calculate idle time
            current_ticks = ctypes.windll.kernel32.GetTickCount()
            millis_since_input = current_ticks - lii.dwTime
            
            # Convert to minutes
            minutes_idle = millis_since_input / 1000.0 / 60.0
            
            return minutes_idle
            
        except Exception as e:
            app_logger.error(f"PowerManager: Error getting system idle time: {e}")
            return 0.0
    
    def get_system_idle_timeout_minutes(self) -> int:
        """
        Get the system's configured idle timeout for sleep in minutes.
        Returns 0 if never sleep, or -1 if cannot determine.
        """
        if not self.is_windows:
            return -1

        try:
            # Query current power scheme for STANDBYIDLE (sleep after) setting
            completed = subprocess.run([
                "powercfg", "/q", "SCHEME_CURRENT", "SUB_SLEEP", "STANDBYIDLE"
            ], capture_output=True, text=True, shell=False)

            if completed.returncode != 0:
                app_logger.warning("PowerManager: Failed to query system sleep timeout")
                return -1

            # Parse output to find Current AC Power Setting Index
            output = completed.stdout
            for line in output.splitlines():
                if "Current AC Power Setting Index:" in line:
                    hex_value = line.split(":")[1].strip()
                    seconds = int(hex_value, 16)
                    minutes = seconds // 60
                    app_logger.debug(f"PowerManager: System sleep timeout is {minutes} minutes")
                    return minutes

            app_logger.warning("PowerManager: Could not parse system sleep timeout")
            return -1

        except Exception as e:
            app_logger.error(f"PowerManager: Error getting system idle timeout: {e}")
            return -1

    def get_other_power_requests(self) -> List[str]:
        """
        Get list of power requests from other applications (not our audio driver).
        Returns list of strings describing what's blocking sleep.

        Analyzes all power request categories that can block system sleep:
        - SYSTEM: System-level requests (drivers) - can block sleep
        - EXECUTION: Application-level requests (processes) - can block sleep
        - AWAYMODE: Away mode requests - can block sleep
        - PERFBOOST: Performance boost requests - can block sleep
        - DISPLAY: Display requests - usually don't block system sleep
        - ACTIVELOCKSCREEN: Lock screen requests - usually don't block system sleep
        """
        if not self.is_windows:
            return []

        try:
            output = self._powercfg_requests()
            if not output:
                # Return empty list if we can't get power requests (no admin rights)
                # This means we can't detect other blockers, so we should be conservative
                return []

            # Parse all categories that can block system sleep
            system_blockers = self._extract_section_blockers(output, "SYSTEM:")
            execution_blockers = self._extract_section_blockers(output, "EXECUTION:")
            awaymode_blockers = self._extract_section_blockers(output, "AWAYMODE:")
            perfboost_blockers = self._extract_section_blockers(output, "PERFBOOST:")

            # DISPLAY and ACTIVELOCKSCREEN typically don't block system sleep
            # (they only prevent display sleep, not system sleep)
            display_blockers = self._extract_section_blockers(output, "DISPLAY:")
            lockscreen_blockers = self._extract_section_blockers(output, "ACTIVELOCKSCREEN:")

            app_logger.debug(f"PowerManager: SYSTEM={len(system_blockers)}, EXECUTION={len(execution_blockers)}, AWAYMODE={len(awaymode_blockers)}, PERFBOOST={len(perfboost_blockers)}")
            app_logger.debug(f"PowerManager: DISPLAY={len(display_blockers)}, ACTIVELOCKSCREEN={len(lockscreen_blockers)} (ignored for sleep blocking)")

            # Combine only sleep-blocking categories
            all_blockers = system_blockers + execution_blockers + awaymode_blockers + perfboost_blockers

            # Filter to only blockers that are NOT our audio recording
            other_blockers = []
            for blocker in all_blockers:
                blocker_lower = blocker.lower()

                # Skip our audio recording drivers (SYSTEM level)
                if blocker in system_blockers and any(pattern in blocker_lower for pattern in [
                    'audio', 'sound', 'realtek', 'conexant', 'idt', 'via hd audio',
                    'high definition audio', 'hdaudio'
                ]):
                    app_logger.debug(f"PowerManager: Skipping our audio driver: {blocker}")
                    continue

                # Skip our own process if it appears in EXECUTION (unlikely but possible)
                if 'homemusicassistant' in blocker_lower or 'python' in blocker_lower:
                    app_logger.debug(f"PowerManager: Skipping our process: {blocker}")
                    continue

                # Skip AnyDesk or remote desktop software that might be related to our testing
                if 'anydesk' in blocker_lower:
                    app_logger.debug(f"PowerManager: Skipping remote desktop software: {blocker}")
                    continue

                # Keep other blockers (music players, video players, etc.)
                other_blockers.append(blocker)

            app_logger.debug(f"PowerManager: Final sleep blockers: {other_blockers}")
            return other_blockers

        except Exception as e:
            app_logger.error(f"PowerManager: Error getting power requests: {e}")
            return []
    
    def should_allow_sleep(self, conversation_active: bool = False) -> Tuple[bool, str]:
        """
        Determine if system should be allowed to sleep based on idle time and other blockers.
        Returns (should_sleep: bool, reason: str)

        Args:
            conversation_active: True if user is currently speaking to assistant
        """
        if not self.is_windows:
            return (False, "Not Windows")

        if not self._is_windows_10():
            return (False, "Not Windows 10")

        if not self.power_settings:
            return (False, "No power settings configured")

        # Check if sleep is disabled in Windows settings
        if self.system_idle_timeout_minutes == 0:
            return (False, "Sleep disabled in Windows power settings")

        # Check idle time (but account for conversation activity)
        idle_minutes = self.get_system_idle_time()

        # Use system idle timeout if available, otherwise use default
        if self.system_idle_timeout_minutes > 0:
            threshold = self.system_idle_timeout_minutes
        else:
            threshold = 10  # fallback default

        # If user is actively conversing with assistant, extend idle threshold
        if conversation_active:
            # Add 5 minutes to idle threshold during conversation
            conversation_threshold = threshold + 5
            if idle_minutes < conversation_threshold:
                return (False, f"Conversation active - idle {idle_minutes:.1f}min < {conversation_threshold}min threshold")
        else:
            if idle_minutes < threshold:
                return (False, f"Not idle enough ({idle_minutes:.1f}min < {threshold}min system threshold)")

        # Check for other blockers
        other_blockers = self.get_other_power_requests()

        # Handle case where we can't get power requests (no admin rights)
        if not other_blockers and not self._is_elevated():
            # We can't detect other blockers, so be conservative and don't force sleep
            # This prevents accidentally sleeping while music is playing
            app_logger.debug("PowerManager: Cannot detect power requests without admin rights - not forcing sleep")
            return (False, "Cannot detect power requests (no admin rights) - being conservative")

        if other_blockers:
            # Log what types of blockers were found for debugging
            system_blockers = [b for b in other_blockers if any(pattern in b.lower() for pattern in ['driver', 'device'])]
            execution_blockers = [b for b in other_blockers if any(pattern in b.lower() for pattern in ['exe', 'process'])]

            if system_blockers:
                app_logger.debug(f"PowerManager: SYSTEM blockers preventing sleep: {system_blockers}")
            if execution_blockers:
                app_logger.debug(f"PowerManager: EXECUTION blockers preventing sleep: {execution_blockers}")

            blockers_str = ", ".join(other_blockers[:3])  # Show first 3
            if len(other_blockers) > 3:
                blockers_str += f" (+{len(other_blockers) - 3} more)"
            return (False, f"Other apps blocking: {blockers_str}")

        # All conditions met
        if conversation_active:
            return (True, f"Conversation ended, idle {idle_minutes:.1f}min, no other blockers")
        else:
            return (True, f"Idle {idle_minutes:.1f}min, no other blockers")
    
    def force_sleep_if_appropriate(self, conversation_active: bool = False) -> bool:
        """
        Force system to sleep if all conditions are met (Windows 10 only).
        Returns True if sleep was attempted, False otherwise.

        Args:
            conversation_active: True if user is currently interacting with assistant
        """
        should_sleep, reason = self.should_allow_sleep(conversation_active)

        app_logger.debug(f"PowerManager: Sleep check - {reason}")

        if not should_sleep:
            return False

        # All conditions met - attempt to force sleep
        try:
            app_logger.info(f"PowerManager: Forcing system sleep ({reason})")

            # SetSuspendState(hibernate, forceCritical, disableWakeEvent)
            # hibernate=False: sleep mode (not hibernate)
            # forceCritical=False: apps can still prevent sleep if needed
            # disableWakeEvent=False: allow wake events
            result = ctypes.windll.PowrProf.SetSuspendState(False, False, False)

            if result == 0:
                # SetSuspendState returns 0 on success
                # If we reach here, sleep was initiated successfully
                # (though we likely won't see this log as system will be sleeping)
                app_logger.info("PowerManager: Sleep initiated successfully")
                return True
            else:
                app_logger.warning(f"PowerManager: SetSuspendState returned {result}")
                return False

        except Exception as e:
            app_logger.error(f"PowerManager: Error forcing sleep: {e}")
            return False
    
    def allow_system_sleep(self) -> bool:
        """
        Allow the system to sleep normally while keeping the application running.
        This prevents the audio stream from blocking system sleep.
        """
        if not self.is_windows:
            return False
            
        try:
            # Set execution state to allow sleep but keep the thread running
            # ES_CONTINUOUS keeps our thread active, but doesn't prevent system sleep
            result = ctypes.windll.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)
            
            if result != 0:
                app_logger.info("PowerManager: System sleep enabled (audio stream won't prevent sleep)")
                return True
            else:
                app_logger.warning("PowerManager: Failed to set execution state for sleep allowance")
                return False
                
        except Exception as e:
            app_logger.error(f"PowerManager: Error setting execution state: {e}")
            return False
    
    def prevent_system_sleep(self) -> bool:
        """
        Prevent the system from sleeping (use sparingly, only when necessary).
        """
        if not self.is_windows:
            return False
            
        try:
            # Prevent system sleep but allow display to turn off
            result = ctypes.windll.kernel32.SetThreadExecutionState(
                self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED
            )
            
            if result != 0:
                app_logger.info("PowerManager: System sleep prevented")
                return True
            else:
                app_logger.warning("PowerManager: Failed to prevent system sleep")
                return False
                
        except Exception as e:
            app_logger.error(f"PowerManager: Error preventing sleep: {e}")
            return False
    
    def reset_power_state(self) -> bool:
        """
        Reset to default Windows power management behavior.
        """
        if not self.is_windows:
            return False
            
        try:
            # Reset to default behavior
            result = ctypes.windll.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)
            
            if result != 0:
                app_logger.info("PowerManager: Power state reset to default")
                return True
            else:
                app_logger.warning("PowerManager: Failed to reset power state")
                return False
                
        except Exception as e:
            app_logger.error(f"PowerManager: Error resetting power state: {e}")
            return False


class CrossPlatformPowerManager:
    """Cross-platform power management utility."""
    
    def __init__(self, settings: Optional[object] = None):
        self.platform = platform.system()
        self.power_manager = None
        self._power_settings: Optional[PowerSettings] = None
        try:
            if settings is not None and hasattr(settings, 'power'):
                self._power_settings = getattr(settings, 'power')  # type: ignore
        except Exception:
            self._power_settings = None
        
        if self.platform == "Windows":
            self.power_manager = WindowsPowerManager(power_settings=self._power_settings)
        elif self.platform == "Darwin":  # macOS
            self.power_manager = MacOSPowerManager()
        elif self.platform == "Linux":
            self.power_manager = LinuxPowerManager()
        else:
            app_logger.warning(f"PowerManager: Unsupported platform '{self.platform}', power management disabled")
    
    def allow_system_sleep(self) -> bool:
        """Allow the system to sleep normally while keeping the application running."""
        if self.power_manager:
            return self.power_manager.allow_system_sleep()
        return False
    
    def prevent_system_sleep(self) -> bool:
        """Prevent the system from sleeping."""
        if self.power_manager:
            return self.power_manager.prevent_system_sleep()
        return False
    
    def reset_power_state(self) -> bool:
        """Reset to default power management behavior."""
        if self.power_manager:
            return self.power_manager.reset_power_state()
        return False
    
    def get_system_idle_time(self) -> float:
        """Get system idle time in minutes (Windows only)."""
        if self.power_manager and hasattr(self.power_manager, 'get_system_idle_time'):
            return self.power_manager.get_system_idle_time()
        return 0.0
    
    def should_allow_sleep(self, conversation_active: bool = False) -> Tuple[bool, str]:
        """Check if system should be allowed to sleep (Windows 10 only)."""
        if self.power_manager and hasattr(self.power_manager, 'should_allow_sleep'):
            return self.power_manager.should_allow_sleep(conversation_active)
        return (False, "Platform not supported")

    def force_sleep_if_appropriate(self, conversation_active: bool = False) -> bool:
        """Force sleep if all conditions are met (Windows 10 only)."""
        if self.power_manager and hasattr(self.power_manager, 'force_sleep_if_appropriate'):
            return self.power_manager.force_sleep_if_appropriate(conversation_active)
        return False

    def get_system_idle_timeout_minutes(self) -> int:
        """Get the system's configured idle timeout for sleep in minutes (Windows only)."""
        if self.power_manager and hasattr(self.power_manager, 'get_system_idle_timeout_minutes'):
            return self.power_manager.get_system_idle_timeout_minutes()
        return -1

    def _is_windows_10(self) -> bool:
        """Check if running on Windows 10 (for Windows 10 sleep management)."""
        if self.power_manager and hasattr(self.power_manager, '_is_windows_10'):
            return self.power_manager._is_windows_10()
        return False


class MacOSPowerManager:
    """macOS power management using IOKit framework."""
    
    def __init__(self):
        self.assertion_id = None
        try:
            # Try to import required macOS frameworks
            import objc
            from Foundation import NSBundle
            
            # Load IOKit framework
            IOKit = NSBundle.bundleWithIdentifier_('com.apple.framework.IOKit')
            if IOKit is None:
                app_logger.warning("PowerManager: IOKit framework not available on macOS")
                self.available = False
            else:
                self.available = True
                app_logger.info("PowerManager: macOS IOKit power management initialized")
        except ImportError:
            app_logger.warning("PowerManager: PyObjC not available, macOS power management disabled")
            self.available = False
    
    def allow_system_sleep(self) -> bool:
        """Allow system sleep on macOS by releasing any power assertions."""
        if not self.available:
            return False
            
        try:
            if self.assertion_id is not None:
                # Release existing assertion
                self._release_assertion()
            app_logger.info("PowerManager: macOS system sleep enabled")
            return True
        except Exception as e:
            app_logger.error(f"PowerManager: Error allowing sleep on macOS: {e}")
            return False
    
    def prevent_system_sleep(self) -> bool:
        """Prevent system sleep on macOS using IOPMAssertionCreateWithName."""
        if not self.available:
            return False
            
        try:
            # This would require proper IOKit bindings
            # For now, just log that it's not implemented
            app_logger.warning("PowerManager: macOS sleep prevention not fully implemented")
            return False
        except Exception as e:
            app_logger.error(f"PowerManager: Error preventing sleep on macOS: {e}")
            return False
    
    def reset_power_state(self) -> bool:
        """Reset power state on macOS."""
        return self.allow_system_sleep()
    
    def _release_assertion(self):
        """Release power assertion on macOS."""
        # Implementation would go here with proper IOKit bindings
        pass


class LinuxPowerManager:
    """Linux power management using systemd-inhibit or D-Bus."""
    
    def __init__(self):
        self.inhibit_handle = None
        self.available = self._check_availability()
        
        if self.available:
            app_logger.info("PowerManager: Linux power management initialized")
        else:
            app_logger.warning("PowerManager: Linux power management not available")
    
    def _check_availability(self) -> bool:
        """Check if systemd-inhibit or D-Bus is available."""
        try:
            import subprocess
            result = subprocess.run(['which', 'systemd-inhibit'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False
    
    def allow_system_sleep(self) -> bool:
        """Allow system sleep on Linux."""
        if not self.available:
            return False
            
        try:
            if self.inhibit_handle is not None:
                # Kill the inhibit process
                self.inhibit_handle.terminate()
                self.inhibit_handle = None
            app_logger.info("PowerManager: Linux system sleep enabled")
            return True
        except Exception as e:
            app_logger.error(f"PowerManager: Error allowing sleep on Linux: {e}")
            return False
    
    def prevent_system_sleep(self) -> bool:
        """Prevent system sleep on Linux using systemd-inhibit."""
        if not self.available:
            return False
            
        try:
            import subprocess
            # Start systemd-inhibit in background
            self.inhibit_handle = subprocess.Popen([
                'systemd-inhibit', 
                '--what=sleep', 
                '--who=HomeMusicAssistant',
                '--why=Voice control active',
                'sleep', 'infinity'
            ])
            app_logger.info("PowerManager: Linux system sleep prevented")
            return True
        except Exception as e:
            app_logger.error(f"PowerManager: Error preventing sleep on Linux: {e}")
            return False
    
    def reset_power_state(self) -> bool:
        """Reset power state on Linux."""
        return self.allow_system_sleep() 