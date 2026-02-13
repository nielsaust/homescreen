import json

class Settings:
    def __init__(self, json_file):
        self.json_file = json_file
        self.load_settings(json_file)

    def load_settings(self, json_file):
        try:
            with open(json_file, 'r') as file:
                data = json.load(file)
                # Dynamically set attributes from the JSON keys
                for key, value in data.items():
                    setattr(self, key, value)
        except FileNotFoundError:
            print(f"Settings file '{json_file}' not found. Using default values.")
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}. Using default values.")

    def save_settings(self):
        try:
            with open(self.json_file, 'w') as file:
                # Serialize the current attributes of the instance
                json.dump(self.__dict__, file, indent=4)
            print(f"Settings successfully saved to '{self.json_file}'.")
        except Exception as e:
            print(f"Error saving settings: {e}")

    def __repr__(self):
        # Show all settings dynamically
        return f"Settings({self.__dict__})"

# Example Usage
if __name__ == "__main__":
    # Assume settings.json initially contains:
    # {
    #     "log_level": "DEBUG",
    #     "app_name": "MyApp"
    # }
    settings = Settings("settings.json")

    # Modify settings dynamically
    settings.version = "1.0.1"
    settings.log_level = "INFO"

    # Save modified settings back to the file
    settings.save_settings()

    # Reload to confirm changes
    new_settings = Settings("settings.json")
    print(new_settings)