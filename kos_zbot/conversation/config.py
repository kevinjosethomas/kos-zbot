import os
import json
import tempfile
from pathlib import Path
import sounddevice as sd

PROJECT_DIR = Path(__file__).parent
CONFIG_DIR = PROJECT_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "microphone_id": 1,
    "speaker_id": 2,
    "volume": 0.35,
    "environment": "default",
}


def get_available_devices():
    device_list = sd.query_devices()
    microphones = []
    speakers = []

    for i, device in enumerate(device_list):
        device_info = {
            "id": i,
            "name": device["name"],
            "channels": device["max_input_channels"] if device["max_input_channels"] > 0 else device["max_output_channels"]
        }
        
        if device["max_input_channels"] > 0:
            microphones.append(device_info)
        if device["max_output_channels"] > 0:
            speakers.append(device_info)

    return microphones, speakers


def prompt_device_selection(devices, device_type):
    if not devices:
        print(f"No {device_type}s found!")
        return None

    print(f"\nAvailable {device_type}s:")
    print("-" * 50)
    for device in devices:
        print(f"{device['id']:2d}: {device['name']} (channels: {device['channels']})")
    
    while True:
        try:
            choice = input(f"\nSelect {device_type} ID: ").strip()
            device_id = int(choice)
            
            valid_ids = [device['id'] for device in devices]
            if device_id in valid_ids:
                selected_device = next(d for d in devices if d['id'] == device_id)
                print(f"Selected {device_type}: {selected_device['name']}")
                return device_id
            else:
                print(f"Invalid choice. Please select from available IDs.")
                
        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            print(f"\nUsing first available {device_type} (ID: {devices[0]['id']})")
            return devices[0]['id']


def create_config():
    CONFIG_DIR.mkdir(exist_ok=True)
    
    config = DEFAULT_CONFIG.copy()
    microphones, speakers = get_available_devices()

    mic_id = prompt_device_selection(microphones, "microphone")
    if mic_id is not None:
        config["microphone_id"] = mic_id
    else:
        print(f"Warning: No microphones found. Using default ID: {config['microphone_id']}")

    speaker_id = prompt_device_selection(speakers, "speaker")
    if speaker_id is not None:
        config["speaker_id"] = speaker_id
    else:
        print(f"Warning: No speakers found. Using default ID: {config['speaker_id']}")

    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        print(f"\n✓ Configuration saved to: {CONFIG_FILE}")
    except Exception as e:
        print(f"Error saving configuration: {e}")
        print("Using default configuration in memory only.")
    
    print("=" * 40)
    return config


def load_config():
    CONFIG_DIR.mkdir(exist_ok=True)
    
    if not CONFIG_FILE.exists():
        print("Configuration not found. Setting up for first time...")
        return create_config()
  

    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

        for key in DEFAULT_CONFIG:
            if key not in config:
                config[key] = DEFAULT_CONFIG[key]

        return config

    except Exception as e:
        print(f"Error loading configuration: {e}")
        print("Creating new configuration...")
        return create_config()