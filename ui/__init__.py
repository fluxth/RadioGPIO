import PySimpleGUI as sg

import exceptions
from helpers import Map
from ui.app import MainWindow

class FxGpioUI():
    simple_init: bool = False
    fill_init: bool = False

    app = None
    config: dict = None

    main_window: MainWindow = None
    window: Map = Map()

    default_theme: str = 'SystemDefault1'

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
        self.main_window = MainWindow(self)

        # menu_def = ['BLANK', ['&Open', '---', '&Save', ['1', '2', ['a', 'b']], '&Properties', 'E&xit']]
        # self.tray = sg.SystemTray(menu=menu_def, data_base64=sg.DEFAULT_BASE64_ICON)

    def show_alert(self, *args, **kwargs):
        return sg.Popup(*args, no_titlebar=True, grab_anywhere=True, **kwargs)

    def show_error(self, *args, **kwargs):
        kwargs['button_color'] = ('white', 'red')
        return self.show_alert(*args, **kwargs)

    def create_window(self, name, *args, **kwargs):
        self.window[name] = sg.Window(*args, **kwargs)
        return self.window[name]

    def close_window(self, name):
        return self.window[name].close()

    def window_tick(self):
        # self.tray.Read(timeout=100)
        event, value = self.main_window.Read(timeout=100)
        
        if self.app.tps is not None:
            self.main_window['tps'].update(f'TPS: {self.app.tps:.2f}')

        if event == 'Change Theme':
            self.app.config['Interface']['Theme'] = value[0]
            self.app.save_config_file()
            self.app.restart = True
            event = None

        if event is None:
            self.main_window.close()
            self.app.shutdown()

        # winkey = 'gpo_manual_send_dialog'
        # if winkey in self.window:
        #     ok = False

        #     event, values = self.window[winkey].Read(timeout=50)

        #     if event in (None, 'Cancel'):
        #         self.close_window(winkey)
        #         self.app.shutdown()
        #     elif event == 'OK':
        #         if values[0] != '':
        #             ok = values[0]
        #             self.close_window(winkey)

    def gpo_manual_send(self, cmd_list=[]):
        layout = [  
            [sg.Text('Send GPO to Zetta')],
            [
                sg.Text('Send Command:'), 
                sg.Combo(values=cmd_list, size=(30, 1), default_value='( None )')
            ],
            [sg.OK(), sg.Cancel()]
        ]

        self.create_window('gpo_manual_send_dialog', 'GPO Manual Send', layout)

