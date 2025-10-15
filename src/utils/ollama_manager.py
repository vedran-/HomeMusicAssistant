"""Ollama lifecycle manager for automatic start/stop on-demand."""

import subprocess
import threading
import time
import psutil
from typing import Optional
from .logger import app_logger


class OllamaManager:
    """Manages Ollama server lifecycle: auto-start on-demand, auto-stop after idle period."""
    
    def __init__(self, idle_timeout_seconds: int = 180):
        """Initialize OllamaManager.
        
        Args:
            idle_timeout_seconds: Time in seconds to wait before stopping Ollama (default: 180 = 3 minutes)
        """
        self.idle_timeout_seconds = idle_timeout_seconds
        self.last_activity_time: Optional[float] = None
        self.is_running = False
        self.stop_requested = False
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Check if Ollama is available
        if not self.is_ollama_available():
            app_logger.warning("Ollama is not installed or not in PATH. Memory features will be limited.")
            app_logger.warning("Please install Ollama from https://ollama.com/download")
            raise RuntimeError("Ollama is not available. Please install from https://ollama.com/download")
        
        app_logger.info("OllamaManager initialized with {}s idle timeout", idle_timeout_seconds)
    
    def is_ollama_available(self) -> bool:
        """Check if Ollama command is available in the system."""
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output if possible
                version = result.stdout.strip() if result.stdout else result.stderr.strip()
                app_logger.info(f"Ollama found: {version}")
                return True
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            app_logger.debug(f"Ollama availability check failed: {e}")
            return False
    
    def is_ollama_server_running(self) -> bool:
        """Check if Ollama server process is running."""
        try:
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    # Check for ollama process
                    if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                        # Additional check: see if it's the server (serve command)
                        cmdline = proc.info.get('cmdline')
                        if cmdline and any('serve' in str(arg).lower() or 'ollama.exe' in str(arg).lower() for arg in cmdline):
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except Exception as e:
            app_logger.warning(f"Error checking Ollama server status: {e}")
            return False
    
    def start_ollama_server(self) -> bool:
        """Start the Ollama server in the background."""
        try:
            app_logger.info("Starting Ollama server...")
            
            # Start ollama serve in background (non-blocking)
            # On Windows, use CREATE_NEW_PROCESS_GROUP to prevent it from being killed with parent
            if psutil.WINDOWS:
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            
            # Wait a bit for server to start (up to 10 seconds)
            max_wait = 10
            for i in range(max_wait):
                time.sleep(1)
                if self.is_ollama_server_running():
                    app_logger.info("✅ Ollama server started successfully")
                    return True
                app_logger.debug(f"Waiting for Ollama server to start... ({i+1}/{max_wait})")
            
            app_logger.error("Ollama server failed to start within timeout")
            return False
        except Exception as e:
            app_logger.error(f"Failed to start Ollama server: {e}", exc_info=True)
            return False
    
    def stop_ollama_server(self) -> bool:
        """Stop the Ollama server gracefully."""
        try:
            app_logger.info("Stopping Ollama server...")
            
            # Find and terminate Ollama server processes
            stopped = False
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                        cmdline = proc.info.get('cmdline')
                        if cmdline and any('serve' in str(arg).lower() or 'ollama.exe' in str(arg).lower() for arg in cmdline):
                            app_logger.debug(f"Terminating Ollama process (PID: {proc.pid})")
                            proc.terminate()
                            try:
                                proc.wait(timeout=5)
                            except psutil.TimeoutExpired:
                                proc.kill()
                            stopped = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if stopped:
                app_logger.info("✅ Ollama server stopped")
                return True
            else:
                app_logger.debug("No Ollama server process found to stop")
                return False
        except Exception as e:
            app_logger.error(f"Failed to stop Ollama server: {e}", exc_info=True)
            return False
    
    def ensure_running(self):
        """Ensure Ollama server is running. Start it if not running. Update activity timestamp."""
        with self._lock:
            # Update activity time
            self.last_activity_time = time.time()
            
            # Check if already running
            if self.is_ollama_server_running():
                if not self.is_running:
                    app_logger.info("Ollama server is already running")
                    self.is_running = True
                    # Start monitor thread if not running
                    if self._monitor_thread is None or not self._monitor_thread.is_alive():
                        self._start_monitor_thread()
                return
            
            # Start server
            if self.start_ollama_server():
                self.is_running = True
                # Start monitor thread
                if self._monitor_thread is None or not self._monitor_thread.is_alive():
                    self._start_monitor_thread()
            else:
                raise RuntimeError("Failed to start Ollama server")
    
    def mark_activity(self):
        """Mark that activity has occurred (resets idle timer)."""
        with self._lock:
            self.last_activity_time = time.time()
    
    def _start_monitor_thread(self):
        """Start background thread to monitor idle time and auto-stop."""
        self.stop_requested = False
        self._monitor_thread = threading.Thread(target=self._auto_stop_worker, daemon=True)
        self._monitor_thread.start()
        app_logger.debug("Started Ollama idle monitor thread")
    
    def _auto_stop_worker(self):
        """Background worker that monitors idle time and stops Ollama when idle."""
        app_logger.debug("Ollama auto-stop monitor active ({}s idle timeout)", self.idle_timeout_seconds)
        
        while not self.stop_requested:
            time.sleep(10)  # Check every 10 seconds
            
            with self._lock:
                if self.last_activity_time is None:
                    continue
                
                idle_time = time.time() - self.last_activity_time
                
                if idle_time >= self.idle_timeout_seconds:
                    app_logger.info(f"Ollama idle for {int(idle_time)}s, stopping server...")
                    if self.stop_ollama_server():
                        self.is_running = False
                        self.last_activity_time = None
                    break
        
        app_logger.debug("Ollama auto-stop monitor exited")
    
    def stop(self):
        """Stop the Ollama manager and server."""
        app_logger.info("Shutting down OllamaManager...")
        
        with self._lock:
            self.stop_requested = True
            
            if self.is_running:
                self.stop_ollama_server()
                self.is_running = False
        
        # Wait for monitor thread to finish
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)
        
        app_logger.info("OllamaManager shutdown complete")

