import PySimpleGUI as sg

class MainWindow(sg.Window):

    ui = None

    def __init__(self, ui, *args, **kwargs):
        self.ui = ui

        title = f'{self.ui.app.appname} v{self.ui.app.version} by fluxdev'
        super(MainWindow, self).__init__(title, *args, **kwargs)

        self.init_components()

    def init_components(self):
        self._Size = (500, 300)
        # self.NoTitleBar = True
        # self.GrabAnywhere = True
        self.Resizable = True
        self.layout([
            [sg.Text('MainWindow'), sg.Text(text='TPS', key='tps', size=(10, 1))],
            [sg.Combo(values=sg.theme_list(), size=(20, 1), default_value=self.ui.config.get('Theme', '( None )')), sg.Button('Change Theme')]
        ])