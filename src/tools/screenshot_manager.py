"""
Screenshot Manager

This module handles screenshot capture and vision-based analysis with multi-step LLM workflow.
This demonstrates the reusable multi-step agentic pattern.
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

import pyautogui
from PIL import Image

from src.config.settings import AppSettings
from src.utils.logger import app_logger
from src.utils.audio_effects import play_wake_word_accepted_sound

# Platform-specific imports for active window capture
if sys.platform == 'win32':
    try:
        import win32gui
        import win32ui
        import win32con
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
        app_logger.warning("win32gui not available - active window capture may not work optimally on Windows")
else:
    WIN32_AVAILABLE = False


class ScreenshotManager:
    """Manages screenshot capture and vision-based analysis with multi-step workflow."""
    
    def __init__(self, settings: AppSettings, vision_client, llm_client=None):
        """
        Initialize the screenshot manager.
        
        Args:
            settings: Application settings
            vision_client: GroqVisionClient instance for image analysis
            llm_client: LiteLLMClient instance for multi-step processing (can be None, injected later)
        """
        self.settings = settings
        self.vision_client = vision_client
        self.llm_client = llm_client  # Can be None initially, injected later
        self.screenshots_dir = Path(settings.screenshot_settings.data_dir)
        
        # Ensure screenshots directory exists
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        app_logger.info(f"ScreenshotManager initialized. Screenshots dir: {self.screenshots_dir}")
    
    def _sanitize_filename(self, text: str, max_length: int = 50) -> str:
        """
        Sanitize text for use in filename.
        
        Args:
            text: Text to sanitize
            max_length: Maximum length of sanitized text
            
        Returns:
            Sanitized text safe for filenames
        """
        # Take first max_length characters
        text = text[:max_length]
        
        # Replace spaces with underscores
        text = text.replace(' ', '_')
        
        # Keep only alphanumeric, underscores, and hyphens
        text = re.sub(r'[^a-zA-Z0-9_-]', '', text)
        
        # Remove multiple consecutive underscores
        text = re.sub(r'_+', '_', text)
        
        # Strip leading/trailing underscores
        text = text.strip('_')
        
        # If empty after sanitization, use default
        if not text:
            text = "screenshot"
        
        return text
    
    def _capture_all_monitors(self) -> Tuple[bool, str, Optional[Path]]:
        """
        Capture screenshot of all monitors.
        
        Returns:
            Tuple of (success, message, image_path)
        """
        try:
            app_logger.info("Capturing screenshot of all monitors...")
            
            # Capture entire screen (all monitors)
            screenshot = pyautogui.screenshot()
            
            # Generate temporary filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_filename = f"{timestamp}_temp.png"
            temp_path = self.screenshots_dir / temp_filename
            
            # Save screenshot
            screenshot.save(str(temp_path))
            
            app_logger.info(f"All monitors screenshot captured: {temp_path}")
            return True, "Screenshot captured successfully", temp_path
            
        except Exception as e:
            error_msg = f"Failed to capture all monitors screenshot: {str(e)}"
            app_logger.error(error_msg, exc_info=True)
            return False, error_msg, None
    
    def _capture_active_window_windows(self) -> Tuple[bool, str, Optional[Path]]:
        """
        Capture screenshot of active window on Windows.
        Uses pyautogui primarily (works better with hardware-accelerated apps),
        with PrintWindow API as fallback.
        
        Returns:
            Tuple of (success, message, image_path)
        """
        try:
            app_logger.info("Capturing active window screenshot (Windows)...")
            
            # Method 1: Try pyautogui first (works best with modern apps)
            try:
                import time
                time.sleep(0.1)  # Small delay to ensure window is ready
                
                active_window = pyautogui.getActiveWindow()
                if active_window:
                    app_logger.info(f"Capturing window: {active_window.title} at ({active_window.left}, {active_window.top}, {active_window.width}, {active_window.height})")
                    
                    screenshot = pyautogui.screenshot(region=(
                        active_window.left,
                        active_window.top,
                        active_window.width,
                        active_window.height
                    ))
                    
                    # Generate temporary filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    temp_filename = f"{timestamp}_temp.png"
                    temp_path = self.screenshots_dir / temp_filename
                    
                    # Save screenshot
                    screenshot.save(str(temp_path))
                    
                    app_logger.info(f"Active window screenshot captured via pyautogui: {temp_path}")
                    return True, "Active window screenshot captured successfully", temp_path
                else:
                    app_logger.warning("pyautogui.getActiveWindow() returned None")
            except Exception as e:
                app_logger.warning(f"pyautogui active window capture failed: {e}")
            
            # Method 2: Try PrintWindow API (better than BitBlt for hardware-accelerated windows)
            if WIN32_AVAILABLE:
                try:
                    app_logger.info("Trying PrintWindow API method...")
                    
                    hwnd = win32gui.GetForegroundWindow()
                    if not hwnd:
                        raise Exception("No foreground window")
                    
                    # Get window rectangle
                    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                    width = right - left
                    height = bottom - top
                    
                    if width <= 0 or height <= 0:
                        raise Exception("Invalid window dimensions")
                    
                    # Get window device context
                    hwndDC = win32gui.GetWindowDC(hwnd)
                    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
                    saveDC = mfcDC.CreateCompatibleDC()
                    
                    # Create bitmap
                    saveBitMap = win32ui.CreateBitmap()
                    saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
                    saveDC.SelectObject(saveBitMap)
                    
                    # Use PrintWindow instead of BitBlt - works better with hardware acceleration
                    # PW_CLIENTONLY = 1, PW_RENDERFULLCONTENT = 2
                    result = win32gui.SendMessage(hwnd, 0x0317, saveDC.GetSafeHdc(), 2)  # WM_PRINT with PW_RENDERFULLCONTENT
                    
                    if result == 0:
                        # PrintWindow failed, try BitBlt with CAPTUREBLT flag
                        app_logger.warning("PrintWindow failed, trying BitBlt with CAPTUREBLT")
                        saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY | 0x40000000)  # SRCCOPY | CAPTUREBLT
                    
                    # Convert to PIL Image
                    bmpinfo = saveBitMap.GetInfo()
                    bmpstr = saveBitMap.GetBitmapBits(True)
                    screenshot = Image.frombuffer(
                        'RGB',
                        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                        bmpstr, 'raw', 'BGRX', 0, 1
                    )
                    
                    # Clean up
                    win32gui.DeleteObject(saveBitMap.GetHandle())
                    saveDC.DeleteDC()
                    mfcDC.DeleteDC()
                    win32gui.ReleaseDC(hwnd, hwndDC)
                    
                    # Generate temporary filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    temp_filename = f"{timestamp}_temp.png"
                    temp_path = self.screenshots_dir / temp_filename
                    
                    # Save screenshot
                    screenshot.save(str(temp_path))
                    
                    app_logger.info(f"Active window screenshot captured via PrintWindow: {temp_path}")
                    return True, "Active window screenshot captured successfully", temp_path
                    
                except Exception as e:
                    app_logger.warning(f"PrintWindow/BitBlt capture failed: {e}")
            
            # Method 3: Fallback to all monitors
            app_logger.warning("All active window capture methods failed, falling back to all monitors")
            return self._capture_all_monitors()
            
        except Exception as e:
            error_msg = f"Failed to capture active window: {str(e)}"
            app_logger.error(error_msg, exc_info=True)
            # Fallback to all monitors
            app_logger.info("Falling back to all monitors capture")
            return self._capture_all_monitors()
    
    def _capture_active_window_generic(self) -> Tuple[bool, str, Optional[Path]]:
        """
        Capture screenshot of active window using pyautogui (cross-platform fallback).
        
        Returns:
            Tuple of (success, message, image_path)
        """
        try:
            app_logger.info("Capturing active window screenshot (generic)...")
            
            # On non-Windows platforms, use pyautogui with getActiveWindow
            try:
                active_window = pyautogui.getActiveWindow()
                if active_window:
                    screenshot = pyautogui.screenshot(region=(
                        active_window.left,
                        active_window.top,
                        active_window.width,
                        active_window.height
                    ))
                else:
                    # No active window, capture all
                    app_logger.warning("No active window detected, capturing all monitors")
                    return self._capture_all_monitors()
            except Exception as e:
                # getActiveWindow may not be available or may fail
                app_logger.warning(f"pyautogui.getActiveWindow() failed: {e}, falling back to all monitors")
                return self._capture_all_monitors()
            
            # Generate temporary filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_filename = f"{timestamp}_temp.png"
            temp_path = self.screenshots_dir / temp_filename
            
            # Save screenshot
            screenshot.save(str(temp_path))
            
            app_logger.info(f"Active window screenshot captured: {temp_path}")
            return True, "Active window screenshot captured successfully", temp_path
            
        except Exception as e:
            error_msg = f"Failed to capture active window: {str(e)}"
            app_logger.error(error_msg, exc_info=True)
            return False, error_msg, None
    
    def capture_screenshot(self, capture_mode: str = "active_window") -> Tuple[bool, str, Optional[Path]]:
        """
        Capture screenshot based on mode.
        
        Args:
            capture_mode: "active_window" (default) or "all_monitors"
        
        Returns:
            Tuple of (success, message, image_path)
        """
        if capture_mode == "all_monitors":
            return self._capture_all_monitors()
        elif capture_mode == "active_window":
            # Use platform-specific active window capture
            if sys.platform == 'win32':
                return self._capture_active_window_windows()
            else:
                return self._capture_active_window_generic()
        else:
            error_msg = f"Invalid capture mode: {capture_mode}"
            app_logger.error(error_msg)
            return False, error_msg, None
    
    def analyze_and_answer(self, user_question: str, 
                          capture_mode: str = "active_window",
                          focus_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Multi-step agentic workflow:
        1. Play processing sound
        2. Capture screenshot
        3. Send to vision API with focus hint
        4. Save screenshot with description
        5. Call LLM to answer question based on description
        6. Return answer
        
        This demonstrates the reusable multi-step pattern!
        
        Args:
            user_question: The user's question about the screen
            capture_mode: "active_window" or "all_monitors"
            focus_hint: Optional hint about what to focus on
            
        Returns:
            Dict with success, feedback, output, and optional error
        """
        app_logger.info(f"Starting screen analysis workflow. Question: '{user_question}', Mode: {capture_mode}")
        
        # Step 1: Play processing sound (reuse wake word sound as processing indicator)
        try:
            play_wake_word_accepted_sound()
        except Exception as e:
            app_logger.warning(f"Failed to play processing sound: {e}")
        
        screenshot_path = None
        description = ""
        
        try:
            # Step 2: Capture screenshot
            success, message, screenshot_path = self.capture_screenshot(capture_mode)
            
            if not success:
                return {
                    "success": False,
                    "error": message,
                    "feedback": "I couldn't capture the screenshot"
                }
            
            # Step 3: Send to vision API with focus hint
            app_logger.info("Sending screenshot to vision API...")
            vision_success, description = self.vision_client.analyze_image(
                str(screenshot_path),
                focus_hint=focus_hint
            )
            
            if not vision_success:
                # Vision failed, but we still have the screenshot
                error_msg = f"Vision analysis failed: {description}"
                app_logger.error(error_msg)
                
                # Step 4a: Save screenshot with error description
                if self.settings.screenshot_settings.save_screenshots and screenshot_path:
                    final_path = self._save_screenshot_with_description(
                        screenshot_path,
                        "vision_analysis_failed"
                    )
                    app_logger.info(f"Screenshot saved despite vision failure: {final_path}")
                
                return {
                    "success": False,
                    "error": error_msg,
                    "feedback": "I couldn't analyze the screenshot. The vision service may be unavailable."
                }
            
            app_logger.info(f"Vision analysis successful: {len(description)} characters")
            
            # Step 4: Save screenshot with description
            if self.settings.screenshot_settings.save_screenshots and screenshot_path:
                final_path = self._save_screenshot_with_description(screenshot_path, description)
                app_logger.info(f"Screenshot saved: {final_path}")
            
            # Step 5: Call LLM to answer question based on description
            if not self.llm_client:
                # No LLM client available, just return the description
                app_logger.warning("No LLM client available for multi-step processing. Returning vision description.")
                return {
                    "success": True,
                    "output": description,
                    "feedback": description[:500]  # Truncate for TTS
                }
            
            app_logger.info("Calling LLM to answer user question based on screen description...")
            
            llm_messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that answers questions about screen content based on vision AI descriptions."
                },
                {
                    "role": "user",
                    "content": f"""Here's what I can see on the screen:

{description}

User's question: {user_question}

Please answer their question based on what's visible on the screen. Be concise and helpful."""
                }
            ]
            
            answer = self.llm_client.get_completion(llm_messages, temperature=0.3, max_tokens=500)
            
            if not answer:
                # LLM failed, fallback to description
                app_logger.warning("LLM completion failed. Falling back to vision description.")
                return {
                    "success": True,
                    "output": description,
                    "feedback": description[:500]
                }
            
            # Step 6: Return answer
            app_logger.info(f"Multi-step workflow complete. Answer: {len(answer)} characters")
            
            return {
                "success": True,
                "output": f"Vision Description: {description}\n\nAnswer: {answer}",
                "feedback": answer
            }
            
        except Exception as e:
            error_msg = f"Screen analysis workflow failed: {str(e)}"
            app_logger.error(error_msg, exc_info=True)
            
            # Try to save screenshot even on error
            if screenshot_path and self.settings.screenshot_settings.save_screenshots:
                try:
                    final_path = self._save_screenshot_with_description(
                        screenshot_path,
                        f"error_{str(e)[:30]}"
                    )
                    app_logger.info(f"Screenshot saved despite error: {final_path}")
                except Exception as save_error:
                    app_logger.error(f"Failed to save screenshot: {save_error}")
            
            return {
                "success": False,
                "error": error_msg,
                "feedback": "Sorry, I encountered an error while analyzing the screen"
            }
    
    def _save_screenshot_with_description(self, temp_path: Path, description: str) -> Path:
        """
        Save screenshot with descriptive filename.
        
        Args:
            temp_path: Temporary screenshot path
            description: Description from vision AI
            
        Returns:
            Final screenshot path
        """
        # Generate filename: {timestamp}_{sanitized_description}.png
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        description_snippet = self._sanitize_filename(description, max_length=50)
        final_filename = f"{timestamp}_{description_snippet}.png"
        final_path = self.screenshots_dir / final_filename
        
        # Rename temp file to final name
        if temp_path.exists():
            temp_path.rename(final_path)
            app_logger.debug(f"Renamed {temp_path} to {final_path}")
        
        return final_path


if __name__ == '__main__':
    # Basic test for ScreenshotManager
    from src.config.settings import load_settings
    from src.vision.groq_vision_client import GroqVisionClient
    from src.llm.client import LiteLLMClient
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(current_dir, "..", "..", "config.json")
    
    if not os.path.exists(config_file_path):
        print(f"ERROR: config.json not found at {config_file_path}")
        sys.exit(1)
    
    try:
        settings = load_settings(config_path=config_file_path)
        app_logger.info("Settings loaded for ScreenshotManager test.")
        
        # Initialize components
        vision_client = GroqVisionClient(settings)
        llm_client = LiteLLMClient(settings)
        screenshot_manager = ScreenshotManager(settings, vision_client, llm_client)
        
        # Test screenshot capture
        app_logger.info("Testing screenshot capture...")
        success, message, path = screenshot_manager.capture_screenshot("active_window")
        
        if success:
            app_logger.info(f"Screenshot captured successfully: {path}")
            
            # Test full workflow
            app_logger.info("Testing full analyze_and_answer workflow...")
            result = screenshot_manager.analyze_and_answer(
                user_question="What's on the screen?",
                capture_mode="active_window"
            )
            
            if result["success"]:
                app_logger.info(f"Workflow successful! Feedback: {result['feedback'][:200]}...")
            else:
                app_logger.error(f"Workflow failed: {result.get('error')}")
        else:
            app_logger.error(f"Screenshot capture failed: {message}")
            
    except Exception as e:
        app_logger.error(f"ScreenshotManager test error: {e}", exc_info=True)
        sys.exit(1)

