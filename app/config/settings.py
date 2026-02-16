import json
import logging
import pathlib
import sys
logger = logging.getLogger(__name__)

class Settings:
    def __init__(self, json_file):
        self.json_file = pathlib.Path(json_file)
        if not self.json_file.is_absolute():
            self.json_file = pathlib.Path(__file__).resolve().parents[2] / self.json_file
        self.load_settings(self.json_file)

    def load_settings(self, json_file: pathlib.Path):
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
                f"'local_config/settings.json' first. Example: cp settings.json.example local_config/settings.json"
            )
            sys.exit(1)
        except json.JSONDecodeError as e:
            logger.critical(f"Error parsing JSON: {e}. Check your settings.json file.")
            sys.exit(1)

    def save_settings(self):
        try:
            serializable = self.to_serializable_dict()
            self.json_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.json_file, 'w') as file:
                json.dump(serializable, file, indent=4)
            logger.info(f"Settings successfully saved to '{self.json_file}'.")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def to_serializable_dict(self):
        data = {}
        for key, value in self.__dict__.items():
            # Runtime/internal fields should not be persisted to settings.json
            if key == "json_file" or key.startswith("_"):
                continue
            data[key] = value
        return data

    def __repr__(self):
        # Show all settings dynamically
        return f"Settings({self.__dict__})"
