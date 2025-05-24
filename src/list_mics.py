#!/usr/bin/env python3
"""
A simple utility script to list all available microphones.
This helps users identify which microphone to use with the Home Assistant Voice Control System.
"""

import pyaudio
import os
import sys
import json
from src.config.settings import load_settings
from src.utils.logger import app_logger, configure_logging

def list_microphones():
    """Lists all available microphones with their indices and details."""
    # Initialize PyAudio
    pa = pyaudio.PyAudio()
    
    print("\n=== Available Microphones ===\n")
    
    # Dictionary to store microphone details for possible export
    mics = {}
    found_mics = False
    
    # Get device count
    device_count = pa.get_device_count()
    if device_count == 0:
        print("No audio devices found.")
        return
    
    # Loop through all devices
    for i in range(device_count):
        try:
            info = pa.get_device_info_by_index(i)
            
            # Check if it's an input device
            if info.get('maxInputChannels', 0) > 0:
                found_mics = True
                name = info.get('name', 'Unknown')
                host_api = pa.get_host_api_info_by_index(info.get('hostApi', 0)).get('name', 'Unknown')
                channels = info.get('maxInputChannels', 0)
                sample_rate = info.get('defaultSampleRate', 0)
                
                # Store microphone details
                mics[i] = {
                    'index': i,
                    'name': name,
                    'host_api': host_api,
                    'channels': channels,
                    'sample_rate': sample_rate
                }
                
                # Print microphone details
                print(f"Index {i}: {name}")
                print(f"  API: {host_api}")
                print(f"  Channels: {channels}")
                print(f"  Sample Rate: {sample_rate}")
                print()
        except Exception as e:
            print(f"Error getting info for device {i}: {e}")
    
    if not found_mics:
        print("No input devices (microphones) found.")
        return
    
    # Terminate PyAudio
    pa.terminate()
    
    print("\n=== Configuration Examples ===\n")
    print("To select a microphone by index, add to your config.json:")
    print('''
    "audio_settings": {
        "input_device_index": 1,  # Replace with your chosen index
        ...
    }
    ''')
    
    print("To select a microphone by name keyword, add to your config.json:")
    print('''
    "audio_settings": {
        "input_device_name_keyword": "USB",  # Replace with a keyword in your microphone name
        ...
    }
    ''')
    
    return mics

def update_config(mic_index):
    """Updates config.json with the selected microphone index."""
    try:
        # Load current config
        with open("config.json", 'r') as f:
            config = json.load(f)
        
        # Update audio settings
        if 'audio_settings' not in config:
            config['audio_settings'] = {}
        
        config['audio_settings']['input_device_index'] = int(mic_index)
        
        # Save updated config
        with open("config.json", 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\nConfig updated! Microphone with index {mic_index} set as default input device.")
    except Exception as e:
        print(f"Error updating config: {e}")

if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--update-config" and len(sys.argv) > 2:
        try:
            mic_index = int(sys.argv[2])
            update_config(mic_index)
        except ValueError:
            print(f"Error: '{sys.argv[2]}' is not a valid microphone index. Please provide a number.")
            sys.exit(1)
    else:
        # Just list the microphones
        mics = list_microphones()
        
        # Prompt for config update
        print("\nTo update your config.json with a specific microphone, run:")
        print(f"python -m src.list_mics --update-config INDEX")
        print("Where INDEX is the number from the list above.") 