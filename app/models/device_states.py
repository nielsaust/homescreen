import logging
logger = logging.getLogger(__name__)

class DeviceStates:
    def __init__(self):
        self.devices_inited = False
        self.data = None
        self.printer_progress = 0
        self.harmony_state = None
        self.cover_kitchen = None
        self.canary_temp = None
        self.light_tafel = None
        self.light_keuken = None
        self.light_kleur = None
        self.light_woonkamer = None
        self.in_bed_changed = None
        self.in_bed_original = None
        self.in_bed = None
        self.trash_warning = None
        self.bed_heating_on = None
        self.playstation_power = None
        self.playstation_available = None

    def update_states(self,data):
        self.data = data
        self.harmony_state = data.get('harmony_state')
        try:
            self.cover_kitchen = float(data.get('cover_kitchen'))
        except ValueError:
            logger.error(f"Error: Could not convert the string (cover_kitchen = {data.get('cover_kitchen')}) to a float.")
            self.cover_kitchen = 0
        try:
            self.canary_temp = float(data.get('canary_temp'))
        except ValueError:
            logger.error(f"Error: Could not convert the string (canary_temp = {data.get('canary_temp')}) to a float.")
            self.canary_temp = 15
        self.light_tafel = data.get('light_tafel')
        self.light_keuken = data.get('light_keuken')
        self.light_kleur = data.get('light_kleur')
        self.light_woonkamer = data.get('light_woonkamer')
        if hasattr(self,  'in_bed') and not self.in_bed_changed:
            self.in_bed_changed = self.in_bed_original != data.get('in_bed')
        self.in_bed_original = data.get('in_bed')
        self.in_bed = False if data.get('in_bed') == "off" else True
        self.trash_warning = False if data.get('trash_warning') == "off" else True
        self.bed_heating_on = False if data.get('bed_heating_on') == "off" else True
        self.playstation_power = False if data.get('playstation_power') == "off" or data.get('playstation_power') == "unavailable" else True
        self.playstation_available = False if data.get('playstation_power') == "unavailable" else True
        self.devices_inited = True