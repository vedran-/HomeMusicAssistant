# Home Assistant Voice Control System

This is the documentation for the Home Assistant voice control system.
It should run on a local machine that is connected to the internet.
It should have basic voice control for music, system volume, sending the machine to sleep, and a few other things.

## Tech flow

- It will listen for a wake word using the openwakeword container, using the default wake word "hey jarvis".
- What is said after the wake word is sent to whisper-large-v3 on Groq Cloud for transcription (https://console.groq.com/docs/speech-to-text).
- The transcription is sent to an LLM using LiteLLM, with instructions of available tools and a description of what to do with the transcription.
- The LLM will then respond with a tool to call and a list of parameters to pass to the tool.
- We might need to write a custom tool using AutoHotkey v2 with UIAutomation v2 for the LLM to control the machine to sleep.

## Tech Stack
 - LiteLLM for whisper and LLM support
 - openwakeword container for wake word detection (openwakeword: image: rhasspy/wyoming-openwakeword)
 - tool `music_controller.ahk` to control music volume (check @tools/music_controller.md for more info)
 - AutoHotkey v2 with UIAutomation v2 for writing custom tools
 - Piper (text to speech): rhasspy/wyoming-piper:latest



## Future Scope

For future reference - we will expand the system to include a few other tools.
Home Assistant to control different devices.
  homeassistant:
    image: homeassistant/home-assistant:latest  

But this is out of scope for now.

# TODO
- Add support for MCP and general internet use
- Add support for Home Assistant
