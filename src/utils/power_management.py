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
        
        if not self.is_windows:
            app_logger.warning("PowerManager: Not running on Windows, power management features disabled")
            return

        # Optionally run diagnostics on startup
        try:
            if self.power_settings and getattr(self.power_settings, 'diagnose_on_startup', False):
                self._diagnose_and_optionally_override()
        except Exception as e:
            app_logger.warning(f"PowerManager: Startup diagnostics failed: {e}")

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
            return (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
        except Exception as e:
            app_logger.warning(f"PowerManager: Failed to run powercfg /requests: {e}")
            return ""

    def _extract_system_driver_blockers(self, requests_output: str) -> List[str]:
        lines = requests_output.splitlines()
        blockers: List[str] = []
        in_system = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                # Blank line resets section
                in_system = False
                continue
            if stripped.upper().endswith(":"):
                # Section header
                in_system = stripped.upper().startswith("SYSTEM:")
                continue
            if in_system and stripped.lower() != "none.":
                blockers.append(stripped)
        return blockers

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
    
    def get_other_power_requests(self) -> List[str]:
        """
        Get list of power requests from other applications (not our audio driver).
        Returns list of strings describing what's blocking sleep.
        """
        if not self.is_windows:
            return []
        
        try:
            output = self._powercfg_requests()
            if not output:
                return []
            
            # Extract all SYSTEM blockers
            all_blockers = self._extract_system_driver_blockers(output)
            
            # Filter to only blockers that are NOT our audio driver
            # Our audio driver typically shows as something like "Realtek High Definition Audio" or similar
            # We want to exclude common audio driver patterns that are likely ours
            other_blockers = []
            for blocker in all_blockers:
                blocker_lower = blocker.lower()
                # Skip common audio driver patterns (these are likely our recording)
                if any(pattern in blocker_lower for pattern in [
                    'audio', 'sound', 'realtek', 'conexant', 'idt', 'via hd audio'
                ]):
                    # This might be our audio recording driver - skip it
                    app_logger.debug(f"PowerManager: Skipping audio driver blocker: {blocker}")
                    continue
                # Keep other blockers
                other_blockers.append(blocker)
            
            return other_blockers
            
        except Exception as e:
            app_logger.error(f"PowerManager: Error getting power requests: {e}")
            return []
    
    def should_allow_sleep(self) -> Tuple[bool, str]:
        """
        Determine if system should be allowed to sleep based on idle time and other blockers.
        Returns (should_sleep: bool, reason: str)
        """
        if not self.is_windows:
            return (False, "Not Windows")
        
        if not self._is_windows_10():
            return (False, "Not Windows 10")
        
        if not self.power_settings:
            return (False, "No power settings configured")
        
        if not getattr(self.power_settings, 'windows10_managed_sleep_enabled', False):
            return (False, "Windows 10 managed sleep disabled in config")
        
        # Check idle time
        idle_minutes = self.get_system_idle_time()
        threshold = getattr(self.power_settings, 'idle_timeout_minutes', 10)
        
        if idle_minutes < threshold:
            return (False, f"Not idle enough ({idle_minutes:.1f}min < {threshold}min)")
        
        # Check for other blockers
        other_blockers = self.get_other_power_requests()
        
        if other_blockers:
            blockers_str = ", ".join(other_blockers[:3])  # Show first 3
            if len(other_blockers) > 3:
                blockers_str += f" (+{len(other_blockers) - 3} more)"
            return (False, f"Other apps blocking: {blockers_str}")
        
        # All conditions met
        return (True, f"Idle {idle_minutes:.1f}min, no other blockers")
    
    def force_sleep_if_appropriate(self) -> bool:
        """
        Force system to sleep if all conditions are met (Windows 10 only).
        Returns True if sleep was attempted, False otherwise.
        """
        should_sleep, reason = self.should_allow_sleep()
        
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
    
    def should_allow_sleep(self) -> Tuple[bool, str]:
        """Check if system should be allowed to sleep (Windows 10 only)."""
        if self.power_manager and hasattr(self.power_manager, 'should_allow_sleep'):
            return self.power_manager.should_allow_sleep()
        return (False, "Platform not supported")
    
    def force_sleep_if_appropriate(self) -> bool:
        """Force sleep if all conditions are met (Windows 10 only)."""
        if self.power_manager and hasattr(self.power_manager, 'force_sleep_if_appropriate'):
            return self.power_manager.force_sleep_if_appropriate()
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