from __future__ import annotations

import copy

from app.ui.menu_button import MenuButton


MENU_SCHEMA = [{'id': 'cinema', 'text': 'Zet bioscoop [cinema_action]', 'image': 'cinema.png', 'action': 'cinema'},
 {'id': 'debug_cinema',
  'text': 'Bios probleem repareren',
  'image': 'tools.png',
  'action': 'open_page',
  'screen': [{'id': 'debug_cinema_back', 'text': 'Terug', 'image': 'back.png', 'action': 'back'},
             {'id': 'soundbar_toggle',
              'text': 'Zet soundbar aan/uit',
              'image': 'speaker.png',
              'action': 'soundbar_toggle'},
             {'id': 'beamer_on', 'text': 'Zet projector aan', 'image': 'video.png', 'action': 'beamer_on'},
             {'id': 'beamer_off', 'text': 'Zet projector uit', 'image': 'video-off.png', 'action': 'beamer_off'},
             {'id': 'blinds_up', 'text': 'Scherm omhoog', 'image': 'blinds-up.png', 'action': 'blinds_up'},
             {'id': 'blinds_down', 'text': 'Scherm omlaag', 'image': 'blinds-down.png', 'action': 'blinds_down'},
             {'id': 'blinds_stop', 'text': 'Stop scherm', 'image': 'blinds.png', 'action': 'blinds_stop'},
             {'id': 'soundbar_hdmi', 'text': 'HDMI 1', 'image': 'output.png', 'action': 'soundbar_hdmi'},
             {'id': 'ps_toggle', 'text': 'Playstation [ps_action]', 'image': 'ps.png', 'action': 'ps_toggle'},
             {'id': 'soundbar_volume_down',
              'text': 'Zachter',
              'image': 'volume-down.png',
              'action': 'soundbar_volume_down'},
             {'id': 'soundbar_volume_up', 'text': 'Harder', 'image': 'volume-up.png', 'action': 'soundbar_volume_up'},
             {'id': 'soundbar_mute', 'text': 'Mute soundbar', 'image': 'mute.png', 'action': 'soundbar_mute'}]},
 {'id': 'music',
  'text': 'Muziek',
  'image': 'music.png',
  'action': 'music_menu',
  'screen': [{'id': 'music_back', 'text': 'Terug', 'image': 'back.png', 'action': 'back'},
             {'id': 'music_volume_up', 'text': 'Harder', 'image': 'volume-up.png', 'action': 'music_volume_up'},
             {'id': 'music_play_pause',
              'text': '[music_action] muziek',
              'image': 'play.png',
              'action': 'music_play_pause'},
             {'id': 'music_volume_down', 'text': 'Zachter', 'image': 'volume-down.png', 'action': 'music_volume_down'},
             {'id': 'music_previous', 'text': 'Vorig nummer', 'image': 'backward.png', 'action': 'music_previous'},
             {'id': 'music_next', 'text': 'Volgend nummer', 'image': 'forward.png', 'action': 'music_next'},
             {'id': 'music_show_title',
              'text': 'Toon muziek details',
              'image': 'detail.png',
              'action': 'music_show_title',
              'cancel_close': True}]},
 {'id': 'light_scenes',
  'text': 'Lichten',
  'image': 'lights.png',
  'action': 'light_scenes',
  'screen': [{'id': 'light_scenes_back', 'text': 'Terug', 'image': 'back.png', 'action': 'back'},
             {'id': 'lights_movie', 'text': 'Movie scene', 'image': 'movie.png', 'action': 'scene_movie'},
             {'id': 'lights_romance', 'text': 'Romance scene', 'image': 'romance.png', 'action': 'scene_romantic'},
             {'id': 'lights_dinner', 'text': 'Normal / dinner scene', 'image': 'cutlery.png', 'action': 'scene_dinner'},
             {'id': 'light_woonkamer',
              'text': 'Woonkamer licht [woonkamer_licht_action]',
              'image': 'sofa.png',
              'action': 'light_woonkamer'},
             {'id': 'light_keuken',
              'text': 'Keuken licht [keuken_licht_action]',
              'image': 'kitchen.png',
              'action': 'light_keuken'},
             {'id': 'light_tafel',
              'text': 'Tafel licht [tafel_licht_action]',
              'image': 'table.png',
              'action': 'light_tafel'},
             {'id': 'light_kleur',
              'text': 'Kleur licht [kleur_licht_action]',
              'image': 'color-lights.png',
              'action': 'light_kleur'},
             {'id': 'lights_bright', 'text': 'Fel scene', 'image': 'bright.png', 'action': 'scene_bright'},
             {'id': 'lights_off', 'text': 'Licht uit', 'image': 'light-off.png', 'action': 'scene_off'}]},
 {'id': 'cover_kitchen',
  'text': 'Doe keuken gordijn [cover_action]',
  'image': 'curtain.png',
  'action': 'cover_kitchen'},
 {'id': 'blinds_control',
  'text': 'Rolgordijn schijfpui',
  'image': 'blinds.png',
  'action': 'open_page',
  'screen': [{'id': 'blinds_control_back', 'text': 'Terug', 'image': 'back.png', 'action': 'back'},
             {'id': 'blinds_up', 'text': 'Scherm omhoog', 'image': 'blinds-up.png', 'action': 'blinds_up'},
             {'id': 'blinds_down', 'text': 'Scherm omlaag', 'image': 'blinds-down.png', 'action': 'blinds_down'},
             {'id': 'blinds_stop', 'text': 'Stop scherm', 'image': 'blinds.png', 'action': 'blinds_stop'}]},
 {'id': 'doorbell', 'text': 'Voordeur', 'image': 'door.png', 'action': 'doorbell'},
 {'id': 'calendar', 'text': 'Volgend kalender item', 'image': 'calendar.png', 'action': 'calendar'},
 {'id': 'calendar_add', 'text': 'Voeg kalender item toe', 'image': 'calendar-plus.png', 'action': 'calendar_add'},
 {'id': 'trash_warning_toggle',
  'text': 'Zet afval melding [trash_action]',
  'image': 'trash-x.png',
  'action': 'trash_warning_toggle'},
 {'id': 'screen_off', 'text': 'Zet scherm uit', 'image': 'screen-off.png', 'action': 'turn_screen_off'},
 {'id': 'in_bed_toggle',
  'text': "Zet 'in-bed' modus [in_bed_action]",
  'image': 'in-bed.png',
  'action': 'in_bed_toggle'},
 {'id': 'wifi_qr', 'text': 'Wifi QR code', 'image': 'wifi.png', 'action': 'wifi_qr'},
 {'id': '3d_printer_progress',
  'text': 'Check 3D print status',
  'image': '3d-object.png',
  'action': '3d_printer_status'},
 {'id': '3d_printer_cam', 'text': '3D printer cam', 'image': 'camera.png', 'action': '3d_printer_cam'},
 {'id': 'system_options',
  'text': 'Opties',
  'image': 'system.png',
  'action': 'system_options',
  'screen': [{'id': 'options_back', 'text': 'Terug', 'image': 'back.png', 'action': 'back'},
             {'id': 'show_weather_on_idle',
              'text': 'Toon weer als idle',
              'image': 'weather.png',
              'action': 'show_weather_on_idle'},
             {'id': 'verify_ssl_on_trusted_sources',
              'text': 'SSL verificatie',
              'image': 'shield.png',
              'action': 'verify_ssl_on_trusted_sources'},
             {'id': 'media_show_titles',
              'text': 'Toon media titels',
              'image': 'text.png',
              'action': 'media_show_titles'},
             {'id': 'media_sanitize_titles',
              'text': 'Schoon titels op',
              'image': 'text.png',
              'action': 'media_sanitize_titles'},
             {'id': 'force_update', 'text': 'Forceer UI refresh', 'image': 'tools.png', 'action': 'force_update'},
             {'id': 'enable_network_simulation',
              'text': 'Netwerk simulatie',
              'image': 'wifi.png',
              'action': 'enable_network_simulation'},
             {'id': 'store_settings', 'text': 'Store settings', 'image': 'system.png', 'action': 'store_settings'},
             {'id': 'quit', 'text': 'Sluit deze app', 'image': 'exit.png', 'action': 'exit'},
             {'id': 'shell_reboot', 'text': 'Reboot machine', 'image': 'shell.png', 'action': 'shell_reboot'},
             {'id': 'shell_shutdown', 'text': 'Shutdown machine', 'image': 'shell.png', 'action': 'shell_shutdown'}]}]

MINIMAL_MENU_SCHEMA = [
    {'id': 'music',
     'text': 'Muziek',
     'image': 'music.png',
     'action': 'music_menu',
     'screen': [{'id': 'music_back', 'text': 'Terug', 'image': 'back.png', 'action': 'back'},
                {'id': 'music_volume_up', 'text': 'Harder', 'image': 'volume-up.png', 'action': 'music_volume_up'},
                {'id': 'music_play_pause', 'text': '[music_action] muziek', 'image': 'play.png', 'action': 'music_play_pause'},
                {'id': 'music_volume_down', 'text': 'Zachter', 'image': 'volume-down.png', 'action': 'music_volume_down'},
                {'id': 'music_previous', 'text': 'Vorig nummer', 'image': 'backward.png', 'action': 'music_previous'},
                {'id': 'music_next', 'text': 'Volgend nummer', 'image': 'forward.png', 'action': 'music_next'},
                {'id': 'music_show_title',
                 'text': 'Toon muziek details',
                 'image': 'detail.png',
                 'action': 'music_show_title',
                 'cancel_close': True}]},
    {'id': 'smart_home_quick',
     'text': 'Smart Home',
     'image': 'tools.png',
     'action': 'open_page',
     'screen': [{'id': 'smart_home_quick_back', 'text': 'Terug', 'image': 'back.png', 'action': 'back'},
                {'id': 'calendar', 'text': 'Volgend kalender item', 'image': 'calendar.png', 'action': 'calendar'},
                {'id': 'doorbell', 'text': 'Voordeur', 'image': 'door.png', 'action': 'doorbell'}]},
    {'id': 'system_options',
     'text': 'Opties',
     'image': 'system.png',
     'action': 'system_options',
     'screen': [{'id': 'options_back', 'text': 'Terug', 'image': 'back.png', 'action': 'back'},
                {'id': 'show_weather_on_idle',
                 'text': 'Toon weer als idle',
                 'image': 'weather.png',
                 'action': 'show_weather_on_idle'},
                {'id': 'verify_ssl_on_trusted_sources',
                 'text': 'SSL verificatie',
                 'image': 'shield.png',
                 'action': 'verify_ssl_on_trusted_sources'},
                {'id': 'media_show_titles',
                 'text': 'Toon media titels',
                 'image': 'text.png',
                 'action': 'media_show_titles'},
                {'id': 'media_sanitize_titles',
                 'text': 'Schoon titels op',
                 'image': 'text.png',
                 'action': 'media_sanitize_titles'},
                {'id': 'force_update', 'text': 'Forceer UI refresh', 'image': 'tools.png', 'action': 'force_update'},
                {'id': 'enable_network_simulation',
                 'text': 'Netwerk simulatie',
                 'image': 'wifi.png',
                 'action': 'enable_network_simulation'},
                {'id': 'store_settings', 'text': 'Store settings', 'image': 'system.png', 'action': 'store_settings'},
                {'id': 'quit', 'text': 'Sluit deze app', 'image': 'exit.png', 'action': 'exit'},
                {'id': 'shell_reboot', 'text': 'Reboot machine', 'image': 'shell.png', 'action': 'shell_reboot'},
                {'id': 'shell_shutdown', 'text': 'Shutdown machine', 'image': 'shell.png', 'action': 'shell_shutdown'}]},
    {'id': 'screen_off', 'text': 'Zet scherm uit', 'image': 'screen-off.png', 'action': 'turn_screen_off'},
]


def _build_entry(schema_entry):
    button = MenuButton(
        schema_entry["id"],
        schema_entry["text"],
        schema_entry["image"],
        schema_entry["action"],
        cancel_close=bool(schema_entry.get("cancel_close", False)),
    )
    sub_schema = schema_entry.get("screen", [])
    return {
        "button": button,
        "screen": [_build_entry(child) for child in sub_schema],
    }


_BUTTON_SETTING_REQUIREMENTS = {
    "doorbell": ("mqtt_topic_doorbell",),
    "calendar": ("mqtt_topic_calendar",),
    "calendar_add": ("mqtt_topic_calendar",),
    "3d_printer_progress": ("mqtt_topic_printer_progress",),
    "3d_printer_cam": ("mqtt_topic_printer_progress",),
}


def _is_enabled_by_settings(button_id, settings):
    required_settings = _BUTTON_SETTING_REQUIREMENTS.get(button_id)
    if not required_settings:
        return True
    if settings is None:
        return True
    for key in required_settings:
        value = str(getattr(settings, key, "")).strip()
        if not value:
            return False
    return True


def _filter_schema_by_settings(entries, settings):
    filtered = []
    for entry in entries:
        button_id = entry.get("id")
        if not _is_enabled_by_settings(button_id, settings):
            continue

        cloned = copy.deepcopy(entry)
        children = cloned.get("screen") or []
        if children:
            children = _filter_schema_by_settings(children, settings)
            cloned["screen"] = children
            if cloned.get("action") == "open_page":
                has_actionable_child = any(child.get("action") != "back" for child in children)
                if not has_actionable_child:
                    continue

        filtered.append(cloned)
    return filtered


def build_menu_buttons(settings=None):
    profile = str(getattr(settings, "menu_profile", "full")).strip().lower() if settings is not None else "full"
    schema = MINIMAL_MENU_SCHEMA if profile == "minimal" else MENU_SCHEMA
    schema = _filter_schema_by_settings(schema, settings)
    return [_build_entry(entry) for entry in schema]
