# dashboard_service/gui/settings_manager.py
# Author: Andrew Fox



# -----------------------------
# Imports
# -----------------------------

import json
import os

# Default settings values
DEFAULT_SETTINGS = {
    "graph_refresh_rate": 1000, # ms
    "accent_color": "#FF0000" # red
}

# Path to settings file
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".smart_dashboard_settings.json")


def load_settings():

    # Load settings from JSON file
    # If file doesn't exist, create it with default values

    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS

    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)

        # Ensure all default keys exist
        for key, value in DEFAULT_SETTINGS.items():
            if key not in data:
                data[key] = value

        return data

    except (json.JSONDecodeError, OSError):
        # If corrupted, reset to defaults
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS


def save_settings(settings_dict):
    # Save given dictionary to settings file
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings_dict, f, indent=4)
    except OSError as e:
        print(f"Error saving settings: {e}")