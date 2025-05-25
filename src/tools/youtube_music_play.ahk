#Requires AutoHotkey v2.0
#SingleInstance Force
#include Lib\UIA.ahk

YTM_EXE_PATTERN := "YouTube Music.exe"

Echo(message) {
    logFilePath := A_ScriptDir . "\youtube_music_play_log.txt"
    FileAppend(FormatTime(,"HH:mm:ss") . " | " . message . "`n", logFilePath)
}


EnsureYouTubeMusicAppOpenAndFocus() {
    try {
        hWnd := WinExist("ahk_exe " . YTM_EXE_PATTERN)

        if (hWnd) {
            WinActivate(hWnd)
            WinWaitActive(hWnd,, 2)
            ; Sleep(500)
            appElement := UIA.ElementFromHandle(hWnd)
            Echo("YouTube Music app found and activated.")
            return appElement
        } else {
            Echo("YouTube Music app not found running. Please start it.")
            throw Error("YouTube Music app is not running.")
        }
    } catch Error as e {
        Echo("Error in EnsureYouTubeMusicAppOpenAndFocus: " . e.Message)
        throw e
    }
}

SearchMusicInAppUIA(searchTerm) {
    Send "/"
    Send "^a"
    Send searchTerm
    Send "{Enter}"
}

ExecutePlaybackActionUIA(cUIA, command) {
    Echo("Executing playback action: " . command)

    allButtons := cUIA.FindElements({Type: "Button"})
    radio_button := ""
    shuffle_button := ""
    play_button := ""

    For button in allButtons {
        if (radio_button = "" && button.Name = "Radio") {
            radio_button := button
            Echo("Found 'Radio' button.")
        }
        if (shuffle_button = "" && button.Name = "Shuffle") {
            shuffle_button := button
            Echo("Found 'Shuffle' button.")
        }
        if (play_button = "" && StrLen(button.Name) > 5 && SubStr(button.Name, 1, 5) = "Play ") {
            play_button := button
            Echo("Found 'Play...' button: " . button.Name)
        }
    }

    if (command = "radio") {
        if (radio_button != "") {
            radio_button.Click()
            Echo("Radio button clicked for 'radio' command!")
            return
        } else {
            Echo("Radio button not found for 'radio' command. Attempting fallback...")
            if (shuffle_button != "") {
                shuffle_button.Click()
                Echo("Shuffle button clicked! (fallback from radio)")
                return
            }
            if (play_button != "") {
                play_button.Click()
                Echo("Play button '" . play_button.Name . "' clicked! (fallback from radio)")
                return
            }
            Echo("No suitable button (Radio, Shuffle, Play) found for 'radio' command.")
            throw Error("No Radio/Shuffle/Play button found for 'radio' command.")
        }
    } else if (command = "play") {
        if (shuffle_button != "") {
            shuffle_button.Click()
            Echo("Shuffle button clicked for 'play' command!")
            return
        }
        if (play_button != "") {
            play_button.Click()
            Echo("Play button '" . play_button.Name . "' clicked for 'play' command!")
            return
        }
        Echo("Shuffle or Play button not found for 'play' command. Attempting fallback to Radio...")
        if (radio_button != "") {
            radio_button.Click()
            Echo("Radio button clicked! (fallback from play)")
            return
        }
        Echo("No suitable button (Shuffle, Play, Radio) found for 'play' command.")
        throw Error("No Shuffle/Play/Radio button found for 'play' command.")
    } else {
        Echo("Unknown command: " . command)
        throw Error("Unknown command specified: " . command)
    }
}


Echo("--------------")

if (A_Args.Length < 2) {
    Echo("Error: Insufficient arguments provided.")
    Echo("Usage: youtube_music_play.ahk <command> <searchTerm>")
    Echo("  <command>: 'play' or 'radio'")
    Echo("  <searchTerm>: The music query")
    ExitApp(1)
}

command := Trim(A_Args[1])
searchTerm := Trim(A_Args[2])

Echo("Received Command: '" . command . "'")
Echo("Received Search Term: '" . searchTerm . "'")

appElement := EnsureYouTubeMusicAppOpenAndFocus()

SearchMusicInAppUIA(searchTerm)
Sleep(2500) ; Increased sleep slightly to ensure page elements load after search
ExecutePlaybackActionUIA(appElement, command)


