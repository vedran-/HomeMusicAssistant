# YouTube Music Controller Documentation

## Overview

The YouTube Music Controller is a powerful AutoHotkey-based tool that provides comprehensive voice and command-line control over YouTube Music. It uses UIAutomation v2 for reliable browser interaction and supports a full range of playback controls, search functionality, and system volume management.

## Features

- **🎵 Music Playback Control**: Play, pause, next, previous, shuffle, repeat
- **⏩ Time Navigation**: Forward/back by custom increments with smart 10s+1s calculation
- **🔍 Search Integration**: Search and play music by genre, artist, or song
- **👍 Song Feedback**: Like/dislike current songs
- **🔊 Volume Control**: System volume management with relative adjustments
- **🎯 Smart Focus Management**: Prevents keyboard shortcuts from interfering with search box
- **🐛 Visual Debugging**: Message box popups for real-time feedback
- **🔄 Multiple Button Detection**: Prioritizes correct buttons (player controls vs search results)

## Requirements

### Software Dependencies
- **Windows 10/11**
- **AutoHotkey v2.0** (installed at `C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe`)
- **Brave Browser** (configured for YouTube Music)
- **UIAutomation v2 Libraries** (included in `src/tools/Lib/`)

### Setup Requirements
- YouTube Music account and active session
- Internet connection
- Brave browser configured as default for YouTube Music
- UIAutomation libraries properly installed

## Installation

The music controller is part of the Home Assistant Voice Control System. Ensure the following files are in place:

```
src/tools/
├── music_controller.ahk          # Main controller script
├── Lib/
│   ├── UIA.ahk                  # UIAutomation library
│   └── UIA_Browser.ahk          # Browser-specific UIA functions
└── registry.py                  # Python integration
```

## Command Reference

### Music Playback Commands

#### `play [search_term]`
Searches for and plays music on YouTube Music.

**Examples:**
```bash
music_controller.ahk play                    # Plays "chill music" (default)
music_controller.ahk play jazz               # Searches and plays jazz music
music_controller.ahk play "classical music"  # Multi-word searches need quotes
music_controller.ahk play "Boards of Canada" # Search for specific artists
```

**Behavior:**
1. Opens YouTube Music if not already open
2. Searches for the specified term
3. Prioritizes: Radio buttons → Play buttons (last found)
4. Shows debug popups indicating button counts and actions

#### `toggle`
Toggles play/pause of currently playing music.

**Examples:**
```bash
music_controller.ahk toggle
```

**Behavior:**
- Finds all Play/Pause buttons and uses the last one (main player controls)
- Prioritizes Pause button (if music is playing) over Play button
- Falls back to Space key if no buttons found
- Shows button counts in debug popup

#### `next [count]`
Plays the next song(s) in the current playlist/queue. Supports skipping multiple songs at once.

**Examples:**
```bash
music_controller.ahk next         # Next 1 song (default)
music_controller.ahk next 3       # Skip next 3 songs
music_controller.ahk next 5       # Skip next 5 songs
```

**Technical:** Uses `Shift+N` keyboard shortcut or Next button clicking, repeated for the specified count.

#### `previous [count]` / `prev [count]`
Plays the previous song(s) in the current playlist/queue. Supports going back multiple songs with asymmetric behavior handling.

**Examples:**
```bash
music_controller.ahk previous     # Previous 1 song (default)
music_controller.ahk prev 2       # Go back 2 songs  
music_controller.ahk previous 4   # Go back 4 songs
```

**Technical:** Uses `Shift+P` keyboard shortcut or Previous button clicking. **Note:** Due to YouTube Music's behavior, going back N songs requires N+1 button presses (first press rewinds current song to start, subsequent presses go to previous songs).

### Time Navigation Commands

#### `forward [seconds]`
Fast-forwards by the specified number of seconds (default: 10).

**Examples:**
```bash
music_controller.ahk forward         # Forward 10 seconds
music_controller.ahk forward 30      # Forward 30 seconds  
music_controller.ahk forward 32      # Forward 32 seconds (3×10s + 2×1s)
music_controller.ahk forward 5       # Forward 5 seconds (5×1s)
```

**Smart Increment Logic:**
- Automatically calculates optimal combination of 10-second and 1-second increments
- `32 seconds` = 3 presses of `L` (10s each) + 2 presses of `Shift+L` (1s each)
- Shows calculation in debug popup: "32 seconds (3x10s + 2x1s)"

#### `back [seconds]` / `rewind [seconds]`
Goes back by the specified number of seconds (default: 10).

**Examples:**
```bash
music_controller.ahk back 15         # Go back 15 seconds
music_controller.ahk rewind 45       # Go back 45 seconds (4×10s + 5×1s)
```

**Smart Increment Logic:**
- Uses `H` key for 10-second decrements
- Uses `Shift+H` for 1-second decrements
- Same smart calculation as forward command

### Mode Control Commands

#### `toggle-shuffle`
Toggles shuffle mode on/off.

**Examples:**
```bash
music_controller.ahk toggle-shuffle
```

**Behavior:**
- Finds all Shuffle buttons and uses the last one (player control, not playlist starter)
- Shows count of Shuffle buttons found
- Confirms action with debug popup

#### `repeat`
Toggles repeat mode (off/all/one).

**Examples:**
```bash
music_controller.ahk repeat
```

**Technical:** Sends `R` keyboard shortcut

### Song Feedback Commands

#### `like`
Likes the currently playing song.

**Examples:**
```bash
music_controller.ahk like
```

**Technical:** Sends `+` (plus) key

#### `dislike`
Dislikes the currently playing song.

**Examples:**
```bash
music_controller.ahk dislike
```

**Technical:** Sends `-` (minus) key

### Search Commands

#### `search <term>`
Searches for music without automatically playing.

**Examples:**
```bash
music_controller.ahk search "electronic music"
music_controller.ahk search beethoven
```

### System Volume Commands

#### `volume-up [percentage]`
Increases system volume by the specified percentage of current volume.

**Examples:**
```bash
music_controller.ahk volume-up        # Increase by 100% of current (default)
music_controller.ahk volume-up 50     # Increase by 50% of current volume
```

#### `volume-down [percentage]`
Decreases system volume by the specified percentage of current volume.

**Examples:**
```bash
music_controller.ahk volume-down      # Decrease by 50% of current (default)
music_controller.ahk volume-down 25   # Decrease by 25% of current volume
```

#### `mute` / `unmute`
Mutes or unmutes system audio.

**Examples:**
```bash
music_controller.ahk mute
music_controller.ahk unmute
```

#### `get-volume`
Returns the current system volume percentage.

**Examples:**
```bash
music_controller.ahk get-volume       # Returns: 75
```

### Utility Commands

#### `help`
Shows comprehensive help information.

**Examples:**
```bash
music_controller.ahk help
```

## Voice Integration

The music controller integrates with the Home Assistant Voice Control System. Voice commands are processed through the LLM and mapped to appropriate tool calls:

**Basic Playback (`play_music` tool)**:
- *"Play some jazz music"* → `play_music` with `action: "play"`, `search_term: "jazz"`
- *"Play Boards of Canada"* → `play_music` with `action: "play"`, `search_term: "Boards of Canada"`
- *"Pause the music"* → `play_music` with `action: "pause"`
- *"Next song"* → `play_music` with `action: "next"`
- *"Skip next 3 songs"* → `play_music` with `action: "next"`, `count: 3`
- *"Previous song"* → `play_music` with `action: "previous"`
- *"Go back 2 songs"* → `play_music` with `action: "previous"`, `count: 2`

**Advanced Controls (`music_control` tool)**:
- *"Go forward 30 seconds"* → `music_control` with `action: "forward"`, `amount: 30`
- *"Go back 15 seconds"* → `music_control` with `action: "back"`, `amount: 15`
- *"Like this song"* → `music_control` with `action: "like"`
- *"Dislike this song"* → `music_control` with `action: "dislike"`
- *"Turn on shuffle"* → `music_control` with `action: "shuffle"`
- *"Toggle repeat mode"* → `music_control` with `action: "repeat"`
- *"Search for electronic music"* → `music_control` with `action: "search"`, `search_term: "electronic music"`

**Volume Control (`control_volume` tool)**:
- *"Turn up the volume"* → `control_volume` with `action: "up"`
- *"Turn down the volume"* → `control_volume` with `action: "down"`
- *"Mute the sound"* → `control_volume` with `action: "mute"`

## Technical Details

### Focus Management
The controller includes smart focus management to prevent keyboard shortcuts from being typed into the search box:

```autohotkey
EnsurePlayerFocus(cUIA) {
    # 1. Try clicking main content area
    # 2. Send Escape key to clear focus  
    # 3. Activate window as fallback
}
```

This function is called before sending any keyboard shortcuts.

### Button Priority Logic

#### Play Command Priority:
1. **Radio buttons** (highest priority - starts radio for search term)
2. **Play buttons** (uses last found - typically main player controls)
3. **Keyboard shortcuts** (Space key fallback)

#### Toggle Command Priority:
1. **Pause buttons** (if music is playing)
2. **Play buttons** (if music is paused)
3. **Keyboard shortcuts** (Space key fallback)

### Debug Mode
All commands include visual debugging with message boxes that show:
- Button counts found (e.g., "Found 3 Play buttons")
- Action confirmations (e.g., "About to click Play button!")
- Result confirmations (e.g., "Play button clicked!")
- Error messages with specific details

### Browser Integration
- **Target Browser**: Brave (`ahk_exe brave.exe`)
- **Target URL**: `https://music.youtube.com`
- **Auto-launch**: Opens YouTube Music automatically if not running
- **Window Management**: Activates and focuses browser window

## Troubleshooting

### Common Issues

#### "YouTube Music not found" Error
**Cause:** Brave browser not running or not on YouTube Music page  
**Solution:** 
1. Ensure Brave browser is installed
2. Run a `play` command to auto-launch YouTube Music
3. Manually navigate to music.youtube.com

#### Keyboard Shortcuts Not Working
**Cause:** Search box has focus, preventing shortcuts from reaching player  
**Solution:** 
- The controller automatically handles this with `EnsurePlayerFocus()`
- If issues persist, manually click in the main content area
- Try the command again

#### No Buttons Found
**Cause:** Page not fully loaded or UIAutomation detection issues  
**Solution:**
1. Wait for page to fully load (2-3 seconds)
2. Try the command again
3. Check debug popups for button counts
4. Use keyboard fallback methods (automatically attempted)

#### Volume Commands Not Working
**Cause:** System volume API issues or permissions  
**Solution:**
1. Run as administrator if needed
2. Check Windows audio system is working
3. Try Windows volume controls manually

### Debug Information

Enable debug mode by noting the message box popups during command execution:

1. **Button Count Popup**: Shows total buttons found on page
2. **Search Popups**: Show button counts for specific types (Radio, Shuffle, Play)
3. **Action Popups**: Confirm which button will be clicked
4. **Result Popups**: Confirm action was attempted

### Performance Optimization

- **Sleep Timings**: Adjust `Sleep()` values in script if your system is slower
- **Page Load Wait**: Increase initial wait time for slower internet connections
- **Button Detection**: Multiple detection methods provide robustness

## Advanced Usage

### Custom Time Increments
The time navigation system supports any increment and automatically optimizes:

```bash
# Complex examples:
music_controller.ahk forward 73    # 7×10s + 3×1s = 73 seconds
music_controller.ahk back 156      # 15×10s + 6×1s = 156 seconds  
```

### Batch Operations
Chain commands for complex operations:

```bash
# Like current song and skip to next
music_controller.ahk like
music_controller.ahk next

# Go back to beginning and set repeat mode
music_controller.ahk back 300
music_controller.ahk repeat
```

### Integration Examples

#### PowerShell Script
```powershell
# PowerShell wrapper for common operations
function Play-Music {
    param($Genre = "chill music")
    & "C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe" "src\tools\music_controller.ahk" "play" $Genre
}

function Next-Song {
    & "C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe" "src\tools\music_controller.ahk" "next"
}
```

#### Python Integration
```python
# Python integration (used by voice control system)
from src.tools.registry import ToolRegistry

registry = ToolRegistry(autohotkey_path, scripts_dir)
result = registry.execute_tool("play_music", {"search_term": "jazz music"})
```

## Keyboard Shortcuts Reference

| Action | Primary Key | Alternative | Notes |
|--------|-------------|-------------|-------|
| Play/Pause | `Space` | `;` | Global YouTube Music shortcut |
| Next Song | `Shift+N` | `j` | Controller uses Shift+N |
| Previous Song | `Shift+P` | `k` | Controller uses Shift+P |
| Forward 10s | `L` | `Shift+→` | Used by increment system |
| Back 10s | `H` | `Shift+←` | Used by increment system |
| Forward 1s | `Shift+L` | `Ctrl+Shift+→` | Fine control |
| Back 1s | `Shift+H` | `Ctrl+Shift+←` | Fine control |
| Like Song | `+` | - | Thumbs up |
| Dislike Song | `-` | - | Thumbs down |
| Shuffle | `S` | - | Via button click |
| Repeat | `R` | - | Cycles through modes |

## Version History

- **v1.0**: Basic play/pause/volume control
- **v2.0**: Added UIAutomation support and button detection
- **v3.0**: Enhanced debugging and focus management
- **v4.0**: Added comprehensive playback controls (next/prev/forward/back)
- **v4.1**: Smart time increment calculation and song feedback
- **v4.2**: Improved button priority logic and toggle commands

## Support

For issues or feature requests:
1. Check this documentation
2. Review debug popup messages
3. Test commands manually with message boxes
4. Check AutoHotkey v2 installation
5. Verify Brave browser and YouTube Music access

---
*Part of the Home Assistant Voice Control System - Advanced Music Control Module* 