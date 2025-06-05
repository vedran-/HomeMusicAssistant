import ctypes
import platform
from src.utils.logger import app_logger
from typing import Optional

class WindowsPowerManager:
    """Windows power management utility to control sleep behavior."""
    
    # Windows SetThreadExecutionState constants
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    ES_AWAYMODE_REQUIRED = 0x00000040
    
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.previous_state: Optional[int] = None
        
        if not self.is_windows:
            app_logger.warning("PowerManager: Not running on Windows, power management features disabled")
    
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
    
    def __init__(self):
        self.platform = platform.system()
        self.power_manager = None
        
        if self.platform == "Windows":
            self.power_manager = WindowsPowerManager()
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