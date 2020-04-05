import PySimpleGUI as sg
import logging

import exceptions
from helpers import Map
from ui.app import MainWindow
from ui.gpio import GPOManualSendWindow

class FxGpioUI():
    simple_init: bool = False
    fill_init: bool = False

    app = None
    config: dict = None

    main_window: MainWindow = None
    window: list = []

    default_theme: str = 'SystemDefault'
    target_tick_length: int = 50

    def __init__(self, app):
        self.app = app
        sg.theme(self.default_theme)

        self.simple_init = True

    def post_init(self):
        self.config = self.app.config.get('Interface', {})
        
        self.full_init = True
        self.set_theme(self.config.get('Theme', None))

    def set_theme(self, theme):
        if theme is None or theme == '':
            return False

        if theme in sg.theme_list():
            return sg.theme(theme)

        raise exceptions.FxUIException(f'Theme "{theme}" could not be loaded.')

    def app_start(self):
        self.main_window = MainWindow(ui=self)

        # menu_def = ['BLANK', ['&Open', '---', '&Save', ['1', '2', ['a', 'b']], '&Properties', 'E&xit']]
        # self.tray = sg.SystemTray(menu=menu_def, data_base64=sg.DEFAULT_BASE64_ICON)

    def show_alert(self, *args, **kwargs):
        return sg.Popup(*args, no_titlebar=True, keep_on_top=True, grab_anywhere=True, **kwargs)

    def show_error(self, *args, **kwargs):
        kwargs['button_color'] = ('white', 'red')
        return self.show_alert(*args, **kwargs)

    def create_window_later(self, *args, **kwargs):
        self.app.run_later('UI.create_window').with_args(*args, **kwargs)

    def create_window(self, win_class, *args, user_data=None, **kwargs):
        window = win_class(*args, **kwargs, ui=self, user_data=user_data)

        create = True
        count = 0
        for win in self.window:
            if type(win) is win_class:
                count += 1
                max_inst = window.max_instance
                if count >= max_inst:
                    create = False
                    logging.error(f'Cannot create more than {max_inst} instance of {win_class.__name__}')
                    win.BringToFront()
                    break

        if create:
            self.window.append(window)

    def close_window(self, window_obj):
        retval = window_obj.close()
        self.window.remove(window_obj)
        return retval

    def calculate_tick_length(self, pad=1):
        return self.target_tick_length // ( len(self.window) + pad )

    def ui_tick(self):

        # TODO: Make this a property instead, reduce CPU
        tick_length = self.calculate_tick_length(pad=1)

        # MainWindow
        event, values = self.main_window.Read(timeout=tick_length)
        self.main_window.process_func(event, values)

        # self.tray.Read(timeout=100)

        # SubWindows
        for win in self.window:
            event, values = win.Read(timeout=tick_length)
            win.process_func(event, values)

    def shutdown(self):
        for win in self.window:
            self.close_window(win)

        self.main_window.close()