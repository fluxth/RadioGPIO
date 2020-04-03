import threading
import logging
import time
import os.path
import json
import sys

import exceptions
from ui import FxGpioUI
from threads import ThreadBase, FxQueueItem
from threads.gpio import GPIThread, GPOThread

import PySimpleGUI as sg

from helpers import Map, multi_getattr

def terminate_process(exit_code):
    logging.info(f'Process terminating with exit code {exit_code}.')
    sys.exit(exit_code)

class ModuleIterator:
    def __init__(self, config, module_map):
        self.config = config
        self.module_map = module_map

    def __iter__(self):
        self.index = 0
        return self

    def __next__(self):
        while self.index < len(self.config):
            value = None
            
            module = self.module_map[self.index]
            key = module[0]
            if self.config[key].get('Enabled', False) is True:
                value = module

            self.index += 1
            if value is not None and value[1] is not None:
                return value

        if self.index >= len(self.config):
            raise StopIteration

class FxGpioApp(ThreadBase):

    # AppName
    appname: str = 'RadioGPIO'

    # AppVersion
    version: str = '1.0'

    # ThreadName
    name: str = 'MainThread'

    # SubThreads
    subthread: Map = Map()

    UI = None
    initialized = False

    last_tick = None
    tps = None

    is_mainthread = True
    queue_rate: int = 0
    queue_cooldown: float = 0

    config_file = './config.json'
    config = {
        'Interface': {
            'Theme': 'SystemDefault1',
            'Buttons': {},
            'Keyboard': {},
        },
        'Actions': [],
        'Modules': {
            'GPI': {
                'Enabled': True,
                'Protocol': 'tcp',
                'Listen': '0.0.0.0',
                'Port': 9310,
                'Encoding': 'utf-8',
                'Separator': '\n',
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
        ('HTTPClient', None),
        ('Livewire', None),
    )

    def __init__(self, *args, **kwargs):
        super(FxGpioApp, self).__init__(*args, **kwargs)

        self.restart = False

        logging.debug(f'Initializing main app...')
        self.init_app()
        self.initialized = True

    def init_app(self):
        init_sequence = (
            { 'method': 'init_settings' },
            { 'method': 'init_ui' },
            { 'method': 'init_config' },
            { 'method': 'UI.post_init' },
            { 'method': 'init_subthreads' },
        )

        for init_ptr in init_sequence:
            try:
                init = multi_getattr(self, init_ptr['method'])
                init(*init_ptr.get('args', ()), **init_ptr.get('kwargs', {}))
            except exceptions.FxBaseException as e:
                logging.error(e.get_caught_str())
                if type(self.UI) is FxGpioUI and self.UI.simple_init:
                    self.UI.show_error(
                        f'{self.appname} Initialization Error', 
                        e.get_alert_str(),
                        custom_text=('Exit' if e.fatal else 'OK')
                    )  

                if e.fatal:
                    terminate_process(1)
                else:
                    continue

    def init_settings(self):
        logging.debug('Initializing internal settings...')
        self.queue_blocking = False

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
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def load_config_file(self):
        logging.debug('Loading configuration from file')
        with open(self.config_file, 'r') as f:
            try:
                self.config = json.load(f)
            except json.decoder.JSONDecodeError as e:
                raise exceptions.FxConfigException('Unable to load configuration', e, fatal=True)

    def iterate_modules(self):
        module_config = self.config.get('Modules', {})
        return iter(ModuleIterator(module_config, self.module_map))

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
        self.UI.window_tick()

        cur_time = time.time_ns() // 1000000
        if self.last_tick is not None:
            self.tps = 1000 / (cur_time-self.last_tick)

        self.last_tick = cur_time

    def run(self):
        if not self.initialized:
            return 1

        super(FxGpioApp, self).main_loop()
        return self.post_shutdown()
    
    def closeEvent(self, event):
        self.shutdown()

    def shutdown(self, by_exception=False):
        if self.exit:
            return

        logging.warning(f'{self.appname} shutting down!')
        
        self.shutdown_subthreads()
        self.exit = True

        if by_exception:
            return self.post_shutdown()

    def post_shutdown(self):
        logging.debug('Waiting for all threads to shutdown...')

        for module in self.subthread.values():
            module.join(10)

        logging.info('Main thread exiting.')
        return 0

if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s', datefmt='%d %b %Y %H:%M:%S', level=logging.INFO)
    logging.debug('Logging initialized.')
    
    exit_code: int = 0

    while True:
        logging.info('Creating main application...')
        try:
            app = FxGpioApp()
            try:
                logging.debug('Running main app')
                exit_code = app.run()
            except KeyboardInterrupt:
                logging.warning('SIGINT Detected!')
                exit_code = app.shutdown(True)
        except Exception as e:
            logging.exception(e)
            raise

        if app.restart is True:
            logging.warning('Restart flag detected, restarting main app...')
            continue

        break

    terminate_process(exit_code)
