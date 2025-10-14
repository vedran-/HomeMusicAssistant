# Windows 10 Sleep Management Implementation

**Implementation Date**: October 14, 2025  
**Status**: ✅ Complete and Ready for Testing

## Overview

This implementation adds intelligent sleep management for Windows 10 systems, allowing the voice assistant to run continuously while still permitting the computer to sleep when appropriate.

## The Problem

On Windows 10, continuous audio recording for wake word detection creates a driver-level power request that blocks the system from entering sleep mode, even when the user is idle. This is different from Windows 11, which handles audio streams more intelligently.

## The Solution

Instead of trying to work around Windows 10's sleep blocking, we implement our own sleep management logic that:

1. **Monitors system idle time** - Uses Windows `GetLastInputInfo` API to track user activity
2. **Checks for other applications** - Parses `powercfg /requests` to detect music players, video players, etc.
3. **Makes intelligent sleep decisions** - Only forces sleep when:
   - User has been idle for configured timeout (default: 10 minutes)
   - No other applications are blocking sleep (no music, videos, etc.)
   - Running on Windows 10 (Windows 11 doesn't need this)
   - Feature is enabled in configuration

## Implementation Details

### 1. Configuration Schema (`src/config/settings.py`)

Added three new fields to `PowerSettings`:

```python
windows10_managed_sleep_enabled: bool = True  # Enable/disable the feature
idle_timeout_minutes: int = 10                # How long user must be idle
sleep_check_interval_seconds: int = 120       # How often to check (2 minutes)
```

### 2. Power Management Module (`src/utils/power_management.py`)

Added four new methods to `WindowsPowerManager`:

#### `get_system_idle_time() -> float`
- Uses `GetLastInputInfo` Windows API
- Returns minutes since last mouse/keyboard input
- Returns 0.0 on non-Windows platforms

#### `get_other_power_requests() -> List[str]`
- Executes `powercfg /requests`
- Parses SYSTEM section for blockers
- Filters out audio drivers (our recording)
- Returns list of other apps blocking sleep

#### `should_allow_sleep() -> Tuple[bool, str]`
- Checks if Windows 10
- Checks if feature enabled
- Checks if idle time exceeds threshold
- Checks for other blockers
- Returns (should_sleep, reason)

#### `force_sleep_if_appropriate() -> bool`
- Calls `should_allow_sleep()`
- If conditions met, calls `SetSuspendState(False, False, False)`
- Logs decision and reason
- Returns True if sleep attempted

### 3. Wake Word Detection Integration (`src/audio/wake_word.py`)

Added sleep monitoring to the wake word detection loop:

#### New Instance Variables
```python
self.last_sleep_check_time = 0  # Track when we last checked
```

#### New Methods

**`_should_check_sleep() -> bool`**
- Returns True if enough time has passed since last check
- Checks if feature is enabled
- Returns False if not Windows 10

**`_check_and_sleep_if_appropriate()`**
- Updates last check time
- Calls power_manager.force_sleep_if_appropriate()
- Logs idle time and decision

#### Integration into Listen Loop
```python
while True:
    # Windows 10: Periodic sleep check
    if self._should_check_sleep():
        self._check_and_sleep_if_appropriate()
    
    # Normal wake word detection
    audio_chunk = self.stream.read(...)
    # ... rest of wake word logic
```

### 4. Configuration File (`config.json`)

Added new `power` section:

```json
"power": {
  "log_power_requests": false,
  "auto_override_windows10_audio_blockers": false,
  "allow_sleep_during_capture": true,
  "diagnose_on_startup": true,
  "windows10_managed_sleep_enabled": true,
  "idle_timeout_minutes": 10,
  "sleep_check_interval_seconds": 120
}
```

## How It Works

### Normal Operation (User Active)

1. User is working on computer
2. Wake word detector runs continuously
3. Every 2 minutes (configurable), system checks:
   - Idle time: 0.5 minutes (user just moved mouse)
   - Decision: **Don't sleep** (not idle enough)
4. Wake word detection continues normally

### Idle with Music Playing

1. User walks away from computer
2. Spotify is playing music in background
3. Every 2 minutes, system checks:
   - Idle time: 15 minutes ✓
   - Other blockers: ["Chrome.exe - Playing audio"] ✗
   - Decision: **Don't sleep** (music playing)
4. Computer stays awake, music continues

### Idle with No Activity

1. User walks away from computer
2. No music, videos, or other activity
3. After 10 minutes idle, next check (at 2-minute interval):
   - Idle time: 10+ minutes ✓
   - Other blockers: [] ✓
   - Decision: **Force sleep**
4. System calls `SetSuspendState()`
5. Computer goes to sleep

## Configuration Options

### `windows10_managed_sleep_enabled` (default: `true`)
- Enable or disable the feature entirely
- Set to `false` if you don't want automatic sleep

### `idle_timeout_minutes` (default: `10`)
- How long user must be idle before sleep is considered
- Increase if you want more time before sleep
- Decrease for quicker sleep

### `sleep_check_interval_seconds` (default: `120`)
- How often to check sleep conditions while listening
- Lower values = more responsive, more CPU usage
- Higher values = less responsive, less CPU usage

## Logging

The implementation includes comprehensive logging:

### DEBUG Level
```
DEBUG: Windows 10 sleep check: system idle for 12.5 minutes
DEBUG: PowerManager: Sleep check - Idle 12.5min, no other blockers
```

### INFO Level
```
INFO: PowerManager: Forcing system sleep (Idle 12.5min, no other blockers)
```

### When Sleep is Deferred
```
DEBUG: Windows 10 sleep check: system idle for 12.5 minutes
DEBUG: PowerManager: Sleep check - Other apps blocking: Chrome.exe - Playing audio
```

## Testing

### Test Script: `src/test_windows10_sleep.py`

Run the comprehensive test suite:

```bash
python -m src.test_windows10_sleep
```

The script tests:
1. ✓ Configuration loading
2. ✓ Idle time detection
3. ✓ Power request parsing
4. ✓ Sleep decision logic
5. ✓ Cross-platform wrapper
6. ✓ Interactive idle time monitoring

**Note**: The test script does NOT actually put the computer to sleep to avoid disruption.

### Manual Testing

To test actual sleep behavior:

1. **Configure timeout**:
   ```json
   "power": {
     "idle_timeout_minutes": 1,  // Short timeout for testing
     "sleep_check_interval_seconds": 30  // Check every 30 seconds
   }
   ```

2. **Run the application**:
   ```bash
   python -m src.main
   ```

3. **Test scenarios**:

   **Scenario A: Idle Sleep**
   - Leave computer idle for 1+ minutes
   - Don't play any music/videos
   - Computer should sleep automatically

   **Scenario B: Music Blocks Sleep**
   - Open Spotify and play music
   - Leave computer idle for 1+ minutes
   - Computer should NOT sleep (music playing)

   **Scenario C: User Activity Resets Timer**
   - Leave computer idle for 50 seconds
   - Move mouse
   - Idle timer resets to 0
   - Computer should NOT sleep

## Platform Compatibility

### Windows 10
- ✅ Fully supported
- ✅ Managed sleep enabled by default
- ✅ All features functional

### Windows 11
- ✅ Supported but not needed
- ℹ️ Windows 11 allows sleep during audio recording natively
- ℹ️ Managed sleep logic is bypassed (not Windows 10)

### Other Platforms (macOS, Linux)
- ✅ Supported via existing power management
- ℹ️ Managed sleep logic is bypassed (not Windows 10)

## Files Modified

1. ✅ `src/config/settings.py` - Added PowerSettings fields
2. ✅ `src/utils/power_management.py` - Added sleep management methods
3. ✅ `src/audio/wake_word.py` - Integrated sleep checks into listen loop
4. ✅ `config.json` - Added power configuration section
5. ✅ `src/test_windows10_sleep.py` - Created test suite (NEW FILE)
6. ✅ `docs/WINDOWS10_SLEEP_IMPLEMENTATION.md` - This document (NEW FILE)

## Key Features

✅ **No burst recording** - Continuous wake word detection  
✅ **Respects other apps** - Checks for music/video playback  
✅ **Respects user activity** - Monitors actual idle time  
✅ **Windows 10 specific** - Doesn't affect Windows 11  
✅ **Configurable** - Users can adjust all thresholds  
✅ **Transparent** - Detailed logging of all decisions  
✅ **Safe** - Only sleeps when all conditions are right  
✅ **No admin rights required** - Works for all users  

## Troubleshooting

### Computer not sleeping on Windows 10

**Check configuration**:
```bash
python -m src.test_windows10_sleep
```

**Common issues**:
1. Feature disabled in config → Set `windows10_managed_sleep_enabled: true`
2. Idle timeout too high → Reduce `idle_timeout_minutes`
3. Other apps blocking → Close music/video players
4. Check interval too long → Reduce `sleep_check_interval_seconds`

**Check logs** (set `"level": "DEBUG"` in config):
```
DEBUG: Windows 10 sleep check: system idle for X.X minutes
DEBUG: PowerManager: Sleep check - [reason]
```

### Computer sleeping too quickly

1. Increase `idle_timeout_minutes` in config
2. Or disable feature: `windows10_managed_sleep_enabled: false`

### Want to prevent sleep entirely

Set in config:
```json
"power": {
  "windows10_managed_sleep_enabled": false
}
```

## Future Enhancements

Potential improvements for future versions:

1. **Smart idle detection** - Learn user patterns
2. **Application whitelist** - Specify apps that should block sleep
3. **Time-based rules** - Different timeouts for different times of day
4. **UI integration** - Visual indicator of sleep status
5. **Sleep delay on wake word** - Extend timeout after user interaction

## Technical Notes

### Why `SetSuspendState`?

We use `SetSuspendState(False, False, False)` with `forceCritical=False`, which means:
- Windows still checks all sleep conditions
- Other apps can still block sleep
- It's like programmatically pressing the Sleep button
- BUT: Windows makes the final decision

### Why Check Every 2 Minutes?

- Balance between responsiveness and CPU usage
- Most users won't notice 2-minute delay
- Configurable for power users
- Could be reduced to 30-60 seconds if desired

### Why Filter Audio Drivers?

- Our audio recording creates a driver-level block
- We want to ignore our own block
- But respect blocks from other apps
- Filters common audio driver names (Realtek, etc.)

## Conclusion

This implementation provides a robust solution for Windows 10 sleep management that:
- Works seamlessly in the background
- Respects user activity and other applications
- Provides extensive configurability
- Maintains continuous wake word detection
- Requires no user intervention

The system is now ready for testing and production use on Windows 10 systems.

