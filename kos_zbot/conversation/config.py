import os
import json
import tempfile
import sounddevice as sd
from pathlib import Path

TEMP_DIR = Path(tempfile.gettempdir()) / "kos_zbot"
CONFIG_FILE = TEMP_DIR / "config.json"

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
    print("=== KOS ZBot Configuration Setup ===")
    print("Setting up your audio configuration...")
    
    TEMP_DIR.mkdir(exist_ok=True)
    
    config = DEFAULT_CONFIG.copy()
    microphones, speakers = get_available_devices()

    config["microphone_id"] = prompt_device_selection(microphones, "microphone")
    config["speaker_id"] = prompt_device_selection(speakers, "speaker")

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

    print(f"\n✓ Configuration saved to: {CONFIG_FILE}")
    print("=" * 40)
    return config


def load_config():
    TEMP_DIR.mkdir(exist_ok=True)
    
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


def update_config():
    print("=== Update KOS ZBot Configuration ===")
    
    current_config = load_config()
    print(f"Current configuration loaded from: {CONFIG_FILE}\n")
    
    microphones, speakers = get_available_devices()

    print(f"Current microphone ID: {current_config.get('microphone_id', 'Not set')}")
    new_mic = prompt_device_selection(microphones, "microphone")
    if new_mic is not None:
        current_config["microphone_id"] = new_mic

    print(f"\nCurrent speaker ID: {current_config.get('speaker_id', 'Not set')}")
    new_speaker = prompt_device_selection(speakers, "speaker")
    if new_speaker is not None:
        current_config["speaker_id"] = new_speaker

    with open(CONFIG_FILE, "w") as f:
        json.dump(current_config, f, indent=4)
    
    print(f"\n✓ Configuration updated and saved to: {CONFIG_FILE}")
    return current_config


def show_config():
    config = load_config()
    
    print("=== Current KOS ZBot Configuration ===")
    print(f"Config file: {CONFIG_FILE}")
    print("-" * 40)
    print(f"Microphone ID: {config.get('microphone_id', 'Not set')}")
    print(f"Speaker ID: {config.get('speaker_id', 'Not set')}")
    print(f"Volume: {config.get('volume', 'Not set')}")
    print(f"Environment: {config.get('environment', 'Not set')}")
    print("=" * 40)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "show":
            show_config()
        elif command == "update":
            update_config()
        elif command == "create":
            create_config()
        else:
            print("Usage: python config.py [show|update|create]")
            print("  show   - Display current configuration")
            print("  update - Update existing configuration") 
            print("  create - Create new configuration")
    else:
        config = load_config()
        print("Configuration loaded successfully!")
        show_config()
