# Music Controller Documentation

## Overview

The `music_controller.ahk` is an AutoHotkey v2 script that provides command-line control for YouTube Music and system volume. It uses UIAutomation v2 for robust browser interaction and works seamlessly with automation systems like Home Assistant.

## System Requirements

- **AutoHotkey v2.0** or higher
- **Windows 10/11**
- **Brave Browser** (configured path: `C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe`)
- **Internet connection** (for music commands)

## Installation

1. Ensure AutoHotkey v2 is installed
2. Place the script in your desired directory
3. Ensure UIAutomation libraries are in the `Lib` subdirectory:
   - `Lib\UIA.ahk`
   - `Lib\UIA_Browser.ahk`

## Usage Syntax

```
music_controller.ahk <command> [parameters]
```

## Commands Reference

### Music Control Commands

#### `play [genre or artist or song]`
Opens YouTube Music and starts playing radio for the specified genre.

**Parameters:**
- `genre` (optional): Music genre or search term. Default: "chill music"

**Examples:**
```bash
music_controller.ahk play
music_controller.ahk play jazz
music_controller.ahk play "classical music"
music_controller.ahk play "study beats"
```

**Behavior:**
- Opens Brave browser with YouTube Music
- Searches for the specified genre
- Automatically starts radio/shuffle play
- Creates new browser instance if needed

#### `search <term>`
Searches for music in YouTube Music without auto-playing.

**Parameters:**
- `term` (required): Search term for music

**Examples:**
```bash
music_controller.ahk search "rock music"
music_controller.ahk search "Beatles"
```

#### `toggle`
Toggles play/pause for currently playing music.

**Examples:**
```bash
music_controller.ahk toggle
```

**Requirements:**
- YouTube Music must already be open
- Will show error if no YouTube Music instance found

### System Volume Commands

#### `get-volume`
Retrieves current system volume and outputs to stdout.

**Output:** Integer value (1-100) representing volume percentage

**Examples:**
```bash
music_controller.ahk get-volume
# Output: 45
```

**Integration Note:** Output goes to stdout for capture by automation systems.

#### `volume-up [percentage]`
Increases volume by relative percentage of current volume.

**Parameters:**
- `percentage` (optional): Percentage increase relative to current volume. Default: 10

**Output:** New volume level to stdout

**Examples:**
```bash
music_controller.ahk volume-up        # Increase by 10% of current
music_controller.ahk volume-up 50     # Increase by 50% of current
```

**Calculation Logic:**
- Uses minimum 1% as calculation base (if current volume < 1%)
- Change = `max(current_volume, 1) * (percentage / 100)`
- Final volume = `current_volume + change`
- Clamped between 1% and 100%

#### `volume-down [percentage]`
Decreases volume by relative percentage of current volume.

**Parameters:**
- `percentage` (optional): Percentage decrease relative to current volume. Default: 10

**Output:** New volume level to stdout

**Examples:**
```bash
music_controller.ahk volume-down      # Decrease by 10% of current
music_controller.ahk volume-down 25   # Decrease by 25% of current
```

**Important:** Volume will never go below 1% (absolute minimum).

#### `mute`
Mutes system audio.

**Examples:**
```bash
music_controller.ahk mute
```

#### `unmute`
Unmutes system audio.

**Examples:**
```bash
music_controller.ahk unmute
```

### Utility Commands

#### `help`
Displays help information with all available commands.

**Examples:**
```bash
music_controller.ahk help
```

## Volume Calculation Examples

Current volume: 40%

| Command | Calculation | Result |
|---------|-------------|---------|
| `volume-up 50` | 40% + (40% × 0.5) = 40% + 20% | 60% |
| `volume-down 25` | 40% - (40% × 0.25) = 40% - 10% | 30% |
| `volume-down 100` | 40% - (40% × 1.0) = 40% - 40% | 1% (clamped) |

Current volume: 0.5%

| Command | Calculation | Result |
|---------|-------------|---------|
| `volume-up 50` | 0.5% + (1% × 0.5) = 0.5% + 0.5% | 1% |

## Integration with Automation Systems

### Home Assistant Example

```yaml
# Get current volume
sensor:
  - platform: command_line
    name: system_volume
    command: 'C:\path\to\music_controller.ahk get-volume'
    scan_interval: 30

# Volume control services
shell_command:
  volume_up_10: 'C:\path\to\music_controller.ahv volume-up 10'
  volume_down_10: 'C:\path\to\music_controller.ahk volume-down 10'
  play_jazz: 'C:\path\to\music_controller.ahk play jazz'
  toggle_music: 'C:\path\to\music_controller.ahk toggle'
```

### PowerShell Integration

```powershell
# Get volume and store in variable
$volume = & "C:\path\to\music_controller.ahk" get-volume

# Conditional volume control
if ($volume -lt 50) {
    & "C:\path\to\music_controller.ahk" volume-up 20
}
```

### Batch File Integration

```batch
@echo off
REM Get current volume
for /f %%i in ('"C:\path\to\music_controller.ahv get-volume"') do set VOLUME=%%i

REM Play music if volume is adequate
if %VOLUME% GTR 10 (
    "C:\path\to\music_controller.ahk" play "ambient music"
)
```

## Error Handling

### Common Issues

1. **"YouTube Music not found"**
   - Run `play` command first to open YouTube Music
   - Ensure Brave browser is accessible

2. **No console output in PowerShell**
   - This is expected behavior with AutoHotkey v2
   - Output goes to stdout and can be captured by automation systems
   - Use redirection: `music_controller.ahk get-volume > output.txt`

3. **Browser automation fails**
   - Script includes multiple fallback methods
   - UIAutomation v2 provides robust element detection
   - Keyboard shortcuts used as last resort

### Exit Codes

- `0`: Success
- `1`: Error (with error message to stderr)

## Technical Details

### UIAutomation Features

- **Multi-method element detection**: Tries AutomationId, Name, Type combinations
- **Fallback mechanisms**: Keyboard shortcuts when UI elements aren't found
- **Robust error handling**: Graceful degradation with user feedback

### Volume Control Features

- **Relative calculations**: Percentage-based changes relative to current volume
- **Minimum protection**: Prevents volume from going below 1%
- **Dual output**: Both stdout (for automation) and human-readable messages

### Browser Management

- **Instance detection**: Checks for existing YouTube Music tabs
- **Auto-navigation**: Navigates to YouTube Music if not already there
- **Window management**: Activates and focuses browser windows appropriately

## Troubleshooting

### Debug Mode

Create a test script to verify functionality:

```autohotkey
#Requires AutoHotkey v2.0
; Test volume retrieval
try {
    vol := SoundGetVolume()
    FileAppend("Current volume: " . vol . "`n", "debug.txt")
} catch Error as e {
    FileAppend("Error: " . e.message . "`n", "debug.txt")
}
```

### Verification Commands

```bash
# Test basic functionality
music_controller.ahk get-volume

# Test volume changes
music_controller.ahv volume-up 1
music_controller.ahk get-volume
music_controller.ahk volume-down 1
```

## Version History

- **v2.0**: Added UIAutomation v2 support, relative volume control, stdout output
- **v1.0**: Basic music and volume control functionality

## License

This script is provided as-is for automation and personal use. 