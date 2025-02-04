"""
ZiboCabinTemp
X-Plane plugin

Copyright (c) 2023, Antonio Golfari
All rights reserved.

This source code is licensed under the BSD-style license found in the
LICENSE file in the root directory of this source tree. 
"""

import json

from datetime import datetime, timedelta
from time import perf_counter
from pathlib import Path

try:
    from XPPython3 import xp
except ImportError:
    print('xp module not found')
    pass


# Version
__VERSION__ = 'v1.2-beta.1'

# Plugin parameters required from XPPython3
plugin_name = 'ZiboCabinTemp'
plugin_sig = 'xppython3.zibocabintemp'
plugin_desc = 'Simple Python script to get a feedback about Zibo cabin temperature'

# Other parameters
DEFAULT_SCHEDULE = 10  # positive numbers are seconds, 0 disabled, negative numbers are cycles
DEFAULT_DELTA_TIME = 5  # how often a message can repeat, minutes
DEFAULT_COMFORT_TEMP = 21  # degrees C
DELTA_COMFORT = 2  # degrees C
DELTA_REQUEST = 4  # degrees C
DELTA_LIMIT = 8  # degrees C

# Aural messages
VERY_HOT_MESSAGE = "it's really hot in the cabin"
TOO_HOT_MESSAGE = "could we cool down the cabin a bit please?"
TOO_COLD_MESSAGE = "passengers are asking for a cozier temperature"
VERY_COLD_MESSAGE = "we are freezing in the cabin"

# Aircrafts
AIRCRAFTS = [
    ('Zibo', 'B737-800X'),
    ('LevelUp', 'LevelUp')
]

# widget parameters
try:
    FONT = xp.Font_Proportional
    FONT_WIDTH, FONT_HEIGHT, _ = xp.getFontDimensions(FONT)
except NameError:
    FONT_WIDTH, FONT_HEIGHT = 10, 10

LINE = FONT_HEIGHT + 4
WIDTH = 280
HEIGHT = 200
HEIGHT_MIN = 100
MARGIN = 10
HEADER = 12


def time_passed(event: datetime) -> bool:
    return datetime.now() - event > timedelta(minutes=DEFAULT_DELTA_TIME)


def check_temperature(temp: float, comfort_temp: float) -> str:
    delta = temp - comfort_temp
    if delta < - DELTA_LIMIT:
        return VERY_COLD_MESSAGE
    elif delta <= - DELTA_REQUEST:
        return TOO_COLD_MESSAGE
    elif delta > DELTA_LIMIT:
        return VERY_HOT_MESSAGE
    elif delta >= DELTA_REQUEST:
        return TOO_HOT_MESSAGE
    else:
        return ''


class Dref(object):

    def __init__(self) -> None:
        self._cabin_temp_dref = xp.findDataRef('laminar/B738/cabin_temp')
        self._leg_started_dref = xp.findDataRef('laminar/b738/fmodpack/leg_started')

    @property
    def cabin_temp(self) -> float | bool:
        try:
            return round(xp.getDataf(self._cabin_temp_dref), 1)
        except SystemError as e:
            xp.log(f"ERROR: {e}")
            return False

    @property
    def pax_onboard(self) -> bool:
        try:
            return bool(xp.getDatai(self._leg_started_dref))
        except SystemError:
            return False


class PythonInterface(object):

    def __init__(self) -> None:
        self.plugin_name = f"{plugin_name} - {__VERSION__}"
        self.plugin_sig = plugin_sig
        self.plugin_desc = plugin_desc

        # folders init
        self.prefs = Path(xp.getPrefsPath()).parent

        # Dref init
        self.dref = False

        # app init
        self.latest_request_time = None
        self.config_file = Path(self.prefs, 'zibocabintemp.prf')
        self.enabled = True
        self.comfort_temp = DEFAULT_COMFORT_TEMP
        self.load_settings()

        # widget
        self.settings_widget = None
        self.message = ""  # text displayed in widget info_line

        # create main menu and widget
        self.main_menu = self.create_main_menu()

        self.aircraft = False
        self.acf_path = None

    @property
    def aircraft_path(self) -> str:
        _, acf_path = xp.getNthAircraftModel(0)
        return acf_path

    @property
    def aircraft_detected(self) -> bool:
        self.check_aircraft()
        return bool(self.aircraft)

    @property
    def time_to_check(self) -> bool:
        return self.latest_request_time and time_passed(self.latest_request_time)

    def show_info_widget(self) -> None:
        if not xp.isWidgetVisible(self.info_widget):
            for widget in (self.cabin_cap, self.cabin_temp_widget, self.comfort_delta_cap, self.comfort_delta_widget):
                xp.showWidget(widget)
            xp.showWidget(self.info_widget)

    def hide_info_widget(self) -> None:
        if xp.isWidgetVisible(self.info_widget):
            for widget in (self.cabin_cap, self.cabin_temp_widget, self.comfort_delta_cap, self.comfort_delta_widget):
                xp.hideWidget(widget)
            xp.hideWidget(self.info_widget)

    def check_aircraft(self) -> None:
        _, acf_path = xp.getNthAircraftModel(0)
        if acf_path != self.acf_path:
            self.acf_path = acf_path
            acf = next((p[0] for p in AIRCRAFTS if p[1] in self.acf_path), None)
            if acf:
                self.aircraft = acf
                # load drefs if needed
                if not self.dref:
                    self.dref = Dref()
            else:
                self.aircraft = False
                self.dref = False

    def create_main_menu(self):
        # create Menu
        menu = xp.createMenu('ZiboCabinTemp', handler=self.main_menu_callback)
        # add Menu Items
        xp.appendMenuItem(menu, 'Settings', 1)
        return menu

    def main_menu_callback(self, menuRef, menuItem):
        """Main menu Callback"""
        if menuItem == 1:
            if not self.settings_widget:
                self.create_settings_widget(400, 1000)
            elif not xp.isWidgetVisible(self.settings_widget):
                xp.showWidget(self.settings_widget)

    def create_settings_widget(self, x: int = 400, y: int = 1000):

        left, top, right, bottom = x + MARGIN, y - HEADER - MARGIN, x + WIDTH - MARGIN, y - HEIGHT + MARGIN

        # main windows
        self.settings_widget = xp.createWidget(
            x, y, x+WIDTH, y-HEIGHT,
            1, f"ZiboCabinTemp {__VERSION__}", 1, 0, xp.WidgetClass_MainWindow
        )
        xp.setWidgetProperty(self.settings_widget, xp.Property_MainWindowHasCloseBoxes, 1)
        xp.setWidgetProperty(self.settings_widget, xp.Property_MainWindowType, xp.MainWindowStyle_Translucent)

        t = top
        # info message line
        self.info_line = xp.createWidget(
            left, top, right, top - LINE,
            1, "", 0, self.settings_widget, xp.WidgetClass_Caption
        )
        xp.setWidgetProperty(self.info_line, xp.Property_CaptionLit, 1)

        t -= (LINE + MARGIN)
        b = t - 2*LINE - 3*MARGIN
        # Temp info sub window
        self.info_widget = xp.createWidget(
            left, t, right, b,
            1, "", 0, self.settings_widget, xp.WidgetClass_SubWindow
        )
        xp.setWidgetProperty(self.info_widget, xp.Property_SubWindowType, xp.SubWindowStyle_SubWindow)
        t -= MARGIN
        l = left + MARGIN
        r = right - MARGIN
        self.cabin_cap = xp.createWidget(
            l, t, l + 160, t - LINE,
            1, 'cabin temperature (°C):', 0, self.settings_widget, xp.WidgetClass_Caption
        )
        # xp.setWidgetProperty(self.cabin_cap, xp.Property_CaptionLit, 1)
        self.cabin_temp_widget = xp.createWidget(
            l + 175, t, r, t - LINE,
            1, '', 0, self.settings_widget, xp.WidgetClass_Caption
        )
        # xp.setWidgetProperty(self.cabin_temp_widget, xp.Property_CaptionLit, 1)

        t -= (LINE + MARGIN)
        self.comfort_delta_cap = xp.createWidget(
            l, t, l + 160, t - LINE,
            1, 'comfort delta (°C):', 0, self.settings_widget, xp.WidgetClass_Caption
        )
        self.comfort_delta_widget = xp.createWidget(
            l + 175, t, r, t - LINE,
            1, '', 0, self.settings_widget, xp.WidgetClass_Caption
        )

        t = b - MARGIN
        cap = xp.createWidget(
            left, t, left + 160, t - LINE,
            1, 'OPTIONS', 0, self.settings_widget, xp.WidgetClass_Caption
        )
        xp.setWidgetProperty(cap, xp.Property_CaptionLit, 1)
        t -= (LINE + MARGIN)
        cap = xp.createWidget(
            left, t, left + 160, t - LINE,
            1, 'FA calls:', 0, self.settings_widget, xp.WidgetClass_Caption
        )
        xp.setWidgetProperty(cap, xp.Property_CaptionLit, 1)
        self.enable_check = xp.createWidget(
            left + 225, t, right, t - LINE,
            1, '', 0, self.settings_widget, xp.WidgetClass_Button
        )
        xp.setWidgetProperty(self.enable_check, xp.Property_ButtonState, xp.RadioButton)
        xp.setWidgetProperty(self.enable_check, xp.Property_ButtonBehavior, xp.ButtonBehaviorCheckBox)
        xp.setWidgetProperty(self.enable_check, xp.Property_ButtonState, self.enabled)

        t -= (LINE + MARGIN)
        cap = xp.createWidget(
            left, t, left + 175, t - LINE,
            1, 'comfort temperature (°C):', 0, self.settings_widget, xp.WidgetClass_Caption
        )
        xp.setWidgetProperty(cap, xp.Property_CaptionLit, 1)
        self.comfort_t_input = xp.createWidget(
            left + 175, t, left + 210, t - LINE,
            1, '', 0, self.settings_widget, xp.WidgetClass_TextField
        )
        xp.setWidgetProperty(self.comfort_t_input, xp.Property_MaxCharacters, 2)
        xp.setWidgetProperty(self.comfort_t_input, xp.Property_TextFieldType, xp.TextTranslucent)
        xp.setWidgetDescriptor(self.comfort_t_input, str(self.comfort_temp))

        self.comfort_t_button = xp.createWidget(
            left + 225, t, right, t - LINE,
            1, "set", 0, self.settings_widget, xp.WidgetClass_Button
        )

        # Register our widget handler
        self.settingsWidgetHandlerCB = self.settingsWidgetHandler
        xp.addWidgetCallback(self.settings_widget, self.settingsWidgetHandlerCB)

    def settingsWidgetHandler(self, inMessage, inWidget, inParam1, inParam2):
        if xp.getWidgetDescriptor(self.info_line) != self.message:
            xp.setWidgetDescriptor(self.info_line, self.message)

        if self.aircraft_detected and self.dref:
            temp = str(self.dref.cabin_temp)
            if xp.getWidgetDescriptor(self.cabin_temp_widget) != temp:
                xp.setWidgetDescriptor(self.cabin_temp_widget, temp)
            delta = str(round(self.dref.cabin_temp - self.comfort_temp, 1))
            if xp.getWidgetDescriptor(self.comfort_delta_widget) != delta:
                xp.setWidgetDescriptor(self.comfort_delta_widget, delta)
            self.show_info_widget()
        else:
            self.hide_info_widget()

        if inMessage == xp.Message_CloseButtonPushed:
            if self.settings_widget:
                xp.hideWidget(self.settings_widget)
                return 1

        if inMessage == xp.Msg_PushButtonPressed and inParam1 == self.comfort_t_button:
            try:
                self.comfort_temp = int(xp.getWidgetDescriptor(self.comfort_t_input).strip())
            except ValueError as e:
                xp.log(f"Error in comfort temp input: {e}")
                xp.setWidgetDescriptor(self.comfort_t_input, str(self.comfort_temp))
            xp.loseKeyboardFocus(self.comfort_t_input)
            return 1

        if inMessage == xp.Msg_ButtonStateChanged and inParam1 == self.enable_check:
            self.enabled = bool(xp.getWidgetProperty(self.enable_check, xp.Property_ButtonState))
            return 1

        return 0

    def load_settings(self) -> bool:
        if self.config_file.is_file():
            # read file
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = f.read()
            # parse file
            settings = json.loads(data)
            if settings:
                self.enabled = settings.get('settings').get('enabled')
                self.comfort_temp = settings.get('settings').get('comfort_temp')
        else:
            # keep default values
            return False

    def save_settings(self) -> None:
        settings = {'settings': {'enabled': self.enabled, 'comfort_temp': self.comfort_temp}}
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f)

    def loopCallback(self, lastCall, elapsedTime, counter, refCon):
        """Loop Callback"""
        t = datetime.now()
        start = perf_counter()
        if self.aircraft_detected and self.dref:
            cabin_temp = self.dref.cabin_temp
            if self.dref.pax_onboard:
                message = check_temperature(cabin_temp, self.comfort_temp)
                if not self.latest_request_time:
                    # boarding just started
                    self.latest_request_time = t
                    self.message = "Boarding started ..."
                    if self.enabled:
                        comm = "we are starting boarding now"
                        if message:
                            comm += ". Please, make sure the cabin is conditioned"
                            xp.speakString(f"Captain, {comm}")
                elif self.time_to_check:
                    self.latest_request_time = t
                    if message:
                        self.message = message
                        if self.enabled:
                            xp.speakString(f"Captain, {message}")
            elif self.latest_request_time:
                # reset for turnaround
                self.latest_request_time = None
                self.message = "Passengers disembarked"
            else:
                self.message = "Boarding not started yet ..."
        else:
            self.message = "Zibo not detected"

        return DEFAULT_SCHEDULE

    def XPluginStart(self):
        return self.plugin_name, self.plugin_sig, self.plugin_desc

    def XPluginEnable(self):
        # loopCallback
        self.loop = self.loopCallback
        self.loop_id = xp.createFlightLoop(self.loop, phase=1)
        xp.scheduleFlightLoop(self.loop_id, interval=DEFAULT_SCHEDULE)
        return 1

    def XPluginDisable(self):
        pass

    def XPluginStop(self):
        # Called once by X-Plane on quit (or when plugins are exiting as part of reload)
        xp.destroyFlightLoop(self.loop_id)
        self.save_settings()
        xp.destroyWidget(self.settings_widget)
        xp.destroyMenu(self.main_menu)
        xp.log("settings saved, flightloop, widget, menu destroyed, exiting ...")
