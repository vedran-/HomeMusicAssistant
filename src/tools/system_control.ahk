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
        case "restart":
            RestartComputer()
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
        case "set-volume":
            if (A_Args.Length >= 2) {
                percentage := Integer(A_Args[2])
                SetAbsoluteVolume(percentage)
            } else {
                FileAppend("Error: set-volume requires a percentage value`n", "*")
                ExitApp(1)
            }
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
        
        ; Method 1: Use rundll32 (most reliable for sleep)
        try {
            ; Use rundll32 with powrprof.dll - this is the most reliable method
            Run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", , "Hide")
            FileAppend("Sleep command executed via rundll32`n", "*")
            ExitApp(0)
        } catch Error as e {
            FileAppend("rundll32 method failed: " . e.message . "`n", "*")
        }
        
        ; Method 2: Use PowerShell (modern alternative)
        try {
            Run('powershell.exe -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState([System.Windows.Forms.PowerState]::Suspend, $false, $false)"', , "Hide")
            FileAppend("Sleep command executed via PowerShell`n", "*")
            ExitApp(0)
        } catch Error as e {
            FileAppend("PowerShell method failed: " . e.message . "`n", "*")
        }
        
        ; Method 3: Direct Windows API call (last resort)
        try {
            ; Use the Windows API directly - this should work if the others fail
            ; SetSuspendState(BOOLEAN Hibernate, BOOLEAN ForceCritical, BOOLEAN DisableWakeEvent)
            result := DllCall("PowrProf.dll\SetSuspendState", "UChar", 0, "UChar", 0, "UChar", 0, "UInt")
            if (result) {
                FileAppend("Sleep command executed via Windows API`n", "*")
                ExitApp(0)
            } else {
                FileAppend("Windows API returned false - may require administrator privileges`n", "*")
            }
        } catch Error as e {
            FileAppend("Windows API method failed: " . e.message . "`n", "*")
        }
        
        ; If all methods fail, throw an error
        throw Error("All sleep methods failed - computer may not support suspend or requires administrator privileges")
        
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

; Function to restart the computer
RestartComputer() {
    try {
        FileAppend("Restarting computer...`n", "*")
        
        ; Use Windows restart command with 5 second delay
        Run('shutdown.exe /r /t 5 /c "Restart initiated by voice control"', , "Hide")
        
        FileAppend("Restart command executed (5 second delay)`n", "*")
        ExitApp(0)
        
    } catch Error as e {
        FileAppend("Failed to restart computer: " . e.message . "`n", "*")
        ExitApp(1)
    }
}

; Get current system volume and print to stdout
GetVolume() {
    currentVolume := SoundGetVolume()
    volumeValue := Round(currentVolume)
    
    ; Use Echo function to output volume (writes to both log and stdout)
    Echo(volumeValue)
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

; Set system volume to absolute percentage
SetAbsoluteVolume(percentage) {
    try {
        ; Validate percentage range (allow 0 for complete silence)
        if (percentage < 0 || percentage > 100) {
            throw Error("Volume percentage must be between 0 and 100")
        }
        
        SoundSetVolume(percentage)
        
        ; Output confirmation
        RunWait('cmd /c echo ' . percentage, , "")
        Echo("Volume set to: " . percentage . "%")
        
    } catch Error as e {
        throw Error("Failed to set volume: " . e.message)
    }
}

; Echo message to both log file and stdout
Echo(message) {
    ; Write to log file for debugging
    logFilePath := A_ScriptDir . "\system_control_log.txt"
    FileAppend(FormatTime(,"HH:mm:ss") . " | " . message . "`n", logFilePath)
    
    ; Also output to stdout using cmd (for Python to capture)
    try {
        RunWait('cmd /c echo ' . message, , "")
    } catch {
        ; Fallback to FileAppend if cmd fails
        FileAppend(message . "`n", "*")
    }
}

; Function to show help information
ShowHelp() {
    help_text := "System Control Script v1.0`nUsage: system_control.ahk <command>`n`nCommands:`n  sleep         Put the computer to sleep`n  shutdown      Shutdown the computer`n  restart       Restart the computer`n  mute          Mute system audio`n  unmute        Unmute system audio`n  get-volume    Get current system volume percentage`n  volume-up     Increase volume by percentage (default: 10%)`n  volume-down   Decrease volume by percentage (default: 10%)`n  set-volume    Set absolute volume percentage (0-100)`n  help          Show this help information`n"
    FileAppend(help_text . "`n", "*")
}

; Handle script termination
OnExit(CleanExit)

CleanExit(*) {
    ; Cleanup function called when script exits
}