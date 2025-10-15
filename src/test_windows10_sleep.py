"""
Test script for Windows 10 sleep management functionality.

This script tests:
- System idle time detection
- Power request parsing
- Sleep decision logic
- Integration with wake word detection
"""

import time
import platform
from src.config.settings import load_settings
from src.utils.power_management import WindowsPowerManager, CrossPlatformPowerManager
from src.utils.logger import app_logger


def test_idle_time_detection():
    """Test system idle time detection."""
    print("\n" + "="*60)
    print("TEST 1: System Idle Time Detection")
    print("="*60)
    
    if platform.system() != "Windows":
        print("⚠️  Skipping - not on Windows")
        return
    
    try:
        settings = load_settings()
        power_manager = WindowsPowerManager(power_settings=settings.power)
        
        idle_time = power_manager.get_system_idle_time()
        print(f"✓ System idle time: {idle_time:.2f} minutes")
        print(f"  (Move your mouse/keyboard to reset this value)")
        
        # Wait a few seconds and check again
        print("\nWaiting 5 seconds...")
        time.sleep(5)
        
        idle_time_after = power_manager.get_system_idle_time()
        print(f"✓ System idle time after 5 seconds: {idle_time_after:.2f} minutes")
        
        if idle_time_after > idle_time:
            print("✓ Idle time is increasing correctly")
        else:
            print("⚠️  User activity detected (idle time reset)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_power_requests_parsing():
    """Test power request parsing and filtering."""
    print("\n" + "="*60)
    print("TEST 2: Power Requests Parsing")
    print("="*60)
    
    if platform.system() != "Windows":
        print("⚠️  Skipping - not on Windows")
        return
    
    try:
        settings = load_settings()
        power_manager = WindowsPowerManager(power_settings=settings.power)
        
        # Get all power requests
        raw_output = power_manager._powercfg_requests()
        if raw_output:
            print("\nRaw powercfg output (first 500 chars):")
            print("-" * 60)
            print(raw_output[:500])
            print("-" * 60)
        
        # Get parsed blockers from all categories
        system_blockers = power_manager._extract_system_driver_blockers(raw_output)
        execution_blockers = power_manager._extract_execution_blockers(raw_output)
        awaymode_blockers = power_manager._extract_section_blockers(raw_output, "AWAYMODE:")
        perfboost_blockers = power_manager._extract_section_blockers(raw_output, "PERFBOOST:")
        display_blockers = power_manager._extract_section_blockers(raw_output, "DISPLAY:")
        lockscreen_blockers = power_manager._extract_section_blockers(raw_output, "ACTIVELOCKSCREEN:")

        print(f"\n✓ SYSTEM blockers found: {len(system_blockers)}")
        for blocker in system_blockers:
            print(f"  - {blocker}")

        print(f"\n✓ EXECUTION blockers found: {len(execution_blockers)}")
        for blocker in execution_blockers:
            print(f"  - {blocker}")

        print(f"\n✓ AWAYMODE blockers found: {len(awaymode_blockers)}")
        for blocker in awaymode_blockers:
            print(f"  - {blocker}")

        print(f"\n✓ PERFBOOST blockers found: {len(perfboost_blockers)}")
        for blocker in perfboost_blockers:
            print(f"  - {blocker}")

        print(f"\n✓ DISPLAY blockers found: {len(display_blockers)} (ignored for sleep)")
        for blocker in display_blockers:
            print(f"  - {blocker}")

        print(f"\n✓ ACTIVELOCKSCREEN blockers found: {len(lockscreen_blockers)} (ignored for sleep)")
        for blocker in lockscreen_blockers:
            print(f"  - {blocker}")

        # Get filtered blockers (excluding our audio) - only sleep-blocking categories
        other_blockers = power_manager.get_other_power_requests()
        print(f"\n✓ Sleep-blocking categories (SYSTEM+EXECUTION+AWAYMODE+PERFBOOST): {len(other_blockers)}")
        if other_blockers:
            for blocker in other_blockers:
                print(f"  - {blocker}")
            print("\n⚠️  These apps are currently blocking sleep:")
            print("  (Computer should NOT sleep while these are active)")
        else:
            print("  None - only our audio recording blocking (computer can sleep)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_sleep_decision_logic():
    """Test the sleep decision logic."""
    print("\n" + "="*60)
    print("TEST 3: Sleep Decision Logic")
    print("="*60)
    
    if platform.system() != "Windows":
        print("⚠️  Skipping - not on Windows")
        return
    
    try:
        settings = load_settings()
        
        # Test with Windows 10
        if platform.release() == "10":
            print("✓ Detected Windows 10")
        else:
            print(f"⚠️  Detected Windows {platform.release()} (not Windows 10)")
            print("  Sleep management is Windows 10 specific")
        
        power_manager = WindowsPowerManager(power_settings=settings.power)
        
        # Check current sleep decision
        should_sleep, reason = power_manager.should_allow_sleep()
        
        print(f"\nSleep Decision: {'ALLOW' if should_sleep else 'DENY'}")
        print(f"Reason: {reason}")
        
        # Show details
        idle_time = power_manager.get_system_idle_time()
        threshold = settings.power.idle_timeout_minutes
        other_blockers = power_manager.get_other_power_requests()
        
        print("\nDetails:")
        print(f"  Idle time: {idle_time:.2f} minutes")
        print(f"  Threshold: {threshold} minutes")
        print(f"  Idle requirement: {'✓ MET' if idle_time >= threshold else '✗ NOT MET'}")
        print(f"  Other blockers: {len(other_blockers)}")
        if other_blockers:
            for blocker in other_blockers[:3]:
                print(f"    - {blocker}")
        print(f"  Blocker requirement: {'✓ MET (no blockers)' if not other_blockers else '✗ NOT MET (blockers present)'}")
        
        # Test configuration
        print("\nConfiguration:")
        print(f"  Managed sleep enabled: {settings.power.windows10_managed_sleep_enabled}")
        print(f"  Idle timeout: {settings.power.idle_timeout_minutes} minutes")
        print(f"  Check interval: {settings.power.sleep_check_interval_seconds} seconds")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_cross_platform_wrapper():
    """Test the CrossPlatformPowerManager wrapper."""
    print("\n" + "="*60)
    print("TEST 4: CrossPlatformPowerManager Wrapper")
    print("="*60)
    
    try:
        settings = load_settings()
        power_manager = CrossPlatformPowerManager(settings)
        
        print(f"✓ Platform: {power_manager.platform}")
        
        # Test wrapper methods
        idle_time = power_manager.get_system_idle_time()
        print(f"✓ get_system_idle_time(): {idle_time:.2f} minutes")
        
        should_sleep, reason = power_manager.should_allow_sleep()
        print(f"✓ should_allow_sleep(): {should_sleep} - {reason}")

        # Test with conversation active (should extend idle timeout)
        should_sleep_conversation, reason_conversation = power_manager.should_allow_sleep(conversation_active=True)
        print(f"✓ should_allow_sleep(conversation_active=True): {should_sleep_conversation} - {reason_conversation}")

        # Don't actually test force_sleep (would put computer to sleep!)
        print("⚠️  Skipping force_sleep_if_appropriate() test (would sleep the computer)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_configuration_loading():
    """Test that configuration loads correctly."""
    print("\n" + "="*60)
    print("TEST 5: Configuration Loading")
    print("="*60)
    
    try:
        settings = load_settings()
        
        if hasattr(settings, 'power'):
            print("✓ Power settings loaded")
            print(f"  windows10_managed_sleep_enabled: {settings.power.windows10_managed_sleep_enabled}")
            print(f"  idle_timeout_minutes: {settings.power.idle_timeout_minutes}")
            print(f"  sleep_check_interval_seconds: {settings.power.sleep_check_interval_seconds}")
            print(f"  allow_sleep_during_capture: {settings.power.allow_sleep_during_capture}")
            print(f"  diagnose_on_startup: {settings.power.diagnose_on_startup}")
        else:
            print("❌ Power settings not found in configuration")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def interactive_idle_time_test():
    """Interactive test to monitor idle time."""
    print("\n" + "="*60)
    print("INTERACTIVE TEST: Monitor Idle Time")
    print("="*60)
    print("\nThis will monitor your system idle time for 30 seconds.")
    print("Try moving your mouse or pressing keys to see the idle time reset.")
    print("\nStarting in 3 seconds...")
    time.sleep(3)
    
    if platform.system() != "Windows":
        print("⚠️  Skipping - not on Windows")
        return
    
    try:
        settings = load_settings()
        power_manager = WindowsPowerManager(power_settings=settings.power)
        
        print("\nMonitoring (Ctrl+C to stop):")
        print("-" * 60)
        
        for i in range(30):
            idle_time = power_manager.get_system_idle_time()
            print(f"[{i+1:2d}/30] Idle time: {idle_time:.2f} minutes", end='\r')
            time.sleep(1)
        
        print("\n" + "-" * 60)
        print("✓ Monitoring complete")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Windows 10 Sleep Management Test Suite")
    print("="*60)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests
    test_configuration_loading()
    test_idle_time_detection()
    test_power_requests_parsing()
    test_sleep_decision_logic()
    test_cross_platform_wrapper()
    
    # Optional interactive test
    print("\n" + "="*60)
    response = input("\nRun interactive idle time monitor? (y/n): ").strip().lower()
    if response == 'y':
        interactive_idle_time_test()
    
    print("\n" + "="*60)
    print("All tests complete!")
    print("="*60)
    print("\n⚠️  IMPORTANT: The actual sleep functionality was NOT tested")
    print("   to avoid putting your computer to sleep during testing.")
    print("\nTo test actual sleep behavior:")
    print("1. Run the main application (python -m src.main)")
    print("2. Leave your computer idle for the configured timeout")
    print("3. Ensure no music/videos are playing")
    print("4. System should sleep automatically after timeout")
    print("\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

