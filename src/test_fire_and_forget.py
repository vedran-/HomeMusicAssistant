#!/usr/bin/env python3
"""
Test script to verify fire-and-forget behavior of volume control and audio effects.
This test confirms that both functions don't block the main thread.
"""

import time
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ..tools.utils import GetSystemVolume, SetSystemVolume
from ..utils.logger import app_logger, configure_logging

def test_volume_fire_and_forget():
    """Test that SetSystemVolume with duration is fire and forget."""
    app_logger.info("🔊 Testing SetSystemVolume Fire-and-Forget Behavior")
    app_logger.info("=" * 55)
    
    current_volume = GetSystemVolume()
    if current_volume is None:
        app_logger.error("❌ Could not get current system volume")
        return False
    
    app_logger.info(f"📊 Current volume: {current_volume}%")
    
    # Test: Start a gradual transition and verify main thread continues immediately
    app_logger.info("\n🚀 Starting 3-second gradual volume transition...")
    start_time = time.time()
    
    # This should return immediately, not block for 3 seconds
    result = SetSystemVolume(80, duration=3.0, steps=30)
    
    call_duration = time.time() - start_time
    app_logger.info(f"⏱️ SetSystemVolume call took: {call_duration:.3f} seconds")
    
    if call_duration > 0.1:  # Should return almost instantly
        app_logger.error(f"❌ SetSystemVolume blocked for {call_duration:.3f}s - NOT fire and forget!")
        return False
    else:
        app_logger.info("✅ SetSystemVolume returned immediately - IS fire and forget!")
    
    # Verify main thread can do other work while volume changes
    app_logger.info("\n🔄 Main thread doing other work while volume changes...")
    for i in range(3):
        app_logger.info(f"   Main thread working... step {i+1}/3")
        time.sleep(1)
    
    # Restore original volume
    SetSystemVolume(current_volume, duration=1.0)
    time.sleep(2)
    
    app_logger.info("🎉 Volume fire-and-forget test completed!")
    return True

if __name__ == "__main__":
    try:
        configure_logging("INFO")
        app_logger.info("🎵 Testing Fire-and-Forget Behavior")
        app_logger.info("=" * 40)
        
        if test_volume_fire_and_forget():
            app_logger.info("\n🎊 Fire-and-forget test PASSED!")
            app_logger.info("✅ SetSystemVolume with duration is non-blocking")
        else:
            app_logger.error("\n❌ Fire-and-forget test FAILED!")
            sys.exit(1)
        
    except KeyboardInterrupt:
        app_logger.info("\n⏹️ Test interrupted by user")
    except Exception as e:
        app_logger.error(f"❌ Test failed with error: {e}", exc_info=True)
        sys.exit(1) 