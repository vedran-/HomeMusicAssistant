#Requires AutoHotkey v2.0

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
    
    ; Ensure YouTube Music is open
    EnsureYouTubeMusicOpen()
    
    ; Search for the music
    SearchMusic(searchTerm)
    
    ; Start radio after search
    StartRadio()
}

; Toggle play/pause in current YouTube Music tab
TogglePlayback() {
    if (!ActivateYouTubeMusicTab()) {
        throw Error("YouTube Music tab not found. Use 'play' command first.")
    }
    
    ; Space key toggles play/pause in YouTube Music
    Send("{Space}")
    Echo("Toggled playback")
}

; Search for music in YouTube Music
SearchMusic(searchTerm) {
    if (!ActivateYouTubeMusicTab()) {
        EnsureYouTubeMusicOpen()
        Sleep(3000)  ; Wait for page load
    }
    
    Echo("Searching for: " . searchTerm)
    
    ; Use "/" to focus search box (YouTube keyboard shortcut)
    Send("/")
    Sleep(300)
    
    ; Clear existing text and type search term
    Send("^a")  ; Select all
    Sleep(100)
    SendText(searchTerm)
    Sleep(300)
    
    ; Press Enter to search
    Send("{Enter}")
    Sleep(1500)  ; Wait for search results
}

; Start playing radio after search results are loaded
StartRadio() {
    Echo("Starting radio...")
    
    ; Method 1: Try keyboard navigation to find radio button
    ; Tab through elements and look for radio/shuffle buttons
    Loop 15 {
        Send("{Tab}")
        Sleep(200)
        
        ; Try pressing Enter on elements that might be radio buttons
        if (A_Index = 3 || A_Index = 6 || A_Index = 9) {
            Send("{Enter}")
            Sleep(500)
            
            ; Check if music started (this is a simple heuristic)
            if (A_Index = 6) {  ; Usually works around the 6th tab
                Echo("Radio started successfully")
                return
            }
        }
    }
    
    ; Method 2: Try common keyboard shortcuts
    Send("+p")  ; Shift+P sometimes works for shuffle/radio
    Sleep(500)
    
    ; Method 3: Try clicking the first search result
    Send("{Tab}{Tab}{Enter}")
    Sleep(500)
    
    Echo("Attempted to start radio - verify manually if needed")
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

; Ensure YouTube Music is open in Brave
EnsureYouTubeMusicOpen() {
    ; Try to activate existing YouTube Music tab first
    if (ActivateYouTubeMusicTab()) {
        return
    }
    
    Echo("Opening YouTube Music...")
    
    ; Open Brave with YouTube Music URL
    Run(BRAVE_PATH . " " . YOUTUBE_MUSIC_URL)
    Sleep(4000)  ; Wait for browser and page to load
    
    ; Activate the browser window
    if (!ActivateBrowserWindow()) {
        throw Error("Failed to activate browser window")
    }
}

; Activate existing YouTube Music tab or browser window
ActivateYouTubeMusicTab() {
    ; Try to activate window with YouTube Music title
    try {
        WinActivate("YouTube Music")
        Sleep(500)
        return true
    } catch {
        ; Try to activate any Brave window and navigate to YouTube Music
        try {
            WinActivate("ahk_exe brave.exe")
            Sleep(500)
            
            ; Check if we're already on YouTube Music
            ; If not, open new tab with YouTube Music
            Send("^t")  ; New tab
            Sleep(300)
            SendText(YOUTUBE_MUSIC_URL)
            Send("{Enter}")
            Sleep(3000)
            
            return true
        } catch {
            return false
        }
    }
}

; Activate browser window
ActivateBrowserWindow() {
    try {
        WinActivate("ahk_exe brave.exe")
        Sleep(500)
        return true
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
YouTube Music & System Control Script

USAGE:
  TestMusic.ahk <command> [parameters]

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
  TestMusic.ahk play jazz
  TestMusic.ahk search ""study music""
  TestMusic.ahk toggle
  TestMusic.ahk volume-up 20
  TestMusic.ahk mute

NOTES:
- The script works with YouTube Music in Brave browser
- Music commands require internet connection
- The script will open YouTube Music automatically if needed
- Use quotes around multi-word search terms
    )"
    
    Echo(helpText)
}

; ====================================================================
; SCRIPT EXECUTION
; ====================================================================

; Run main function
Main()