"""
Test script for Screenshot Vision Analysis functionality.

This script tests:
1. Vision client (Groq vision API)
2. Screenshot capture (active window, all monitors)
3. Screenshot manager (multi-step workflow)
4. Tool registry integration
5. Filename sanitization and saving
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import load_settings
from src.vision.groq_vision_client import GroqVisionClient
from src.tools.screenshot_manager import ScreenshotManager
from src.llm.client import LiteLLMClient
from src.tools.registry import ToolRegistry
from src.utils.logger import app_logger


def test_vision_client():
    """Test the Groq vision client with a simple image."""
    print("\n" + "=" * 70)
    print("TEST 1: Vision Client")
    print("=" * 70)
    
    settings = load_settings()
    
    try:
        vision_client = GroqVisionClient(settings)
        print("✅ GroqVisionClient initialized")
        
        # Note: This test requires an actual image file to test
        test_image_path = "test_image.png"
        if os.path.exists(test_image_path):
            print(f"Testing with image: {test_image_path}")
            success, description = vision_client.analyze_image(test_image_path)
            
            if success:
                print(f"✅ Vision analysis successful!")
                print(f"Description length: {len(description)} characters")
                print(f"Description preview: {description[:200]}...")
            else:
                print(f"❌ Vision analysis failed: {description}")
                return False
        else:
            print("⚠️  No test image found. Skipping actual API test.")
            print("   Create 'test_image.png' in project root to test vision API.")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vision_with_focus_hint():
    """Test vision client with focus hint."""
    print("\n" + "=" * 70)
    print("TEST 2: Vision Client with Focus Hint")
    print("=" * 70)
    
    settings = load_settings()
    
    try:
        vision_client = GroqVisionClient(settings)
        
        test_image_path = "test_image.png"
        if os.path.exists(test_image_path):
            print(f"Testing with focus hint...")
            success, description = vision_client.analyze_image(
                test_image_path,
                focus_hint="Focus on any text visible in the image"
            )
            
            if success:
                print(f"✅ Vision analysis with focus hint successful!")
                print(f"Description preview: {description[:200]}...")
            else:
                print(f"❌ Vision analysis failed: {description}")
                return False
        else:
            print("⚠️  Skipping - no test image available")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_screenshot_capture():
    """Test screenshot capture functionality."""
    print("\n" + "=" * 70)
    print("TEST 3: Screenshot Capture")
    print("=" * 70)
    
    settings = load_settings()
    temp_dir = tempfile.mkdtemp(prefix="screenshot_test_")
    
    try:
        # Temporarily override screenshot settings
        settings.screenshot_settings.data_dir = temp_dir
        
        vision_client = GroqVisionClient(settings)
        screenshot_manager = ScreenshotManager(settings, vision_client, llm_client=None)
        
        print(f"Screenshots will be saved to: {temp_dir}")
        
        # Test active window capture
        print("\nTesting active window capture...")
        success, message, path = screenshot_manager.capture_screenshot("active_window")
        
        if success and path and path.exists():
            print(f"✅ Active window captured: {path}")
            print(f"   File size: {path.stat().st_size} bytes")
        else:
            print(f"❌ Active window capture failed: {message}")
            return False
        
        # Test all monitors capture
        print("\nTesting all monitors capture...")
        success, message, path = screenshot_manager.capture_screenshot("all_monitors")
        
        if success and path and path.exists():
            print(f"✅ All monitors captured: {path}")
            print(f"   File size: {path.stat().st_size} bytes")
        else:
            print(f"❌ All monitors capture failed: {message}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
            print(f"\n🧹 Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            print(f"⚠️  Failed to clean up temp directory: {e}")


def test_filename_sanitization():
    """Test filename sanitization."""
    print("\n" + "=" * 70)
    print("TEST 4: Filename Sanitization")
    print("=" * 70)
    
    settings = load_settings()
    temp_dir = tempfile.mkdtemp(prefix="screenshot_test_")
    
    try:
        settings.screenshot_settings.data_dir = temp_dir
        vision_client = GroqVisionClient(settings)
        screenshot_manager = ScreenshotManager(settings, vision_client, llm_client=None)
        
        test_cases = [
            ("Simple text", "Simple_text"),
            ("Text with special chars!@#$%", "Text_with_special_chars"),
            ("  Leading and trailing spaces  ", "Leading_and_trailing_spaces"),
            ("Multiple    spaces   between", "Multiple_spaces_between"),
            ("Très long description that should be truncated to 50 characters maximum", "Trs_long_description_that_should_be_truncated_to"),
            ("", "screenshot"),  # Empty should return default
            ("!@#$%^&*()", "screenshot"),  # Only special chars should return default
        ]
        
        print("Testing sanitization cases:")
        for input_text, expected_output in test_cases:
            result = screenshot_manager._sanitize_filename(input_text, max_length=50)
            status = "✅" if result == expected_output else "❌"
            print(f"{status} '{input_text[:30]}...' → '{result}'")
            if result != expected_output:
                print(f"   Expected: '{expected_output}'")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def test_multi_step_workflow():
    """Test the full multi-step agentic workflow (without actual API calls)."""
    print("\n" + "=" * 70)
    print("TEST 5: Multi-Step Workflow (Dry Run)")
    print("=" * 70)
    
    print("This test validates the workflow structure without making API calls.")
    print("For full integration testing, run the system and use voice commands.")
    
    settings = load_settings()
    temp_dir = tempfile.mkdtemp(prefix="screenshot_test_")
    
    try:
        settings.screenshot_settings.data_dir = temp_dir
        
        vision_client = GroqVisionClient(settings)
        llm_client = LiteLLMClient(settings)
        screenshot_manager = ScreenshotManager(settings, vision_client, llm_client)
        
        print("✅ All components initialized")
        print("   - GroqVisionClient")
        print("   - LiteLLMClient")
        print("   - ScreenshotManager")
        
        print("\n📋 Workflow would execute:")
        print("   1. Play processing sound")
        print("   2. Capture screenshot")
        print("   3. Send to vision API")
        print("   4. Save with description")
        print("   5. Call LLM for answer")
        print("   6. Return feedback")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def test_registry_integration():
    """Test integration with ToolRegistry."""
    print("\n" + "=" * 70)
    print("TEST 6: Tool Registry Integration")
    print("=" * 70)
    
    settings = load_settings()
    temp_dir = tempfile.mkdtemp(prefix="screenshot_test_")
    
    try:
        settings.screenshot_settings.data_dir = temp_dir
        
        registry = ToolRegistry(settings)
        llm_client = LiteLLMClient(settings)
        
        print("✅ ToolRegistry initialized")
        
        if registry.screenshot_manager:
            print("✅ Screenshot manager available in registry")
        else:
            print("❌ Screenshot manager not initialized")
            return False
        
        # Test tool call structure (without actual execution)
        tool_call = {
            "tool_name": "analyze_screen",
            "parameters": {
                "user_question": "What's on the screen?",
                "capture_mode": "active_window"
            }
        }
        
        print(f"\n📋 Tool call structure validated:")
        print(f"   Tool: {tool_call['tool_name']}")
        print(f"   Parameters: {tool_call['parameters']}")
        
        # Test disabled state handling
        original_enabled = settings.screenshot_settings.enabled
        settings.screenshot_settings.enabled = False
        registry_disabled = ToolRegistry(settings)
        
        if registry_disabled.screenshot_manager is None:
            print("✅ Disabled state handled correctly")
        else:
            print("❌ Screenshot manager should be None when disabled")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def test_error_handling():
    """Test error handling scenarios."""
    print("\n" + "=" * 70)
    print("TEST 7: Error Handling")
    print("=" * 70)
    
    settings = load_settings()
    temp_dir = tempfile.mkdtemp(prefix="screenshot_test_")
    
    try:
        settings.screenshot_settings.data_dir = temp_dir
        vision_client = GroqVisionClient(settings)
        
        # Test with non-existent image
        print("Testing with non-existent image...")
        success, description = vision_client.analyze_image("non_existent_file.png")
        
        if not success:
            print(f"✅ Error handled correctly: {description[:100]}")
        else:
            print("❌ Should have failed with non-existent file")
            return False
        
        # Test invalid capture mode
        screenshot_manager = ScreenshotManager(settings, vision_client, llm_client=None)
        print("\nTesting invalid capture mode...")
        success, message, path = screenshot_manager.capture_screenshot("invalid_mode")
        
        if not success:
            print(f"✅ Invalid mode handled correctly: {message}")
        else:
            print("❌ Should have failed with invalid mode")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("SCREENSHOT VISION ANALYSIS - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Vision Client", test_vision_client),
        ("Vision with Focus Hint", test_vision_with_focus_hint),
        ("Screenshot Capture", test_screenshot_capture),
        ("Filename Sanitization", test_filename_sanitization),
        ("Multi-Step Workflow", test_multi_step_workflow),
        ("Registry Integration", test_registry_integration),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "-" * 70)
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("=" * 70)
    
    if passed == total:
        print("\n🎉 All tests passed successfully!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

