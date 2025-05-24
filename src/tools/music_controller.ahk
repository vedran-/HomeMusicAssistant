#Requires AutoHotkey v2.0

; Include UIAutomation libraries
#include Lib\UIA.ahk
#include Lib\UIA_Browser.ahk

; Configuration Constants
BRAVE_PATH := "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
YOUTUBE_MUSIC_URL := "https://music.youtube.com"

; ====================================================================
; MAIN ENTRY POINT - Command Line Interface
; ====================================================================

Main() {
    if (A_Args.Length = 0) {
        ShowHelp()
        ExitApp()
    }
    
    command := A_Args[1]
    
    try {
        switch command {
            case "play":
                if (A_Args.Length >= 2) {
                    PlayMusic(A_Args[2])
                } else {
                    PlayMusic("chill music")
                }
            
            case "toggle":
                TogglePlayback()
            
            case "toggle-shuffle":
                ToggleShuffleMode()
            
            case "next":
                NextSong()
            
            case "previous", "prev":
                PreviousSong()
            
            case "forward":
                seconds := (A_Args.Length >= 2) ? Integer(A_Args[2]) : 10
                ForwardSeconds(seconds)
            
            case "back", "rewind":
                seconds := (A_Args.Length >= 2) ? Integer(A_Args[2]) : 10
                BackSeconds(seconds)
            
            case "like":
                LikeSong()
            
            case "dislike":
                DislikeSong()
            
            case "repeat":
                ToggleRepeat()
            
            case "search":
                if (A_Args.Length >= 2) {
                    SearchMusic(A_Args[2])
                } else {
                    throw Error("Search command requires a search term")
                }
            
            case "mute":
                SoundSetMute(true)
                Echo("System muted")
            
            case "unmute":
                SoundSetMute(false)
                Echo("System unmuted")
            
            case "volume-up":
                amount := (A_Args.Length >= 2) ? Integer(A_Args[2]) : 100
                AdjustVolume(amount)
            
            case "volume-down":
                amount := (A_Args.Length >= 2) ? Integer(A_Args[2]) : 50
                AdjustVolume(-amount)
            
            case "get-volume":
                GetVolume()
            
            case "help":
                ShowHelp()
            
            default:
                Echo("Unknown command: " . command)
                ShowHelp()
                ExitApp(1)
        }
    } catch Error as e {
        Echo("Error: " . e.message)
        ExitApp(1)
    }
}

; ====================================================================
; MUSIC CONTROL FUNCTIONS
; ====================================================================

; Play music by genre/term - opens YouTube Music and starts radio
PlayMusic(searchTerm) {
    Echo("Playing: " . searchTerm)
    
    ; Get or create YouTube Music browser instance
    cUIA := EnsureYouTubeMusicOpen()
    
    ; Search for the music
    SearchMusicUIA(cUIA, searchTerm)
    
    ; Start radio after search
    StartRadioUIA(cUIA)
}

; Toggle play/pause in current YouTube Music tab
TogglePlayback() {
    cUIA := GetYouTubeMusicBrowser()
    if (!cUIA) {
        throw Error("YouTube Music not found. Use 'play' command first.")
    }
    
    try {
        ; Find all Play/Pause buttons and use the last one (usually the main player control)
        playButtons := cUIA.FindElements({Name: "Play", Type: "Button"})
        pauseButtons := cUIA.FindElements({Name: "Pause", Type: "Button"})
        
        ;MsgBox("Debug: Found " . playButtons.Length . " Play buttons and " . pauseButtons.Length . " Pause buttons", "Toggle Debug", 0)
        
        ; Try Pause button first (if music is playing)
        if (pauseButtons.Length > 0) {
            lastPauseBtn := pauseButtons[pauseButtons.Length]
            ;MsgBox("About to click Pause button (last one found)!", "Toggle Action", 0)
            lastPauseBtn.Click()
            ;MsgBox("Pause button clicked!", "Toggle Result", 0)
            Echo("Music paused")
            return
        }
        
        ; If no Pause button, try Play button
        if (playButtons.Length > 0) {
            lastPlayBtn := playButtons[playButtons.Length]
            ;MsgBox("About to click Play button (last one found)!", "Toggle Action", 0)
            lastPlayBtn.Click()
            ;MsgBox("Play button clicked!", "Toggle Result", 0)
            Echo("Music resumed")
            return
        }
        
        ; Fallback to keyboard shortcut
        ;MsgBox("No Play/Pause buttons found. Using Space key fallback.", "Toggle Fallback", 0)
        cUIA.Send("{Space}")
        Echo("Toggled playback (keyboard fallback)")
        
    } catch Error as e {
        Echo("Error toggling playback: " . e.message . " - Using keyboard fallback")
        try {
            cUIA.Send("{Space}")
            Echo("Toggled playback (keyboard fallback)")
        } catch {
            throw Error("Failed to toggle playback")
        }
    }
}

; Search for music in YouTube Music using UIAutomation
SearchMusicUIA(cUIA, searchTerm) {
    Echo("Searching for: " . searchTerm)
    
    try {
        ; Wait for page to load completely
        Sleep(200)
        
        ; Method 1: Try to find search box by common selectors
        searchBox := ""
        try {
            searchBox := cUIA.FindElement({AutomationId: "input", Type: "Edit"})
        } catch {
            try {
                searchBox := cUIA.FindElement({Name: "Search", Type: "Edit"})
            } catch {
                try {
                    searchBox := cUIA.FindElement({Name: "Search YouTube Music", Type: "Edit"})
                } catch {
                    ; Try finding by placeholder text
                    try {
                        searchBox := cUIA.FindElement({Type: "Edit", matchMode: 2, Name: "Search"})
                    }
                }
            }
        }
        
        if (!searchBox) {
            ; Method 2: Try clicking search icon first
            try {
                searchIcon := cUIA.FindElement({Name: "Search", Type: "Button"})
                searchIcon.Click()
                Sleep(200)
                searchBox := cUIA.FindElement({Type: "Edit"})
            } catch {
                ; Method 3: Use keyboard shortcut to open search
                cUIA.Send("/")
                Sleep(200)
                ; Focus should now be on search box
            }
        }
        
        if (searchBox) {
            ; Clear existing content and type search term - Enhanced clearing
            searchBox.SetFocus()
            Sleep(100)
            
            ; Multiple clearing attempts to ensure empty search box
            searchBox.SetValue("")  ; Try direct clearing first
            Sleep(50)
            cUIA.Send("^a")  ; Select all
            Sleep(50)
            cUIA.Send("{Delete}")  ; Delete selected content
            Sleep(50)
            cUIA.Send("^a")  ; Select again in case anything remains
            Sleep(50)
            cUIA.Send("{Backspace}")  ; Backspace as additional clearing
            Sleep(50)
            
            ; Now enter the search term
            searchBox.SetValue(searchTerm)
            Sleep(200)
            
            ; Press Enter to search
            cUIA.Send("{Enter}")
        } else {
            ; Fallback: Use global search hotkey and type - Enhanced clearing
            cUIA.Send("/")
            Sleep(200)
            ; Multiple clearing attempts for keyboard fallback
            cUIA.Send("^a")  ; Select all
            Sleep(50)
            cUIA.Send("{Delete}")  ; Delete
            Sleep(50)
            cUIA.Send("^a")  ; Select all again
            Sleep(50)
            cUIA.Send("{Backspace}")  ; Backspace
            Sleep(50)
            cUIA.Send(searchTerm)
            Sleep(200)
            cUIA.Send("{Enter}")
        }
        
        ; Wait for search results
        Sleep(2000)
        
    } catch Error as e {
        Echo("Search error: " . e.message . " - Using keyboard fallback")
        ; Fallback to original keyboard method with enhanced clearing
        cUIA.Send("/")
        Sleep(300)
        ; Enhanced clearing for error fallback
        cUIA.Send("^a")  ; Select all
        Sleep(100)
        cUIA.Send("{Delete}")  ; Delete
        Sleep(100)
        cUIA.Send("^a")  ; Select all again  
        Sleep(100)
        cUIA.Send("{Backspace}")  ; Backspace
        Sleep(100)
        cUIA.Send(searchTerm)
        Sleep(300)
        cUIA.Send("{Enter}")
        Sleep(1500)
    }
}

; Start playing radio after search results are loaded using UIAutomation
StartRadioUIA(cUIA) {
    Echo("Starting radio...")
    
    try {
        ; Wait for search results to load
        Sleep(2000)
        
        ; Debug: Show total button count
        try {
            allButtons := cUIA.FindElements({Type: "Button"})
            ;MsgBox("Debug: Found " . allButtons.Length . " total buttons on page", "Button Count", 0)
        } catch {
            ;MsgBox("Debug: Could not count buttons", "Error", 0)
        }
        
        ; Method 1: Look for Radio button (highest priority)
        radioButtons := ""
        try {
            radioButtons := cUIA.FindElements({Name: "Radio", Type: "Button"})
            ;MsgBox("Debug: Found " . radioButtons.Length . " Radio buttons", "Radio Button Search", 0)
            
            if (radioButtons.Length > 0) {
                Echo("Found Radio button - clicking...")
                ;MsgBox("About to click Radio button!", "Action", 0)
                radioButtons[1].Click()
                Sleep(1000)
                ;MsgBox("Radio button clicked! Check if music started.", "Result", 0)
                Echo("✅ Radio started successfully")
                return
            }
        } catch Error as e {
            ;MsgBox("Radio button search failed: " . e.message, "Radio Error", 0)
            Echo("Radio button not found")
        }
        
        
        ; Method 2: Look for any Play button (second priority)
        playButtons := ""
        try {
            playButtons := cUIA.FindElements({Name: "Play", Type: "Button"})
            ;MsgBox("Debug: Found " . playButtons.Length . " Play buttons", "Play Button Search", 0)
            
            if (playButtons.Length > 0) {
                Echo("Found " . playButtons.Length . " Play buttons - clicking first one...")
                ;MsgBox("About to click first Play button!", "Action", 0)
                playButtons[playButtons.Length].Click()
                Sleep(1000)
                ;MsgBox("Play button clicked! Check if music started.", "Result", 0)
                Echo("✅ Play started successfully")
                return
            }
        } catch Error as e {
            ;MsgBox("Play button search failed: " . e.message, "Play Error", 0)
            Echo("Play buttons not found")
        }
        
        ; Method 3: Keyboard fallback
        Echo("Trying keyboard shortcuts...")
        ;MsgBox("No buttons found. Trying keyboard shortcut (Space).", "Fallback", 0)
        cUIA.Send("{Space}")  ; Space to play
        Sleep(1000)
        ;MsgBox("Keyboard shortcut attempted. Check if music started.", "Keyboard Result", 0)
        Echo("Keyboard shortcut attempted")
        
    } catch Error as e {
        ;MsgBox("Error in StartRadioUIA: " . e.message, "Fatal Error", 0)
        Echo("Error in StartRadioUIA: " . e.message)
        ; Final keyboard fallback
        try {
            cUIA.Send("{Enter}")
            Sleep(500)
            ;MsgBox("Emergency Enter key pressed.", "Emergency Fallback", 0)
            Echo("Emergency keyboard fallback used")
        } catch {
            ;MsgBox("All methods failed!", "Complete Failure", 0)
            Echo("All methods failed")
        }
    }
}

; Search for music in YouTube Music (legacy function)
SearchMusic(searchTerm) {
    cUIA := GetYouTubeMusicBrowser()
    if (!cUIA) {
        EnsureYouTubeMusicOpen()
        Sleep(3000)
        cUIA := GetYouTubeMusicBrowser()
    }
    
    if (cUIA) {
        SearchMusicUIA(cUIA, searchTerm)
    } else {
        throw Error("Could not access YouTube Music")
    }
}

; ====================================================================
; SYSTEM VOLUME FUNCTIONS
; ====================================================================

; Get current system volume and print to stdout
GetVolume() {
    currentVolume := SoundGetVolume()
    volumeValue := Round(currentVolume)
    
    ; Use cmd echo for simple, reliable output
    RunWait('cmd /c echo ' . volumeValue, , "")
}

; Adjust system volume by relative percentage
AdjustVolume(percentage) {
    try {
        currentVolume := SoundGetVolume()
        
        ; Use minimum 1% for calculation base if current volume is lower
        calculationBase := Max(currentVolume, 1)
        
        ; Calculate the change amount based on percentage of calculation base
        changeAmount := calculationBase * (percentage / 100)
        
        ; Apply change to actual current volume
        newVolume := currentVolume + changeAmount
        
        ; Clamp between 1 and 100 (1% absolute minimum)
        if (newVolume > 100) {
            newVolume := 100
        } else if (newVolume < 1) {
            newVolume := 1
        }
        
        SoundSetVolume(newVolume)
        
        ; Output new volume to stdout for automation systems
        RunWait('cmd /c echo ' . Round(newVolume), , "")
        
        ; Also echo human-readable message
        Echo("Volume: " . Round(newVolume) . "% (changed by " . Round(changeAmount, 1) . "%)")
        
    } catch Error as e {
        throw Error("Failed to adjust volume: " . e.message)
    }
}

; ====================================================================
; BROWSER MANAGEMENT FUNCTIONS
; ====================================================================

; Ensure YouTube Music is open and return UIA_Browser instance
EnsureYouTubeMusicOpen() {
    ; Try to get existing browser first
    cUIA := GetYouTubeMusicBrowser()
    if (cUIA) {
        return cUIA
    }
    
    Echo("Opening YouTube Music...")
    
    ; Open Brave with YouTube Music URL
    Run(BRAVE_PATH . " " . YOUTUBE_MUSIC_URL)
    Sleep(500)  ; Wait for browser and page to load
    
    ; Wait for browser window to be available
    WinWait("ahk_exe brave.exe", , 10)
    WinActivate("ahk_exe brave.exe")
    
    ; Create UIA_Browser instance for the new window
    try {
        cUIA := UIA_Browser("ahk_exe brave.exe")
        Sleep(2000)  ; Additional wait for page content to load
        return cUIA
    } catch Error as e {
        throw Error("Failed to initialize browser automation: " . e.message)
    }
}

; Get existing YouTube Music browser instance
GetYouTubeMusicBrowser() {
    try {
        ; Check if Brave is running
        if (!WinExist("ahk_exe brave.exe")) {
            return false
        }
        
        ; Try to create UIA_Browser instance
        cUIA := UIA_Browser("ahk_exe brave.exe")
        
        ; Check if we're on YouTube Music by checking URL or title
        try {
            currentUrl := cUIA.GetCurrentURL()
            if (InStr(currentUrl, "music.youtube.com")) {
                return cUIA
            }
        } catch {
            ; Try checking window title instead
            winTitle := WinGetTitle("ahk_exe brave.exe")
            if (InStr(winTitle, "YouTube Music")) {
                return cUIA
            }
        }
        
        ; If not on YouTube Music, try to navigate to it
        try {
            cUIA.Navigate(YOUTUBE_MUSIC_URL)
            Sleep(3000)
            return cUIA
        } catch {
            return false
        }
        
    } catch {
        return false
    }
}

; ====================================================================
; UTILITY FUNCTIONS
; ====================================================================

; Echo message to stdout (visible when run from command line)
Echo(message) {
    try {
        ; Method 1: Try direct FileAppend to stdout
        FileAppend(message . "`n", "*")
    } catch {
        ; Method 2: Use cmd to echo the message directly to console
        RunWait('cmd /c echo ' . message, , "")
    }
}

; Show help information
ShowHelp() {
    helpText := "
    (
YouTube Music & System Control Script (UIAutomation Enhanced)

USAGE:
  music_controller.ahk <command> [parameters]

MUSIC PLAYBACK COMMANDS:
  play [genre]         - Open YouTube Music and play radio for genre
                        Default: 'chill music'
                        Examples: play jazz, play ""classical music""
  
  toggle               - Toggle play/pause current music (uses last Play/Pause button)
  
  next                 - Play next song (Shift+N)
  
  previous, prev       - Play previous song (Shift+P)
  
  forward [seconds]    - Forward by seconds (default: 10)
                        Uses 10s + 1s increments (e.g., 32s = 3x10s + 2x1s)
                        Examples: forward 30, forward 5
  
  back [seconds]       - Go back by seconds (default: 10)  
  rewind [seconds]     - Same as back
                        Examples: back 15, rewind 45
  
  like                 - Like current song (+)
  
  dislike              - Dislike current song (-)
  
  repeat               - Toggle repeat mode (R)
  
  toggle-shuffle       - Toggle shuffle mode on/off (uses last Shuffle button)

MUSIC SEARCH COMMANDS:
  search <term>        - Search for music in YouTube Music
                        Example: search ""rock music""

SYSTEM VOLUME COMMANDS:
  mute                 - Mute system audio
  unmute               - Unmute system audio
  get-volume           - Get current system volume percentage
  volume-up [percent]  - Increase volume by percentage of current volume (default: 10%)
  volume-down [percent]- Decrease volume by percentage of current volume (default: 10%)

OTHER COMMANDS:
  help                 - Show this help

EXAMPLES:
  music_controller.ahk play jazz
  music_controller.ahk next
  music_controller.ahk forward 32
  music_controller.ahk back 15
  music_controller.ahk like
  music_controller.ahk toggle-shuffle
  music_controller.ahk repeat

NOTES:
- This script uses UIAutomation v2 for robust browser interaction
- The script works with YouTube Music in Brave browser
- Music commands require internet connection and YouTube Music to be open
- Keyboard shortcuts ensure search box focus is cleared before sending commands
- Time increments use YouTube Music's native 10s and 1s forward/back shortcuts
- Use quotes around multi-word search terms for play command

KEYBOARD SHORTCUTS USED:
- Play/Pause: Space
- Next: Shift+N  
- Previous: Shift+P
- Forward 10s: L, Forward 1s: Shift+L
- Back 10s: H, Back 1s: Shift+H
- Like: +, Dislike: -
- Repeat: R, Shuffle: S (via button click)
    )"
    
    Echo(helpText)
}

; ====================================================================
; SCRIPT EXECUTION
; ====================================================================

; Run main function
Main()

; Toggle shuffle mode in current YouTube Music
ToggleShuffleMode() {
    cUIA := GetYouTubeMusicBrowser()
    if (!cUIA) {
        throw Error("YouTube Music not found. Use 'play' command first.")
    }
    
    try {
        ; Find all Shuffle buttons and use the last one (usually the player control)
        shuffleButtons := cUIA.FindElements({Name: "Shuffle", Type: "Button"})
        ;MsgBox("Debug: Found " . shuffleButtons.Length . " Shuffle buttons for toggle", "Toggle Shuffle Debug", 0)
        
        if (shuffleButtons.Length > 0) {
            ; Use the last shuffle button (typically the player control)
            lastShuffleBtn := shuffleButtons[shuffleButtons.Length]
            ;MsgBox("About to toggle shuffle mode using last Shuffle button!", "Toggle Shuffle Action", 0)
            lastShuffleBtn.Click()
            ;MsgBox("Shuffle mode toggled! Check the player.", "Toggle Shuffle Result", 0)
            Echo("Shuffle mode toggled")
        } else {
            throw Error("No Shuffle buttons found")
        }
        
    } catch Error as e {
        Echo("Error toggling shuffle mode: " . e.message)
        throw Error("Failed to toggle shuffle mode")
    }
}

; Ensure focus is on the main player area, not search box
EnsurePlayerFocus(cUIA) {
    try {
        ; Try to click on main content area to remove focus from search box
        try {
            ; Look for main content or player area
            mainContent := cUIA.FindElement({Type: "Main"})
            if (mainContent) {
                mainContent.Click()
                Sleep(200)
                return
            }
        } catch {
            ; Fallback: click on a safe area of the page
            try {
                cUIA.Send("{Esc}")  ; Escape key often removes focus from search
                Sleep(200)
            } catch {
                ; Final fallback: click at a safe coordinate
                WinActivate("ahk_exe brave.exe")
                Sleep(200)
            }
        }
    } catch {
        Echo("Warning: Could not ensure player focus")
    }
}

; Play next song
NextSong() {
    cUIA := GetYouTubeMusicBrowser()
    if (!cUIA) {
        throw Error("YouTube Music not found. Use 'play' command first.")
    }
    
    try {
        EnsurePlayerFocus(cUIA)
        ;MsgBox("Sending next song command (Shift+N)", "Next Song", 0)
        cUIA.Send("+n")  ; Shift+N
        Echo("Next song command sent")
    } catch Error as e {
        Echo("Error playing next song: " . e.message)
        throw Error("Failed to play next song")
    }
}

; Play previous song
PreviousSong() {
    cUIA := GetYouTubeMusicBrowser()
    if (!cUIA) {
        throw Error("YouTube Music not found. Use 'play' command first.")
    }
    
    try {
        EnsurePlayerFocus(cUIA)
        ;MsgBox("Sending previous song command (Shift+P)", "Previous Song", 0)
        cUIA.Send("+p")  ; Shift+P
        Echo("Previous song command sent")
    } catch Error as e {
        Echo("Error playing previous song: " . e.message)
        throw Error("Failed to play previous song")
    }
}

; Forward by specified seconds (using 10s and 1s increments)
ForwardSeconds(seconds) {
    cUIA := GetYouTubeMusicBrowser()
    if (!cUIA) {
        throw Error("YouTube Music not found. Use 'play' command first.")
    }
    
    try {
        EnsurePlayerFocus(cUIA)
        
        ; Calculate 10s and 1s increments
        tens := seconds // 10
        ones := seconds - (tens * 10)
        
        ;MsgBox("Forwarding " . seconds . " seconds (" . tens . "x10s + " . ones . "x1s)", "Forward", 0)
        
        ; Send 10-second forwards (l key)
        Loop tens {
            cUIA.Send("l")
            Sleep(100)
        }
        
        ; Send 1-second forwards (Shift+l)
        Loop ones {
            cUIA.Send("+l")
            Sleep(100)
        }
        
        Echo("Forwarded " . seconds . " seconds")
    } catch Error as e {
        Echo("Error forwarding: " . e.message)
        throw Error("Failed to forward")
    }
}

; Back by specified seconds (using 10s and 1s increments)
BackSeconds(seconds) {
    cUIA := GetYouTubeMusicBrowser()
    if (!cUIA) {
        throw Error("YouTube Music not found. Use 'play' command first.")
    }
    
    try {
        EnsurePlayerFocus(cUIA)
        
        ; Calculate 10s and 1s increments
        tens := seconds // 10
        ones := seconds - (tens * 10)
        
        ;MsgBox("Going back " . seconds . " seconds (" . tens . "x10s + " . ones . "x1s)", "Back", 0)
        
        ; Send 10-second backs (h key)
        Loop tens {
            cUIA.Send("h")
            Sleep(100)
        }
        
        ; Send 1-second backs (Shift+h)
        Loop ones {
            cUIA.Send("+h")
            Sleep(100)
        }
        
        Echo("Went back " . seconds . " seconds")
    } catch Error as e {
        Echo("Error going back: " . e.message)
        throw Error("Failed to go back")
    }
}

; Like current song
LikeSong() {
    cUIA := GetYouTubeMusicBrowser()
    if (!cUIA) {
        throw Error("YouTube Music not found. Use 'play' command first.")
    }
    
    try {
        EnsurePlayerFocus(cUIA)
        ;MsgBox("Liking current song (+)", "Like Song", 0)
        cUIA.Send("{+}")  ; Plus key
        Echo("Song liked")
    } catch Error as e {
        Echo("Error liking song: " . e.message)
        throw Error("Failed to like song")
    }
}

; Dislike current song
DislikeSong() {
    cUIA := GetYouTubeMusicBrowser()
    if (!cUIA) {
        throw Error("YouTube Music not found. Use 'play' command first.")
    }
    
    try {
        EnsurePlayerFocus(cUIA)
        ;MsgBox("Disliking current song (-)", "Dislike Song", 0)
        cUIA.Send("{-}")  ; Minus key
        Echo("Song disliked")
    } catch Error as e {
        Echo("Error disliking song: " . e.message)
        throw Error("Failed to dislike song")
    }
}

; Toggle repeat mode
ToggleRepeat() {
    cUIA := GetYouTubeMusicBrowser()
    if (!cUIA) {
        throw Error("YouTube Music not found. Use 'play' command first.")
    }
    
    try {
        EnsurePlayerFocus(cUIA)
        ;MsgBox("Toggling repeat mode (R)", "Toggle Repeat", 0)
        cUIA.Send("r")  ; R key
        Echo("Repeat mode toggled")
    } catch Error as e {
        Echo("Error toggling repeat: " . e.message)
        throw Error("Failed to toggle repeat")
    }
} 