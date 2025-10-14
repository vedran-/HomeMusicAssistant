"""
Groq Vision Client

This module handles image analysis using Groq's Llama 4 Maverick vision model.
"""

from groq import Groq
import os
import base64
import io
from typing import Optional, Tuple
from pathlib import Path
from PIL import Image as PILImage

from src.config.settings import AppSettings
from src.utils.logger import app_logger


class GroqVisionClient:
    """Handles vision analysis using Groq's Llama 4 Maverick model."""
    
    def __init__(self, settings: AppSettings):
        """
        Initialize the Groq vision client.
        
        Args:
            settings: Application settings containing API key and config
        """
        self.settings = settings
        
        if not self.settings.groq_api_key:
            app_logger.error("Groq API key is not configured. Vision analysis will fail.")
            raise ValueError("Groq API key is missing. Please set GROQ_API_KEY or add to config.json.")
        
        self.client = Groq(api_key=self.settings.groq_api_key)
        self.model = settings.screenshot_settings.vision_model
        self.timeout = settings.screenshot_settings.vision_timeout
        
        app_logger.info(f"GroqVisionClient initialized with model: {self.model}")
    
    def analyze_image(self, image_path: str, focus_hint: Optional[str] = None) -> Tuple[bool, str]:
        """
        Analyze an image and return description.
        
        Args:
            image_path: Path to image file
            focus_hint: Optional hint about what to focus on
                       (e.g., "Focus on selected text" or 
                        "Describe the product details")
        
        Returns:
            Tuple of (success, description_or_error)
        """
        if not os.path.exists(image_path):
            error_msg = f"Image file not found: {image_path}"
            app_logger.error(error_msg)
            return False, error_msg
        
        app_logger.info(f"Analyzing image: {image_path}")
        
        try:
            # Read and resize image if needed to avoid 413 errors
            with PILImage.open(image_path) as img:
                # Check image size and resize if too large
                max_dimension = 2000  # Max width or height
                width, height = img.size
                
                if width > max_dimension or height > max_dimension:
                    app_logger.info(f"Image is large ({width}x{height}), resizing to fit {max_dimension}px")
                    # Calculate new dimensions maintaining aspect ratio
                    if width > height:
                        new_width = max_dimension
                        new_height = int(height * (max_dimension / width))
                    else:
                        new_height = max_dimension
                        new_width = int(width * (max_dimension / height))
                    
                    img = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
                    app_logger.info(f"Resized to {new_width}x{new_height}")
                
                # Convert to RGB if needed (some formats like RGBA cause issues)
                if img.mode not in ('RGB', 'L'):
                    app_logger.debug(f"Converting image from {img.mode} to RGB")
                    img = img.convert('RGB')
                
                # Save to bytes buffer
                buffer = io.BytesIO()
                img.save(buffer, format='PNG', optimize=True, quality=85)
                image_data = buffer.getvalue()
            
            # Encode to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Determine image format from extension
            image_ext = Path(image_path).suffix.lower().lstrip('.')
            if image_ext == 'jpg':
                image_ext = 'jpeg'
            mime_type = f"image/{image_ext}"
            
            # Construct vision prompt
            if focus_hint:
                vision_prompt = f"{focus_hint}. Then describe what you see in detail, including text, UI elements, and key visuals."
            else:
                vision_prompt = "Describe what you see in detail, including text, UI elements, and key visuals."
            
            app_logger.debug(f"Vision prompt: {vision_prompt}")
            app_logger.debug(f"Image size: {len(base64_image)} bytes (base64)")
            app_logger.debug(f"Using model: {self.model}")
            
            # Call Groq vision API
            app_logger.info(f"Calling Groq vision API...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            },
                            {
                                "type": "text",
                                "text": vision_prompt
                            }
                        ]
                    }
                ],
                temperature=0.5,
                max_tokens=1000,
                timeout=self.timeout
            )
            
            app_logger.debug(f"Raw API response received: {type(response)}")
            
            if not response or not response.choices:
                error_msg = "Vision API returned empty response"
                app_logger.error(f"❌ {error_msg}")
                app_logger.error(f"Response object: {response}")
                return False, error_msg
            
            app_logger.debug(f"Response has {len(response.choices)} choice(s)")
            description = response.choices[0].message.content
            app_logger.debug(f"Extracted description from response")
            
            if not description:
                error_msg = "Vision API returned empty description"
                app_logger.error(error_msg)
                return False, error_msg
            
            app_logger.info(f"✅ Vision analysis successful: {len(description)} characters")
            app_logger.debug(f"Description preview: {description[:200]}...")
            
            return True, description
            
        except Exception as e:
            error_msg = f"Vision analysis failed: {type(e).__name__}: {str(e)}"
            # Use .format() to avoid KeyError with curly braces in error messages
            app_logger.error("❌ " + error_msg, exc_info=True)
            
            # Log additional details for debugging
            if hasattr(e, 'response'):
                app_logger.error(f"API Response object: {e.response}")
            if hasattr(e, 'status_code'):
                app_logger.error(f"HTTP Status Code: {e.status_code}")
            if hasattr(e, 'body'):
                app_logger.error(f"Response Body: {e.body}")
            
            # Try to extract more info from Groq API errors
            try:
                error_details = str(e)
                if 'error' in error_details.lower():
                    app_logger.error(f"Error details: {error_details}")
                
                # Check if it's a rate limit or API quota error
                if 'rate' in error_details.lower() or 'quota' in error_details.lower():
                    app_logger.error("⚠️ This appears to be a rate limit or quota error")
                    return False, "Vision API rate limit exceeded. Please wait a moment and try again."
                
                # Check for timeout
                if 'timeout' in error_details.lower():
                    app_logger.error("⚠️ API request timed out")
                    return False, "Vision API request timed out. The image may be too large."
                
                # Check for authentication errors
                if 'auth' in error_details.lower() or 'api key' in error_details.lower():
                    app_logger.error("⚠️ API authentication error")
                    return False, "Vision API authentication failed. Please check your API key."
                    
            except Exception as parse_error:
                app_logger.error(f"Error parsing exception details: {parse_error}")
            
            return False, error_msg


if __name__ == '__main__':
    # Basic test for GroqVisionClient
    from src.config.settings import load_settings
    import sys
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(current_dir, "..", "..", "config.json")
    
    if not os.path.exists(config_file_path):
        print(f"ERROR: config.json not found at {config_file_path}")
        sys.exit(1)
    
    try:
        settings = load_settings(config_path=config_file_path)
        app_logger.info("Settings loaded for GroqVisionClient test.")
        
        if not settings.groq_api_key:
            app_logger.error("GROQ_API_KEY not set. Skipping vision test.")
            sys.exit(1)
        
        vision_client = GroqVisionClient(settings)
        
        # Test with a sample image (you would need to provide a test image)
        test_image_path = "test_image.png"
        if os.path.exists(test_image_path):
            success, description = vision_client.analyze_image(test_image_path)
            
            if success:
                app_logger.info(f"Test successful! Description: {description}")
            else:
                app_logger.error(f"Test failed: {description}")
        else:
            app_logger.info("No test image found. Create 'test_image.png' to test vision analysis.")
            
    except Exception as e:
        app_logger.error(f"GroqVisionClient test error: {e}", exc_info=True)
        sys.exit(1)

