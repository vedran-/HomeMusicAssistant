#!/usr/bin/env python3
"""
Wake Word Stability Test Script

This script helps test and debug wake word detection stability,
including false positive detection and retriggering issues.
"""

import os
import sys
import time
from datetime import datetime

# Add src to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.config.settings import load_settings
from src.audio.wake_word import WakeWordDetector
from src.utils.logger import app_logger

class WakeWordStabilityTester:
    def __init__(self):
        self.settings = load_settings()
        self.detector = WakeWordDetector(self.settings)
        self.detection_count = 0
        self.start_time = None
        
    def test_stability(self, duration_minutes=5):
        """Test wake word detection stability for a specified duration."""
        print(f"\n🔍 Wake Word Stability Test")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Wake word: {self.detector.active_model}")
        print(f"Sensitivity: {self.detector.sensitivity}")
        print("\n⚠️  Instructions:")
        print("- DO NOT say the wake word during this test")
        print("- Keep the environment quiet")
        print("- This test detects false positives and retriggering")
        print("\nStarting test in 3 seconds...")
        
        for i in range(3, 0, -1):
            print(f"{i}...")
            time.sleep(1)
        
        print("🎧 Test started - monitoring for false wake word detections...")
        self.start_time = datetime.now()
        end_time = time.time() + (duration_minutes * 60)
        
        detection_times = []
        
        try:
            while time.time() < end_time:
                if self.detector.listen():
                    detection_time = datetime.now()
                    self.detection_count += 1
                    time_since_start = (detection_time - self.start_time).total_seconds()
                    
                    print(f"❌ FALSE POSITIVE #{self.detection_count} at {detection_time.strftime('%H:%M:%S')} (after {time_since_start:.1f}s)")
                    detection_times.append(time_since_start)
                    
                    # Brief pause before resuming
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            print("\n⚠️  Test interrupted by user")
        
        # Test results
        test_duration = (datetime.now() - self.start_time).total_seconds()
        print(f"\n📊 Test Results:")
        print(f"Test duration: {test_duration:.1f} seconds ({test_duration/60:.1f} minutes)")
        print(f"False positives detected: {self.detection_count}")
        
        if self.detection_count == 0:
            print("✅ EXCELLENT: No false positives detected!")
        elif self.detection_count <= 2:
            print("⚠️  ACCEPTABLE: Few false positives (may be environmental)")
        else:
            print("❌ PROBLEM: Too many false positives - check sensitivity or environment")
            
        if len(detection_times) > 1:
            intervals = [detection_times[i] - detection_times[i-1] for i in range(1, len(detection_times))]
            avg_interval = sum(intervals) / len(intervals)
            print(f"Average interval between false positives: {avg_interval:.1f}s")
            
            if any(interval < 5.0 for interval in intervals):
                print("❌ RETRIGGERING ISSUE: Some detections too close together")
            else:
                print("✅ NO RETRIGGERING: Good spacing between detections")

def main():
    print("Wake Word Stability Tester")
    print("=" * 40)
    
    try:
        tester = WakeWordStabilityTester()
        
        # Quick 1-minute test by default
        duration = 1
        print(f"\nRunning {duration}-minute stability test...")
        tester.test_stability(duration)
        
    except Exception as e:
        app_logger.error(f"Test failed: {e}", exc_info=True)
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main() 