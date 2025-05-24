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
                amount := (A_Args.Length >= 2) ? Integer(A_Args[2]) : 10
                AdjustVolume(amount)
            
            case "volume-down":
                amount := (A_Args.Length >= 2) ? Integer(A_Args[2]) : 10
                AdjustVolume(-amount)
            
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
            ; Clear existing content and type search term
            searchBox.SetFocus()
            Sleep(200)
            searchBox.SetValue("")
            Sleep(200)
            searchBox.SetValue(searchTerm)
            Sleep(500)
            
            ; Press Enter to search
            cUIA.Send("{Enter}")
        } else {
            ; Fallback: Use global search hotkey and type
            cUIA.Send("/")
            Sleep(300)
            cUIA.Send("^a")  ; Select all
            Sleep(100)
            cUIA.Send(searchTerm)
            Sleep(300)
            cUIA.Send("{Enter}")
        }
        
        ; Wait for search results
        Sleep(2000)
        
    } catch Error as e {
        Echo("Search error: " . e.message . " - Using keyboard fallback")
        ; Fallback to original keyboard method
        cUIA.Send("/")
        Sleep(300)
        cUIA.Send("^a")
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
        Sleep(1500)
        
        ; Method 1: Look for "Start Radio" button
        radioBtn := ""
        try {
            radioBtn := cUIA.FindElement({Name: "Start radio", Type: "Button"})
        } catch {
            try {
                radioBtn := cUIA.FindElement({Name: "Radio", Type: "Button"})
            } catch {
                try {
                    radioBtn := cUIA.FindElement({Name: "Start Radio", Type: "Button"})
                } catch {
                    ; Try finding shuffle button
                    try {
                        radioBtn := cUIA.FindElement({Name: "Shuffle", Type: "Button"})
                    } catch {
                        try {
                            radioBtn := cUIA.FindElement({Name: "Shuffle play", Type: "Button"})
                        }
                    }
                }
            }
        }
        
        if (radioBtn) {
            radioBtn.Click()
            Echo("Radio started successfully")
            return
        }
        
        ; Method 2: Look for play buttons on search results
        try {
            playButtons := cUIA.FindElements({Name: "Play", Type: "Button"})
            if (playButtons.Length > 0) {
                ; Click the first play button found
                playButtons[1].Click()
                Echo("Started playing first result")
                return
            }
        }
        
        ; Method 3: Try to find and click first song/album in results
        try {
            ; Look for clickable music items
            musicItems := cUIA.FindElements({Type: "ListItem"})
            if (musicItems.Length > 0) {
                musicItems[1].Click()
                Sleep(500)
                
                ; Now try to find play button in the opened item
                try {
                    itemPlayBtn := cUIA.FindElement({Name: "Play", Type: "Button"})
                    itemPlayBtn.Click()
                    Echo("Started playing selected item")
                    return
                } catch {
                    ; Try shuffle if available
                    try {
                        shuffleBtn := cUIA.FindElement({Name: "Shuffle", Type: "Button"})
                        shuffleBtn.Click()
                        Echo("Started shuffle play")
                        return
                    }
                }
            }
        }
        
        ; Method 4: Try keyboard shortcuts as fallback
        Echo("Using keyboard fallback to start radio...")
        ; Try some common keyboard shortcuts for play/shuffle
        cUIA.Send("{Space}")  ; Space often plays/pauses
        Sleep(500)
        
        Echo("Attempted to start radio - verify manually if needed")
        
    } catch Error as e {
        Echo("Radio start error: " . e.message . " - Using keyboard fallback")
        ; Final fallback to keyboard navigation
        Loop 10 {
            cUIA.Send("{Tab}")
            Sleep(150)
            
            if (A_Index = 3 || A_Index = 5 || A_Index = 7) {
                cUIA.Send("{Enter}")
                Sleep(300)
            }
        }
        Echo("Used keyboard fallback for radio start")
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

; Adjust system volume by specified amount
AdjustVolume(amount) {
    try {
        currentVolume := SoundGetVolume()
        newVolume := currentVolume + amount
        
        ; Clamp between 0 and 100
        if (newVolume > 100) {
            newVolume := 100
        } else if (newVolume < 0) {
            newVolume := 0
        }
        
        SoundSetVolume(newVolume)
        Echo("Volume: " . Round(newVolume) . "%")
        
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
        FileAppend(message . "`n", "*")  ; "*" means stdout in AHK v2
    } catch {
        ; If stdout is not available (no console), silently continue
        ; This happens when script is run by double-clicking or from GUI
        ; For help text, we'll show a message box instead
        if (InStr(message, "USAGE:") > 0) {
            MsgBox(message, "YouTube Music Controller Help", "OK")
        }
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
  volume-up [amount]   - Increase volume (default: 10)
  volume-down [amount] - Decrease volume (default: 10)

OTHER COMMANDS:
  help                 - Show this help

EXAMPLES:
  music_controller.ahk play jazz
  music_controller.ahk search ""study music""
  music_controller.ahk toggle
  music_controller.ahk volume-up 20
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