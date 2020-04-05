import PySimpleGUI as sg

from helpers.enum import ModuleStatus

from ui.base import WindowBase

class MainWindow(WindowBase):

    theme_table = None

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.init_components()

    def init_components(self):
        title = f'{self.ui.app.appname} v{self.ui.app.version} by fluxdev'

        self.Title = title
        # self._Size = (500, 300)
        # self.NoTitleBar = True
        # self.GrabAnywhere = True
        # self.Resizable = True
        self.KeepOnTop = True
        self.ElementJustification = 'center'

        self.theme_table = sg.LOOK_AND_FEEL_TABLE[self.ui.config.get('Theme', self.ui.default_theme)]
         
        layout = []
            
        # Initialize module status
        modules_row = []
        for module in self.ui.app.subthread.values():
            module_text = module.module_id
            modules_row.append(sg.Text(text=module_text, key=f'status_{module_text}', font=('Consolas', 10), text_color='grey'))
        
        # modules_row.append(sg.Button('Options'))
        layout.append(modules_row)

        buttons = []
        for action in self.ui.app.actions:
            buttons.append([sg.Button(action.text, size=(30, 2), font=('Arial', 15), button_color=('white', 'brown'))])

        layout.append([sg.Column(buttons, justification='center', element_justification='center')])

        layout.append([sg.Text('Manual send:'), sg.Button('GPO'), sg.Button('HTTP')])
        layout.append([sg.Button('no errors reported', border_width=0, button_color=(self.get_theme_color('TEXT'), self.get_theme_color('BACKGROUND')))])

        # [sg.Combo(values=sg.theme_list(), size=(20, 1), default_value=self.ui.config.get('Theme', '( None )')), sg.Button('Change Theme')]

        self.layout(layout)
        self.Finalize()

    def get_theme_color(self, key):
        result = self.theme_table[key]
        if result == '1234567890':
            result = 'SystemButtonFace'
        
        return result

    def update_module_status(self):
        # if self.ui.app.tps is not None:
        #     self['tps'].update(f'TPS: {self.ui.app.tps:.2f}')

        for module_id in self.ui.app.module_status:
            status = self.ui.app.module_status[module_id]

            if status is ModuleStatus.ActivityRunning:
                self[f'status_{module_id}'].Update(text_color='white', background_color='green')
                self.ui.app.module_status[module_id] = ModuleStatus.Running
                continue

            if status is ModuleStatus.ActivityError or status is ModuleStatus.ActivityKeepError:
                self[f'status_{module_id}'].Update(text_color='white', background_color='red')
                self.ui.app.module_status[module_id] = ModuleStatus.Error if status is ModuleStatus.ActivityKeepError else ModuleStatus.Running
                continue

            if status is ModuleStatus.ActivityWarning or status is ModuleStatus.ActivityKeepWarning:
                self[f'status_{module_id}'].Update(text_color='white', background_color='orange')
                self.ui.app.module_status[module_id] = ModuleStatus.Warning if status is ModuleStatus.ActivityKeepWarning else ModuleStatus.Running
                continue
            
            if status is ModuleStatus.Running:
                self[f'status_{module_id}'].Update(text_color='green', background_color=self.get_theme_color('BACKGROUND'))
                continue

            if status is ModuleStatus.Error:
                self[f'status_{module_id}'].Update(text_color='red', background_color=self.get_theme_color('BACKGROUND'))
                continue

            if status is ModuleStatus.Warning:
                self[f'status_{module_id}'].Update(text_color='orange', background_color=self.get_theme_color('BACKGROUND'))
                continue
                
            if status is ModuleStatus.Initialized:
                self[f'status_{module_id}'].Update(text_color='white', background_color='grey')
                continue

    def handle_event(self, event, values):
        if event == 'Options':
                pass

        # if event == 'Change Theme':
        #     self.ui.app.config['Interface']['Theme'] = values[0]
        #     self.ui.app.save_config_file()
        #     self.ui.app.restart = True
        #     event = None

        elif event == 'GPO':
            self.ui.app.subthread.gpo.run_later('show_manual_send_window').run()

        elif event == 'HTTP':
            self.ui.app.subthread.httpclient.run_later('show_manual_send_window').run()

        else:
            for action in self.ui.app.actions:
                if event == action.text:
                    action.run()

    def process_func(self, event, values):
        if event is not None:
            self.update_module_status()
            self.handle_event(event, values)
        else:
            self.ui.app.shutdown()