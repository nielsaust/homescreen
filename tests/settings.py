import json
import logging
logger = logging.getLogger(__name__)

class Settings:
    def __init__(self):
        # general
        self.log_level = "INFO"
        self.show_weather_on_idle = True
        self.screen_width = 720
        self.screen_height = 720
        self.min_time_between_actions = 0.2
        self.in_bed_turn_off_timeout = 15000
        self.verify_ssl_on_trusted_sources = True

        # feedback label
        self.show_feedback_label_timeout = 2000 # set to 0 to never show
        self.feedback_label_width = 100
        self.feedback_label_height = 100
        self.feedback_label_border = 5
        self.feedback_label_padx = 10
        self.feedback_label_pady = 10
        self.feedback_icon_size = (60,60)

        # MQTT
        self.mqtt_broker = "192.168.0.175"
        self.mqtt_port = 1883
        self.mqtt_user = "homeassistant"
        self.mqtt_password = "dipath6baiguFi6faik7ocanaiWoLee3fe9piNi2ue3aiteizaich2Ahbole4ooh"
        self.mqtt_sleep_for_connectio_to_complete = 5
        self.mqtt_qos = 2
        self.mqtt_accept_nonessential_messages_after = 10

        # Home Assistant
        self.home_assistant_api_base_url = "https://doornena.duckdns.org"

        # topics
        self.mqtt_topic_music = "music"
        self.mqtt_topic_devices = "screen_commands/incoming"
        self.mqtt_topic_doorbell = "doorbell"
        self.mqtt_topic_printer_progress = "octoPrint/progress/printing"
        self.mqtt_topic_calendar = "calendar"
        self.mqtt_topic_print_start = "octoPrint/event/PrintStarted"
        self.mqtt_topic_print_done = "octoPrint/event/PrintDone"
        self.mqtt_topic_print_cancelled = "octoPrint/event/PrintCancelled"
        self.mqtt_topic_print_change_filament = "octoPrint/event/FilamentChange"
        self.mqtt_topic_print_change_z = "octoPrint/event/ZChange"

        # OpenWeatherMap API key. Get one for free at https://openweathermap.org/
        self.weather_api_key = 'bcde94c14bda17e23edce27c08a8192f'
        self.weather_city_id = '2754064' # lookup your city ID here: https://openweathermap.org/find
        self.weather_langage = 'nl'
        self.weather_update_interval = 60 # each 60 seconds get a weather update
        self.weather_api_call_retries = 10
        self.weather_api_call_retry_delay = 5
        self.weather_api_unavailable = False

        # gestures
        self.hold_time = 0.3
        self.gesture_min_movement = 30 # amount of pixels that must be moved before it to be seen as a gesture

        # music
        self.media_titles_relative_height = 0.20
        self.media_titles_font_size = 28
        self.media_titles_timeout = 5000 
        self.media_show_titles = True
        self.media_get_remote_image_retry_amount = 3
        self.media_clear_image_before_getting_new = True
        self.media_sanitize_titles = True

        # menu
        self.close_menu_timeout = 7000
        self.destroy_image_timeout = 10000
        self.menu_button_width = 360
        self.menu_button_height = 300
        self.menu_button_padding = 10
        self.menu_item_font_size = 24
        self.button_down_color_change_time = 1000
        self.menu_border_thickness = 10
        self.button_color = {
            "inactive": "#FFFFFF",
            "active": "#B4E33D",
            "down": "#00A5CF",
            "disabled": "#DCDCDC"
        }
        self.menu_background_color = {
            "weather": "#000000",
            "music": "#000000",
            "menu": "#201C29"
        }
        self.destroy_slider_timeout = 60000

        # cam
        self.destroy_cam_timeout = 60000

        # doorbell
        self.doorbell_url = "192.168.0.131"
        self.doorbell_path = "/cgi-bin/snapshot.cgi?channel=1"
        self.doorbell_username = "admin"
        self.doorbell_password = "B3lletjeTr3k!"

        # printer
        self.printer_url = None
        self.show_cam_on_print_percentage = 0 # 0 to disable show camera
        self.printer_screen_blink_on_complete = False # MQTT messages are now now send correctly by printer, so turning off
        # calendar
        self.calendar_party_colors = ['#ffbe0b', '#fb5607', '#ff006e', '#8338ec', '#3a86ff']
        self.calendar_default_color = '#3a86ff'

        # Save variables using the helper function
        self.variables_to_save_and_load = [
            'log_level',
            'show_weather_on_idle',
            'screen_width',
            'screen_height',
            'min_time_between_actions',
            'in_bed_turn_off_timeout',
            'verify_ssl_on_trusted_sources',
            'show_feedback_label_timeout',
            'feedback_label_width',
            'feedback_label_height',
            'feedback_label_border',
            'feedback_label_padx',
            'feedback_label_pady',
            'feedback_icon_size',
            'mqtt_broker',
            'mqtt_port',
            'mqtt_user',
            'mqtt_password',
            'mqtt_sleep_for_connectio_to_complete',
            'mqtt_qos',
            'mqtt_accept_nonessential_messages_after',
            'home_assistant_api_base_url',
            'mqtt_topic_music',
            'mqtt_topic_devices',
            'mqtt_topic_doorbell',
            'mqtt_topic_printer_progress',
            'mqtt_topic_calendar',
            'mqtt_topic_print_start',
            'mqtt_topic_print_done',
            'mqtt_topic_print_cancelled',
            'mqtt_topic_print_change_filament',
            'mqtt_topic_print_change_z',
            'weather_api_key',
            'weather_city_id',
            'weather_langage',
            'weather_update_interval',
            'weather_api_call_retries',
            'weather_api_call_retry_delay',
            'weather_api_unavailable',
            'hold_time',
            'gesture_min_movement',
            'media_titles_relative_height',
            'media_titles_font_size',
            'media_titles_timeout',
            'media_show_titles',
            'media_get_remote_image_retry_amount',
            'media_clear_image_before_getting_new',
            'media_sanitize_titles',
            'close_menu_timeout',
            'destroy_image_timeout',
            'menu_button_width',
            'menu_button_height',
            'menu_button_padding',
            'menu_item_font_size',
            'button_down_color_change_time',
            'menu_border_thickness',
            'menu_background_color',
            'destroy_slider_timeout',
            'destroy_cam_timeout',
            'doorbell_url',
            'doorbell_path',
            'doorbell_username',
            'doorbell_password',
            'printer_url',
            'show_cam_on_print_percentage',
            'printer_screen_blink_on_complete',
            'calendar_party_colors',
            'calendar_default_color',
            'force_update',
        ]

        # debug 
        self.force_update = False 

    def _load_variable(self, data, var_name):
        setattr(self, var_name, data.get(var_name, getattr(self, var_name)))

    def load_from_file(self, file_path='settings.json'):
        logger.info("loading settings from settings.json")
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)

            # Load variables using the helper function
            variables_to_load = self.variables_to_save_and_load

            for var_name in variables_to_load:
                logger.debug(f"Loading variable '{var_name}' = {data.get(var_name)}")
                self._load_variable(data, var_name)

            logger.info("Settings loaded successfully!")
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON in {file_path}")    

    def _save_variable(self, data, var_name):
        data[var_name] = getattr(self, var_name)

    def save_to_file(self, file_path='settings.json'):
        logger.info("saving settings to settings.json")
        data = {}
        
        # Save variables using the helper function
        variables_to_save = self.variables_to_save_and_load


        for var_name in variables_to_save:
            self._save_variable(data, var_name)

        try:
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=2)

            print("Settings saved successfully!")
        except Exception as e:
            print(f"Error saving settings: {e}")

