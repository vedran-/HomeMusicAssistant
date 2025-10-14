"""
Groq Vision Client

This module handles image analysis using Groq's Llama 4 Maverick vision model.
"""

from groq import Groq
import os
import base64
from typing import Optional, Tuple
from pathlib import Path

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
            # Read and encode the image
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
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
            
            # Call Groq vision API
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
            
            if not response or not response.choices:
                error_msg = "Vision API returned empty response"
                app_logger.error(error_msg)
                return False, error_msg
            
            description = response.choices[0].message.content
            
            if not description:
                error_msg = "Vision API returned empty description"
                app_logger.error(error_msg)
                return False, error_msg
            
            app_logger.info(f"Vision analysis successful: {len(description)} characters")
            app_logger.debug(f"Description: {description[:200]}...")
            
            return True, description
            
        except Exception as e:
            error_msg = f"Vision analysis failed: {type(e).__name__}: {str(e)}"
            app_logger.error(error_msg, exc_info=True)
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

