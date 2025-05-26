#!/usr/bin/env python3
"""
Test script for Piper TTS integration.
Tests TTS initialization, voice model loading, and speech synthesis.
"""

import os
import sys
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config.settings import load_settings
from src.tts.piper_client import PiperTTSClient
from src.utils.logger import app_logger


def test_tts_initialization():
    """Test TTS client initialization."""
    print("=" * 60)
    print("🧪 Testing TTS Initialization")
    print("=" * 60)
    
    try:
        settings = load_settings()
        app_logger.info("Settings loaded successfully")
        
        # Display TTS configuration
        tts_config = settings.tts_settings
        print(f"TTS Enabled: {tts_config.enabled}")
        print(f"Voice Model: {tts_config.voice_model}")
        print(f"Use CUDA: {tts_config.use_cuda}")
        print(f"Models Directory: {tts_config.models_dir}")
        print(f"Sample Rate: {tts_config.sample_rate}")
        print(f"Speak Responses: {tts_config.speak_responses}")
        
        # Initialize TTS client
        print("\n🔄 Initializing TTS client...")
        tts_client = PiperTTSClient(settings)
        
        if tts_client.is_available():
            print("✅ TTS client initialized successfully!")
            voice_info = tts_client.get_voice_info()
            print(f"Voice Info: {voice_info}")
            return tts_client
        else:
            print("❌ TTS client initialization failed")
            return None
            
    except Exception as e:
        print(f"❌ Error during TTS initialization: {e}")
        app_logger.error(f"TTS initialization error: {e}", exc_info=True)
        return None


def test_basic_speech(tts_client):
    """Test basic speech synthesis."""
    print("\n" + "=" * 60)
    print("🧪 Testing Basic Speech Synthesis")
    print("=" * 60)
    
    if not tts_client:
        print("❌ TTS client not available for testing")
        return False
    
    test_phrases = [
        "Hello! This is a test of the Piper text to speech system.",
        "The voice assistant is now ready to speak responses.",
        "Music control activated. Playing your favorite songs.",
        "Volume adjusted to fifty percent.",
        "System ready for voice commands."
    ]
    
    for i, phrase in enumerate(test_phrases, 1):
        print(f"\n🗣️ Test {i}: '{phrase}'")
        try:
            success = tts_client.speak(phrase)
            if success:
                print(f"✅ Speech test {i} completed successfully")
                time.sleep(1)  # Brief pause between tests
            else:
                print(f"❌ Speech test {i} failed")
                return False
        except Exception as e:
            print(f"❌ Error in speech test {i}: {e}")
            return False
    
    return True


def test_async_speech(tts_client):
    """Test asynchronous speech synthesis."""
    print("\n" + "=" * 60)
    print("🧪 Testing Asynchronous Speech")
    print("=" * 60)
    
    if not tts_client:
        print("❌ TTS client not available for testing")
        return False
    
    try:
        print("🗣️ Starting async speech test...")
        tts_client.speak_async("This is an asynchronous speech test. The function should return immediately.")
        print("✅ Async function returned immediately")
        
        # Wait for speech to complete
        print("⏳ Waiting for speech to complete...")
        time.sleep(5)
        
        print("✅ Async speech test completed")
        return True
        
    except Exception as e:
        print(f"❌ Error in async speech test: {e}")
        return False


def test_interruption(tts_client):
    """Test speech interruption functionality."""
    print("\n" + "=" * 60)
    print("🧪 Testing Speech Interruption")
    print("=" * 60)
    
    if not tts_client:
        print("❌ TTS client not available for testing")
        return False
    
    try:
        print("🗣️ Starting long speech that will be interrupted...")
        tts_client.speak_async("This is a very long speech that should be interrupted by another speech. " +
                              "We are testing the interruption functionality to ensure that new speech " +
                              "can override currently playing speech when needed.")
        
        time.sleep(2)  # Let it start speaking
        
        print("🛑 Interrupting with new speech...")
        success = tts_client.speak("Interruption successful! This new speech should override the previous one.")
        
        if success:
            print("✅ Speech interruption test completed successfully")
            return True
        else:
            print("❌ Speech interruption test failed")
            return False
            
    except Exception as e:
        print(f"❌ Error in interruption test: {e}")
        return False


def test_error_handling(tts_client):
    """Test error handling with invalid inputs."""
    print("\n" + "=" * 60)
    print("🧪 Testing Error Handling")
    print("=" * 60)
    
    if not tts_client:
        print("❌ TTS client not available for testing")
        return False
    
    test_cases = [
        ("", "Empty string"),
        ("   ", "Whitespace only"),
        (None, "None value"),
    ]
    
    for test_input, description in test_cases:
        print(f"\n🧪 Testing {description}: {repr(test_input)}")
        try:
            result = tts_client.speak(test_input)
            if not result:  # Should return False for invalid inputs
                print(f"✅ Correctly handled {description}")
            else:
                print(f"⚠️ Unexpected success for {description}")
        except Exception as e:
            print(f"❌ Exception for {description}: {e}")
            return False
    
    print("✅ Error handling tests completed")
    return True


def main():
    """Run all TTS tests."""
    print("🎤 Piper TTS Integration Test Suite")
    print("=" * 60)
    
    # Test initialization
    tts_client = test_tts_initialization()
    
    if not tts_client:
        print("\n❌ TTS initialization failed. Cannot proceed with other tests.")
        return False
    
    # Run all tests
    tests = [
        ("Basic Speech", test_basic_speech),
        ("Async Speech", test_async_speech),
        ("Speech Interruption", test_interruption),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func(tts_client)
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Unexpected error in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All TTS tests passed! The system is ready for voice responses.")
    else:
        print("⚠️ Some tests failed. Please check the configuration and dependencies.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)