import PySimpleGUI as sg

class WindowBase(sg.Window):
    ui = None
    user_data = None
    max_instance = 1

    def __init__(self, *args, ui=None, user_data=None, **kwargs):
        super(WindowBase, self).__init__('Window', *args, **kwargs)
        self.ui = ui
        self.user_data = user_data

    def process_func(self, event, values):
        if event is None:
            self.ui.close_window(self)