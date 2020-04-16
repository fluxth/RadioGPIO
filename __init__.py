import threading
import logging
import time
import json
import os
import codecs

import exceptions
from ui import FxGpioUI
from threads import ThreadBase, FxQueueItem
from threads.gpio import GPIThread, GPOThread
from threads.http import HTTPClientThread, HTTPServerThread
from threads.livewire import LivewireThread

import PySimpleGUI as sg

from helpers import Map, multi_getattr
from helpers.enum import ModuleStatus
from helpers.app import ModuleIterator, terminate_process
from action import Action

class FxGpioApp(ThreadBase):

    # AppName
    appname: str = 'RadioGPIO'

    # AppVersion
    version: str = '0.0.1'

    # ThreadName
    name: str = 'MainThread'

    # run dir
    run_dir: str = None

    # SubThreads
    subthread: Map = None
    module_status: dict = None

    # ActionsList
    actions: list = None

    UI = None

    initialized = False

    last_tick = None
    tps = None

    is_mainthread = True

    queue_blocking: bool = False
    queue_rate: int = 0
    queue_cooldown: float = 0

    config_file = './config.json'
    config = {
        'Interface': {
            'Theme': 'SystemDefault',
            'Buttons': {
                'Width': 2,
                'Height': 20,
                'Columns': [],
            },
            'Keyboard': {},
        },
        'Actions': [],
        'Modules': {
            'GPI': {
                'Enabled': True,
                'Protocol': 'tcp',
                'Listen': '0.0.0.0',
                'Port': 9310,
                'KeepOpen': False,
                'Encoding': 'utf-8',
                'Separator': '\n',
                'AllowedIP': [
                    '127.0.0.0/8',
                ],
                'InputCommands': [],
            },
            'GPO': {
                'Enabled': True,
                'Protocol': 'tcp',
                'Hostname': '192.168.0.1',
                'Port': 9310,
                'Encoding': 'utf-8',
                'Separator': '\n',
                'OutputCommands': [],
            },
            'HTTPClient': {
                'Enabled': True,
            },
            'Livewire': {
                'Enabled': True,
            },
        }
    }

    module_map = (
        ('GPI', GPIThread),
        ('GPO', GPOThread),
        ('HTTPClient', HTTPClientThread),
        ('HTTPServer', HTTPServerThread),
        ('Livewire', LivewireThread),
    )

    def __init__(self, run_dir, *args, **kwargs):
        super(FxGpioApp, self).__init__(*args, **kwargs)

        self.run_dir = run_dir
        self.init_properties()

        logging.debug(f'Initializing main app...')

        sg.popup_quick_message(f'Initializing {self.appname}...', background_color='black', text_color='white', auto_close=True, non_blocking=True)
        self.init_app()
        self.initialized = True

    def init_properties(self):
        self.restart = False
        self.subthread = Map({})
        self.actions = []
        self.module_status = {}

    def init_app(self):
        init_sequence = (
            { 'method': 'init_settings' },
            { 'method': 'init_ui' },
            { 'method': 'init_config' },
            { 'method': 'UI.post_init' },
            { 'method': 'init_subthreads' },
            { 'method': 'init_actions' },
        )

        for init_ptr in init_sequence:
            try:
                init = multi_getattr(self, init_ptr['method'])
                init(*init_ptr.get('args', ()), **init_ptr.get('kwargs', {}))
            except exceptions.FxBaseException as e:
                logging.error(e.get_caught_str())
                if type(self.UI) is FxGpioUI and self.UI.simple_init:
                    self.UI.show_error(
                        f'{self.appname} failed to initialize.', 
                        e.get_alert_str(),
                        custom_text=('Exit' if e.fatal else 'OK')
                    )  

                if e.fatal:
                    terminate_process(1)
                else:
                    continue

    def init_settings(self):
        logging.debug('Initializing internal settings...')

    def init_ui(self):
        logging.debug('Initializing user interface...')
        self.UI = FxGpioUI(self)

    def init_config(self):
        logging.debug('Initializing configuration...')
        if not os.path.isfile(self.config_file):
            msg = f'Configuration file "{self.config_file}" not found, creating a default one and exiting...'

            logging.warning(msg)
            self.save_config_file()
            
            self.UI.show_alert(f'{self.appname} Information', msg, custom_text='Exit')
            terminate_process(0)

        else:
            logging.debug(f'Loading configuration from "{self.config_file}"...')
            self.load_config_file()
        
    def save_config_file(self):
        logging.debug('Saving current configuration to file')
        with codecs.open(self.config_file, 'w', 'utf-8') as f:
            json.dump(self.config, f, indent=4)

    def load_config_file(self):
        logging.debug('Loading configuration from file')
        with codecs.open(self.config_file, 'r', 'utf-8') as f:
            try:
                self.config = json.load(f)
            except json.decoder.JSONDecodeError as e:
                raise exceptions.FxConfigException('Unable to load configuration', e, fatal=True)

    def iterate_modules(self):
        module_config = self.config.get('Modules', {})
        return iter(ModuleIterator(module_config, self.module_map))

    def init_actions(self):
        actions = self.config.get('Actions', [])

        for action in actions:
            self.actions.append(Action(self, action))

    def init_subthreads(self):
        logging.debug('Initializing subthreads...')
        
        for module in self.iterate_modules():
            module_id = module[0]
            self.subthread[module_id.lower()] = module[1](self, module_id)

    def start_subthreads(self):
        logging.info('Starting subthreads...')

        for module in self.subthread.values():
            module.start()

    def shutdown_subthreads(self):
        logging.info('Stopping subthreads...')

        for module in self.subthread.values():
            module.run_later('shutdown').run()

    def pre_start(self):
        logging.info(f'Starting {self.appname} v{self.version}...')
        self.start_subthreads()
        self.UI.app_start()

    def tick(self):
        self.UI.ui_tick()

        cur_time = time.time_ns() // 1000000
        if self.last_tick is not None:
            self.tps = 1000 / (cur_time-self.last_tick)

        self.last_tick = cur_time
        # print(self.tps)

    def run(self):
        if not self.initialized:
            return 1

        super(FxGpioApp, self).main_loop()
        return self.post_shutdown()

    def run_action(self, action_name):
        for action in self.actions:
            if action.name == action_name:
                return action.run()

    def run_action_later(self, *args, **kwargs):
        return self.run_later('run_action').with_args(*args, **kwargs)

    def update_module_status(self, module, status, update_if=None):
        prev_status = self.module_status.get(module.module_id, None)
        if update_if is not None:
            if not update_if == prev_status:
                return False

        self.module_status[module.module_id] = status
        return status

    def update_module_status_later(self, *args, **kwargs):
        return self.run_later('update_module_status').with_args(*args, **kwargs)

    def shutdown(self, by_exception=False):
        if self.exit:
            return

        logging.warning(f'{self.appname} shutting down!')
        
        self.shutdown_subthreads()
        self.UI.shutdown()
        self.exit = True

        if by_exception:
            return self.post_shutdown()

    def post_shutdown(self):
        logging.debug('Waiting for all threads to shutdown...')

        for module in self.subthread.values():
            module.join(10)

        self.UI.post_shutdown()

        logging.info('Main thread exiting.')
        return 0