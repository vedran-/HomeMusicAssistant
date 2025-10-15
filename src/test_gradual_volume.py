#!/usr/bin/env python3
"""
Test script for gradual volume change functionality.
Demonstrates the enhanced SetSystemVolume function with duration effects.
"""

import time
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ..tools.utils import GetSystemVolume, SetSystemVolume
from ..utils.logger import app_logger, configure_logging

def test_gradual_volume():
    """Test the gradual volume change functionality."""
    configure_logging("INFO")
    
    app_logger.info("🔊 Testing Gradual Volume Change Functionality")
    app_logger.info("=" * 50)
    
    # Get current volume
    current_volume = GetSystemVolume()
    if current_volume is None:
        app_logger.error("❌ Could not get current system volume")
        return False
    
    app_logger.info(f"📊 Current system volume: {current_volume}%")
    
    # Test 1: Instant volume change
    app_logger.info("\n🚀 Test 1: Instant volume change to 50%")
    SetSystemVolume(50)
    time.sleep(1)
    
    # Test 2: Gradual volume change to 80% over 3 seconds
    app_logger.info("\n🌊 Test 2: Gradual volume change to 80% over 3 seconds")
    SetSystemVolume(80, duration=3.0, steps=30)
    time.sleep(4)  # Wait for completion
    
    # Test 3: Gradual volume change to 20% over 2 seconds
    app_logger.info("\n🌊 Test 3: Gradual volume change to 20% over 2 seconds")
    SetSystemVolume(20, duration=2.0, steps=20)
    time.sleep(3)  # Wait for completion
    
    # Test 4: Quick gradual change to 60% over 1 second
    app_logger.info("\n⚡ Test 4: Quick gradual change to 60% over 1 second")
    SetSystemVolume(60, duration=1.0, steps=10)
    time.sleep(2)  # Wait for completion
    
    # Test 5: Using SetSystemVolume with duration parameter
    app_logger.info("\n🎛️ Test 5: Using SetSystemVolume with duration parameter")
    SetSystemVolume(40, duration=2.5, steps=25)
    time.sleep(3)  # Wait for completion
    
    # Restore original volume gradually
    app_logger.info(f"\n🔄 Restoring original volume ({current_volume}%) gradually over 2 seconds")
    SetSystemVolume(current_volume, duration=2.0, steps=20)
    time.sleep(3)  # Wait for completion
    
    final_volume = GetSystemVolume()
    app_logger.info(f"✅ Final volume: {final_volume}%")
    app_logger.info("🎉 Gradual volume change test completed!")
    
    return True

def test_edge_cases():
    """Test edge cases for the gradual volume functionality."""
    app_logger.info("\n🧪 Testing Edge Cases")
    app_logger.info("=" * 30)
    
    current_volume = GetSystemVolume()
    
    # Test with zero duration (should be instant)
    app_logger.info("Test: Zero duration (should be instant)")
    SetSystemVolume(50, duration=0)
    time.sleep(0.5)
    
    # Test with negative duration (should be instant)
    app_logger.info("Test: Negative duration (should be instant)")
    SetSystemVolume(60, duration=-1)
    time.sleep(0.5)
    
    # Test with very small steps
    app_logger.info("Test: Very small steps (2 steps)")
    SetSystemVolume(70, duration=1.0, steps=2)
    time.sleep(2)
    
    # Test with many steps
    app_logger.info("Test: Many steps (50 steps)")
    SetSystemVolume(30, duration=2.0, steps=50)
    time.sleep(3)
    
    # Test automatic cancellation (start long transition, then start new one)
    app_logger.info("Test: Automatic cancellation (start long transition, then start new one)")
    SetSystemVolume(90, duration=5.0, steps=50)
    time.sleep(1)  # Let it start
    app_logger.info("Starting new transition - should automatically cancel previous one")
    SetSystemVolume(40, duration=1.0, steps=10)
    time.sleep(2)
    
    # Restore original volume
    SetSystemVolume(current_volume, duration=1.0)
    time.sleep(2)
    
    app_logger.info("✅ Edge case testing completed!")

if __name__ == "__main__":
    try:
        app_logger.info("🎵 Starting Gradual Volume Change Tests")
        
        if not test_gradual_volume():
            sys.exit(1)
            
        test_edge_cases()
        
        app_logger.info("\n🎊 All tests completed successfully!")
        
    except KeyboardInterrupt:
        app_logger.info("\n⏹️ Test interrupted by user")
        # Try to restore a reasonable volume
        SetSystemVolume(50)
    except Exception as e:
        app_logger.error(f"❌ Test failed with error: {e}", exc_info=True)
        sys.exit(1) 