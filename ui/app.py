import PySimpleGUI as sg
import logging
import time

from helpers.enum import ModuleStatus, ModuleStatusMask, ModuleIOType

from ui.base import WindowBase
from ui.icons import APP_ICON_ICO_BASE64
from action import Action

class MainWindow(WindowBase):

    theme_table = None
    event_map = None

    actionbtn_active = []

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.init_event_map()
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
        self.SetIcon(icon=APP_ICON_ICO_BASE64)

        self.theme_table = sg.LOOK_AND_FEEL_TABLE[self.ui.config.get('Theme', self.ui.default_theme)]
        self.init_layout()

        self.Finalize()

    def init_action_buttons(self):
        btn_config = self.ui.config.get('Buttons', {})

        width = int(btn_config.get('Width', 20))
        height = int(btn_config.get('Height', 2))
        columns = btn_config.get('Columns', [])

        global_font = (btn_config.get('Font', 'Arial'), btn_config.get('FontSize', 16))
        global_color = (btn_config.get('TextColor', 'white'), btn_config.get('ButtonColor', 'brown'))

        output = []
        if len(columns) <= 0:
            # Render raw actions
            actions = self.ui.app.actions
            if len(actions) <= 0:
                # Give up, there is nothing
                return [sg.Text('No actions defined.', size=(40, 1), justification='center', pad=(0, 30), text_color='red')]

            columns = [actions]
        
        for col in columns:
            buttons = []

            for row in col:
                if type(row) is Action:
                    text = row.text
                    action = row.name
                else:
                    # TODO: Verify action exists!
                    text = row.get('Text', None)
                    action = row.get('Action', None)

                if text is None:
                    text = action

                if text is None:
                    logging.warning('Skip drawing an action button because not enough data.')
                    continue

                btn_color = (row.get('TextColor', global_color[0]), row.get('ButtonColor', global_color[1]))

                buttons.append([
                    sg.Button(
                        text,
                        key=f'action_btn.{action}',
                        size=(width, height), 
                        font=global_font,
                        button_color=btn_color,
                        metadata={
                            'color': btn_color
                        }
                    )
                ])

            output.append(sg.Column(buttons, element_justification='center', pad=(0, 10)))

        return output

    def init_layout(self):
        # Initialize module status display & menubar
        modules_row = []
        modules_menu = []
        for module in self.ui.app.subthread.values():
            module_text = module.module_id

            # Status display
            modules_row.append(sg.Text(text=module_text, key=f'status_{module_text}', font=('Consolas', 10), text_color='grey'))

            # Menubar
            modules_menu.append(module_text)

            submenu = []
            submenu.append(f'Reload::menu_reload.{module_text}')

            submenu.append('---')
            if module.module_io_type is ModuleIOType.Output or module.module_io_type is ModuleIOType.Bidirectional:
                submenu.append(f'Manual send::manual_send.{module_text}')

            if module.module_io_type is ModuleIOType.Input or module.module_io_type is ModuleIOType.Bidirectional:
                submenu.append(f'Test input::manual_send.{module_text}')

            modules_menu.append(submenu)

        # Initialize menubar
        menudef = [
            ['&Modules', modules_menu + ['---', 'Reload all::menu_reload._all']],
            ['&View', ['&Themes', [f'{t}::set_theme.{t}' for t in sg.theme_list()], '---', '&Log window']],
            ['&Help', [f'&About {self.ui.app.appname}']],
            ['&Close', ['&Minimize to taskbar', '&QUIT']],
        ]

        layout = [
            [sg.MenuBar(menudef)]
        ]
        
        # modules_row.append(sg.Button('Options'))
        layout.append(modules_row)

        layout.append(self.init_action_buttons())

        layout.append([sg.Text('Manual send:'), sg.Button('GPO'), sg.Button('HTTP'), sg.Text('TPS', key='tps', size=(7,1))])
        layout.append([sg.Button('no errors reported', border_width=0, button_color=(self.get_theme_color('TEXT'), self.get_theme_color('BACKGROUND')))])

        # [sg.Combo(values=sg.theme_list(), size=(20, 1), default_value=self.ui.config.get('Theme', '( None )')), sg.Button('Change Theme')]

        self.layout(layout)

    def get_theme_color(self, key):
        result = self.theme_table[key]
        if result == '1234567890':
            if key == 'TEXT':
                return 'black'
            return 'SystemButtonFace'
        
        return result

    def update_module_status(self):
        for module_id in self.ui.app.module_status:
            status = self.ui.app.module_status[module_id]

            if status == ModuleStatus.Running | ModuleStatus.Activity:
                self[f'status_{module_id}'].Update(text_color='white', background_color='green')
                self.ui.app.module_status[module_id] = ModuleStatus.Running
                continue

            if status == ModuleStatus.Error | ModuleStatus.Activity:
                self[f'status_{module_id}'].Update(text_color='white', background_color='red')
                if status & ModuleStatusMask.KeepActivityMask == ModuleStatus.KeepActivity:
                    self.ui.app.module_status[module_id] = ModuleStatus.Error
                else:
                    self.ui.app.module_status[module_id] = ModuleStatus.Running

                continue

            if status == ModuleStatus.Warning | ModuleStatus.Activity:
                self[f'status_{module_id}'].Update(text_color='white', background_color='orange')
                if status & ModuleStatusMask.KeepActivityMask == ModuleStatus.KeepActivity:
                    self.ui.app.module_status[module_id] = ModuleStatus.Warning
                else:
                    self.ui.app.module_status[module_id] = ModuleStatus.Running

                continue
            
            if status & ModuleStatusMask.StatusMask == ModuleStatus.Running:
                self[f'status_{module_id}'].Update(text_color='green', background_color=self.get_theme_color('BACKGROUND'))
                continue

            if status & ModuleStatusMask.StatusMask == ModuleStatus.Error:
                self[f'status_{module_id}'].Update(text_color='red', background_color=self.get_theme_color('BACKGROUND'))
                continue

            if status & ModuleStatusMask.StatusMask == ModuleStatus.Warning:
                self[f'status_{module_id}'].Update(text_color='orange', background_color=self.get_theme_color('BACKGROUND'))
                continue
                
            if status & ModuleStatusMask.StatusMask == ModuleStatus.Initialized:
                self[f'status_{module_id}'].Update(text_color='white', background_color='grey')
                continue

    def init_event_map(self):
        self.event_map = [
            ('action_btn',              self.action_btn_click),

            ('QUIT',                    self.ui.app.shutdown),
            ('Minimize to taskbar',     self.ui.close_main_window),

            ('GPO',                     self.ui.app.subthread.gpo.run_later('show_manual_send_window').run),
            ('HTTP',                    self.ui.app.subthread.httpclient.run_later('show_manual_send_window').run),

            ('set_theme',               self.set_theme),
        ]

    def set_theme(self, theme):
        self.ui.app.config['Interface']['Theme'] = theme
        self.ui.app.save_config_file()
        self.ui.app.restart = True
        self.ui.app.shutdown()

    def handle_event(self, event, values):
        if self.ui.app.tps is not None:
            self['tps'].update(f'TPS: {self.ui.app.tps:.2f}')

        args = []

        if '::' in event:
            event = event.split('::')[1]

        if '.' in event:
            elist = event.split('.')
            event = elist[0]
            args = elist[1:]

        for emap in self.event_map:
            if emap[0] == event:
                return emap[1](*args)

        for action in self.ui.app.actions:
            if event == action.text:
                return action.run()

        for key, active_btn in enumerate(self.actionbtn_active):
            if active_btn[0] > 0:
                self.actionbtn_active[key] = (active_btn[0] - 1, active_btn[1])
            else:
                self[active_btn[1]].Update(button_color=self[active_btn[1]].metadata['color'])
                self.actionbtn_active.remove(active_btn)

    def action_btn_click(self, action):
        self.ui.app.run_action(action)

    def action_ran(self, action):
        btnkey = f'action_btn.{action.name}'
        self[btnkey].Update(button_color=('red', 'yellow'))
        self.actionbtn_active.append((2, btnkey))

    def process_func(self, event, values):
        if event is not None:
            self.update_module_status()
            self.handle_event(event, values)
        else:
            self.ui.close_main_window()
            # self.ui.app.shutdown()