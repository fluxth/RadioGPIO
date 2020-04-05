import PySimpleGUI as sg
import logging
import textwrap

import exceptions
from helpers import Map
from ui.app import MainWindow
from ui.gpio import GPOManualSendWindow
from ui.icons import APP_ICON_PNG24_BASE64

class FxGpioUI():
    simple_init: bool = False
    fill_init: bool = False

    app = None
    config: dict = None

    main_window: MainWindow = None
    window: list = []

    main_window_shown: bool = True

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
        self.create_main_window()
        self.create_trayicon()

    def show_alert(self, *args, **kwargs):
        wrapper = textwrap.TextWrapper(width=100)

        new_args = list(args)
        for key, arg in enumerate(args):
            if type(arg) is str:
                new_args[key] = '\n'.join(wrapper.wrap(arg))

        return sg.Popup(*new_args, no_titlebar=True, keep_on_top=True, grab_anywhere=True, **kwargs)

    def show_error(self, *args, **kwargs):
        kwargs['button_color'] = ('white', 'red')
        return self.show_alert(*args, **kwargs)

    def notify(self, *args, **kwargs):
        pass
        # blocking
        # return self.tray.ShowMessage(self.app.appname, *args, **kwargs)
        # return sg.SystemTray.notify(self.app.appname, *args, **kwargs)

    def create_main_window(self):
        self.main_window = MainWindow(ui=self)
        self.main_window_shown = True

    def close_main_window(self):
        self.main_window_shown = False
        if self.main_window:
            self.main_window.close()
            del self.main_window

    def create_trayicon(self):
        tray_menu = ['TRAY MENU', [f'!{self.app.appname} v{self.app.version}', '---', '&Show/Hide GUI::toggle_gui', 'O&ptions', '---', '&Quit::quit']]
        self.tray = sg.SystemTray(menu=tray_menu, tooltip=self.app.appname, data_base64=APP_ICON_PNG24_BASE64)

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
        tick_pad = 2 # Pad MainWindow + Tray
        if not self.main_window_shown:
            tick_pad -= 1

        tick_length = self.calculate_tick_length(pad=tick_pad)

        # MainWindow
        if self.main_window_shown:
            event, values = self.main_window.Read(timeout=tick_length)
            self.main_window.process_func(event, values)

        # SubWindows
        for win in self.window:
            event, values = win.Read(timeout=tick_length)
            win.process_func(event, values)

        # Tray
        event = self.tray.Read(timeout=tick_length)
        if '::' in event:
            event = event.split('::')[1]

        if event == 'toggle_gui' or event == '__DOUBLE_CLICKED__':
            if not self.main_window_shown:
                self.create_main_window()
            else:
                self.close_main_window()

        elif event == 'quit':
            self.app.shutdown()

    def shutdown(self):
        for win in self.window:
            self.close_window(win)

        self.close_main_window()

    def post_shutdown(self):
        self.tray.close()