import json
import logging
import os
import pathlib
import sys
logger = logging.getLogger(__name__)

class Settings:
    def __init__(self, json_file):
        self.json_file = json_file
        json_file_path= os.fspath(pathlib.Path(__file__).parent / f'{json_file}')
        self.load_settings(json_file_path)

    def load_settings(self, json_file):
        logger.info(f"Loading settings from {json_file}")
        try:
            with open(json_file, 'r') as file:
                data = json.load(file)
                # Dynamically set attributes from the JSON keys
                for key, value in data.items():
                    #logger.debug(f"Loading variable '{key}' = {value}")
                    setattr(self, key, value)
        except FileNotFoundError:
            logger.critical(
                f"Settings file '{json_file}' not found. Copy 'settings.json.example' to "
                f"'settings.json' first. Example: cp settings.json.example settings.json"
            )
            sys.exit(1)
        except json.JSONDecodeError as e:
            logger.critical(f"Error parsing JSON: {e}. Check your settings.json file.")
            sys.exit(1)

    def save_settings(self):
        try:
            with open(self.json_file, 'w') as file:
                # Serialize the current attributes of the instance
                json.dump(self.__dict__, file, indent=4)
            logger.info(f"Settings successfully saved to '{self.json_file}'.")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def __repr__(self):
        # Show all settings dynamically
        return f"Settings({self.__dict__})"
