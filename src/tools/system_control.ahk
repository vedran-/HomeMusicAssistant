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

; Function to show help information
ShowHelp() {
    help_text := "System Control Script v1.0`nUsage: system_control.ahk <command>`n`nCommands:`n  sleep       Put the computer to sleep`n  shutdown    Shutdown the computer`n  help        Show this help information`n"
    FileAppend(help_text . "`n", "*")
}

; Handle script termination
OnExit(CleanExit)

CleanExit(*) {
    ; Cleanup function called when script exits
} 