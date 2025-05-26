# Gradual Volume Change Feature

## Overview
The Home Assistant Voice Control System now supports smooth, gradual volume transitions instead of jarring instant volume changes. This enhancement improves user experience by providing natural-feeling volume adjustments.

## Features

### Enhanced SetSystemVolume Function
The `SetSystemVolume` function in `src/tools/utils.py` now supports optional duration-based volume transitions:

```python
SetSystemVolume(percentage, duration=None, steps=20)
```

**Parameters:**
- `percentage`: Target volume percentage (0-100)
- `duration`: Optional transition duration in seconds. If `None` or `<= 0`, changes volume instantly
- `steps`: Number of intermediate steps for smooth transition (default: 20)

### Automatic Thread Management
The enhanced `SetSystemVolume` function automatically handles:
- Thread cancellation when starting new transitions
- Volume state management
- Graceful handling of concurrent requests

## Usage Examples

### Instant Volume Change (Backward Compatible)
```python
SetSystemVolume(50)  # Instant change to 50%
```

### Gradual Volume Change
```python
# Gradually change to 80% over 3 seconds
SetSystemVolume(80, duration=3.0, steps=30)

# Quick transition with default steps
SetSystemVolume(60, duration=2.0)

# Starting a new transition automatically cancels any previous one
SetSystemVolume(50, duration=1.0)  # This cancels the previous transition
```

## Implementation Details

### Threading
- Gradual volume changes run in separate daemon threads
- Non-blocking operation - main program continues immediately
- Thread name: "VolumeTransition" for easy identification
- Thread-safe cancellation support
- Automatic cancellation of previous transitions when starting new ones

### Algorithm
1. Get current system volume
2. Check if already at target volume (skip if within 1%)
3. Calculate volume difference and step size
4. Perform incremental volume changes over specified duration
5. Each step includes bounds checking (0-100%)
6. Cancellation-aware sleep between steps
7. Graceful handling of thread cancellation

### Error Handling
- Validates volume percentage range (0-100)
- Handles COM initialization/cleanup for Windows audio APIs
- Graceful fallback if current volume cannot be retrieved
- Comprehensive logging for debugging

## Integration in Main Application

The main voice control loop now uses gradual transitions:

```python
# Before audio capture - quickly lower volume
SetSystemVolume(system_volume/3, duration=1.0, steps=10)

# After audio capture - smoothly restore volume  
SetSystemVolume(system_volume, duration=1.0, steps=15)
```

## Testing

Run the test script to see the feature in action:
```bash
python -m src.test_gradual_volume
```

The test demonstrates:
- Instant vs gradual volume changes
- Different durations and step counts
- Edge cases (zero duration, negative duration)
- Automatic thread cancellation when starting new transitions
- Volume restoration

## Benefits

1. **Better UX**: Smooth transitions feel more natural than instant changes
2. **Non-blocking**: Volume changes don't interrupt main program flow
3. **Configurable**: Adjustable duration and smoothness
4. **Backward Compatible**: Existing code continues to work unchanged
5. **Thread Safe**: Proper COM handling for Windows audio APIs
6. **Simplified API**: Single function handles both instant and gradual changes
7. **Automatic Management**: No need to manually cancel transitions

## Technical Notes

- Uses Windows `pycaw` library for volume control
- Requires `comtypes` and `pycaw` packages
- Thread-safe COM initialization/cleanup
- Daemon threads automatically clean up on program exit
- Floating-point precision handling for volume calculations 