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

StartRadioUIA(cUIA) {
    Echo("Starting radio...")

    allButtons := cUIA.FindElements({Type: "Button"})
    ; Echo("Debug: Found " . allButtons.Length . " total buttons on page")
    radio_button := ""
    shuffle_button := ""
    play_button := ""
    was_like_button_found := false
    For button in allButtons {
        ; Echo(button.Name . " - " . button.Type)
        if (radio_button = "" && button.Name = "Radio") {
            radio_button := button
        }
        if (!was_like_button_found && shuffle_button = "" && button.Name = "Shuffle") {
            shuffle_button := button
        }
        ; First button whose name starts with 'Play '
        if (play_button = "" && StrLen(button.Name) > 5 && SubStr(button.Name, 1, 5) = "Play ") {
            play_button := button
        }
        if (button.Name = "Like") {
            was_like_button_found := true
        }
    }

    if (radio_button != "") {
        radio_button.Click()
        Echo("Radio button clicked!")
        return
    }
    if (shuffle_button != "") {
        shuffle_button.Click()
        Echo("Shuffle button clicked!")
        return
    }
    if (play_button != "") {
        play_button.Click()
        Echo("Play button " . play_button.Name . " clicked!")
        return
    }
}


Echo("--------------")
appElement := EnsureYouTubeMusicAppOpenAndFocus()

SearchMusicInAppUIA(A_Args[1])
Sleep(2000)
StartRadioUIA(appElement)


