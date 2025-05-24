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
        ; Try to find play/pause button using various selectors
        playPauseBtn := ""
        
        ; Method 1: Try common YouTube Music selectors
        try {
            playPauseBtn := cUIA.FindElement({AutomationId: "play-pause-button"})
        } catch {
            ; Method 2: Try aria-label attributes
            try {
                playPauseBtn := cUIA.FindElement({Name: "Play", Type: "Button"})
            } catch {
                try {
                    playPauseBtn := cUIA.FindElement({Name: "Pause", Type: "Button"})
                } catch {
                    ; Method 3: Try generic media controls
                    try {
                        playPauseBtn := cUIA.FindElement({Name: "Play (k)", Type: "Button"})
                    } catch {
                        try {
                            playPauseBtn := cUIA.FindElement({Name: "Pause (k)", Type: "Button"})
                        }
                    }
                }
            }
        }
        
        if (playPauseBtn) {
            playPauseBtn.Click()
            Echo("Toggled playback")
        } else {
            ; Fallback to keyboard shortcut
            cUIA.Send("{Space}")
            Echo("Toggled playback (keyboard fallback)")
        }
        
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
        Sleep(2000)
        
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
                Sleep(500)
                searchBox := cUIA.FindElement({Type: "Edit"})
            } catch {
                ; Method 3: Use keyboard shortcut to open search
                cUIA.Send("/")
                Sleep(500)
                ; Focus should now be on search box
            }
        }
        
        if (searchBox) {
            ; Clear existing content and type search term - Enhanced clearing
            searchBox.SetFocus()
            Sleep(200)
            
            ; Multiple clearing attempts to ensure empty search box
            searchBox.SetValue("")  ; Try direct clearing first
            Sleep(100)
            cUIA.Send("^a")  ; Select all
            Sleep(100)
            cUIA.Send("{Delete}")  ; Delete selected content
            Sleep(100)
            cUIA.Send("^a")  ; Select again in case anything remains
            Sleep(100)
            cUIA.Send("{Backspace}")  ; Backspace as additional clearing
            Sleep(200)
            
            ; Now enter the search term
            searchBox.SetValue(searchTerm)
            Sleep(500)
            
            ; Press Enter to search
            cUIA.Send("{Enter}")
        } else {
            ; Fallback: Use global search hotkey and type - Enhanced clearing
            cUIA.Send("/")
            Sleep(300)
            ; Multiple clearing attempts for keyboard fallback
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
            MsgBox("Debug: Found " . allButtons.Length . " total buttons on page", "Button Count", 0)
        } catch {
            MsgBox("Debug: Could not count buttons", "Error", 0)
        }
        
        ; Method 1: Look for Radio button (highest priority)
        radioButtons := ""
        try {
            radioButtons := cUIA.FindElements({Name: "Radio", Type: "Button"})
            MsgBox("Debug: Found " . radioButtons.Length . " Radio buttons", "Radio Button Search", 0)
            
            if (radioButtons.Length > 0) {
                Echo("Found Radio button - clicking...")
                MsgBox("About to click Radio button!", "Action", 0)
                radioButtons[1].Click()
                Sleep(1000)
                MsgBox("Radio button clicked! Check if music started.", "Result", 0)
                Echo("✅ Radio started successfully")
                return
            }
        } catch Error as e {
            MsgBox("Radio button search failed: " . e.message, "Radio Error", 0)
            Echo("Radio button not found")
        }
        
        ; Method 2: Look for Shuffle button (second priority)
        shuffleButtons := ""
        try {
            shuffleButtons := cUIA.FindElements({Name: "Shuffle", Type: "Button"})
            MsgBox("Debug: Found " . shuffleButtons.Length . " Shuffle buttons", "Shuffle Button Search", 0)
            
            if (shuffleButtons.Length > 0) {
                Echo("Found Shuffle button - clicking...")
                MsgBox("About to click Shuffle button!", "Action", 0)
                shuffleButtons[1].Click()
                Sleep(1000)
                MsgBox("Shuffle button clicked! Check if music started.", "Result", 0)
                Echo("✅ Shuffle started successfully")
                return
            }
        } catch Error as e {
            MsgBox("Shuffle button search failed: " . e.message, "Shuffle Error", 0)
            Echo("Shuffle button not found")
        }
        
        ; Method 3: Look for any Play button (third priority)
        playButtons := ""
        try {
            playButtons := cUIA.FindElements({Name: "Play", Type: "Button"})
            MsgBox("Debug: Found " . playButtons.Length . " Play buttons", "Play Button Search", 0)
            
            if (playButtons.Length > 0) {
                Echo("Found " . playButtons.Length . " Play buttons - clicking first one...")
                MsgBox("About to click first Play button!", "Action", 0)
                playButtons[1].Click()
                Sleep(1000)
                MsgBox("Play button clicked! Check if music started.", "Result", 0)
                Echo("✅ Play started successfully")
                return
            }
        } catch Error as e {
            MsgBox("Play button search failed: " . e.message, "Play Error", 0)
            Echo("Play buttons not found")
        }
        
        ; Method 4: Keyboard fallback
        Echo("Trying keyboard shortcuts...")
        MsgBox("No buttons found. Trying keyboard shortcut (Space).", "Fallback", 0)
        cUIA.Send("{Space}")  ; Space to play
        Sleep(1000)
        MsgBox("Keyboard shortcut attempted. Check if music started.", "Keyboard Result", 0)
        Echo("Keyboard shortcut attempted")
        
    } catch Error as e {
        MsgBox("Error in StartRadioUIA: " . e.message, "Fatal Error", 0)
        Echo("Error in StartRadioUIA: " . e.message)
        ; Final keyboard fallback
        try {
            cUIA.Send("{Enter}")
            Sleep(500)
            MsgBox("Emergency Enter key pressed.", "Emergency Fallback", 0)
            Echo("Emergency keyboard fallback used")
        } catch {
            MsgBox("All methods failed!", "Complete Failure", 0)
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
    Sleep(5000)  ; Wait for browser and page to load
    
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

MUSIC COMMANDS:
  play [genre]         - Open YouTube Music and play radio for genre
                        Default: 'chill music'
                        Examples: play jazz, play ""classical music""
  
  search <term>        - Search for music in YouTube Music
                        Example: search ""rock music""
  
  toggle               - Toggle play/pause current music

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
  music_controller.ahk search ""study music""
  music_controller.ahk toggle
  music_controller.ahk get-volume
  music_controller.ahk volume-up 50    (increase by 50% of current volume)
  music_controller.ahk volume-down 25  (decrease by 25% of current volume)
  music_controller.ahk mute

NOTES:
- This script uses UIAutomation v2 for robust browser interaction
- The script works with YouTube Music in Brave browser
- Music commands require internet connection
- The script will open YouTube Music automatically if needed
- Use quotes around multi-word search terms

IMPROVEMENTS OVER ORIGINAL:
- Uses UIAutomation v2 for reliable element detection
- Multiple fallback methods for robust interaction
- Better error handling and user feedback
- More reliable radio/shuffle start functionality
    )"
    
    Echo(helpText)
}

; ====================================================================
; SCRIPT EXECUTION
; ====================================================================

; Run main function
Main() 