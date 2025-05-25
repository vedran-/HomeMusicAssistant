#Requires AutoHotkey v2.0
; System Control Script for Home Assistant Voice Control
; Provides sleep, shutdown, and other system control functions
; 
; Usage: system_control.ahk <command> [parameters]
; 
; Commands:
;   sleep     - Put the computer to sleep
;   shutdown  - Shutdown the computer
;   help      - Show help information

; Initialize error handling
SetWorkingDir(A_ScriptDir)

; Main execution
if A_Args.Length = 0 {
    ShowHelp()
    ExitApp(1)
}

command := StrLower(A_Args[1])

try {
    switch command {
        case "sleep":
            SleepComputer()
        case "shutdown":
            ShutdownComputer()
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
        case "get-volume":
            GetVolume()
        case "help":
            ShowHelp()
        default:
            FileAppend("Error: Unknown command '" . command . "'`n", "*")
            ShowHelp()
            ExitApp(1)
    }
} catch Error as e {
    FileAppend("Error: " . e.message . "`n", "*")
    ExitApp(1)
}

; Function to put the computer to sleep
SleepComputer() {
    try {
        FileAppend("Putting computer to sleep...`n", "*")
        
        ; Use Windows API to suspend the system
        result := DllCall("PowrProf.dll\SetSuspendState", "int", 0, "int", 0, "int", 0)
        
        if (result = 0) {
            ; If the API call fails, try alternative method
            FileAppend("Primary sleep method failed, trying alternative...`n", "*")
            Run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", , "Hide")
        }
        
        FileAppend("Sleep command executed`n", "*")
        ExitApp(0)
        
    } catch Error as e {
        FileAppend("Failed to put computer to sleep: " . e.message . "`n", "*")
        ExitApp(1)
    }
}

; Function to shutdown the computer
ShutdownComputer() {
    try {
        FileAppend("Shutting down computer...`n", "*")
        
        ; Use Windows shutdown command with 5 second delay
        Run('shutdown.exe /s /t 5 /c "Shutdown initiated by voice control"', , "Hide")
        
        FileAppend("Shutdown command executed (5 second delay)`n", "*")
        ExitApp(0)
        
    } catch Error as e {
        FileAppend("Failed to shutdown computer: " . e.message . "`n", "*")
        ExitApp(1)
    }
}

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

; Echo message to stdout
Echo(message) {
    try {
        ; Try direct FileAppend to stdout
        FileAppend(message . "`n", "*")
    } catch {
        ; Use cmd to echo the message directly to console
        RunWait('cmd /c echo ' . message, , "")
    }
}

; Function to show help information
ShowHelp() {
    help_text := "System Control Script v1.0`nUsage: system_control.ahk <command>`n`nCommands:`n  sleep         Put the computer to sleep`n  shutdown      Shutdown the computer`n  mute          Mute system audio`n  unmute        Unmute system audio`n  get-volume    Get current system volume percentage`n  volume-up     Increase volume by percentage (default: 10%)`n  volume-down   Decrease volume by percentage (default: 10%)`n  help          Show this help information`n"
    FileAppend(help_text . "`n", "*")
}

; Handle script termination
OnExit(CleanExit)

CleanExit(*) {
    ; Cleanup function called when script exits
}