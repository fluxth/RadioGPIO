import PySimpleGUI as sg

from ui.base import WindowBase

class HTTPManualSendWindow(WindowBase):
    def __init__(self, *args, **kwargs):
        super(HTTPManualSendWindow, self).__init__(*args, **kwargs)
        self.init_components()

    def init_components(self):
        self.Title = 'HTTP Manual Send'
        self.KeepOnTop = True

        self.layout([  
            [
                sg.Text('Output Command:'), 
                sg.Combo(values=self.user_data['cmd_list'], size=(40, 1), default_value='( None )')
            ],
            [sg.OK(), sg.Cancel()]
        ])

    def process_func(self, event, values):
        if event in (None, 'Cancel'):
            self.ui.close_window(self)
        elif event == 'OK':
            self.user_data['callback_safe'](values[0])
            self.ui.close_window(self)
