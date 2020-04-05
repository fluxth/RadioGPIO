import logging
import ipaddress
import requests

from threads import SubThreadBase

import exceptions
from ui.http import HTTPManualSendWindow
from helpers.enum import ModuleStatus, ModuleIOType

class HTTPThread(SubThreadBase):
    config = {}

    allowed_methods = ('GET', 'POST')
    command_required = ('Name', 'Url')

    def init(self):
        self.config = self.parent.config['Modules'].get(self.module_id, {})

        self.init_http_commands()

    def init_http_commands(self):
        for http_commands in self.config.get('OutputCommands', []):

            for required in self.command_required:
                if (val := http_commands.get(required, None)) is None or len(val.strip()) == 0:
                    raise exceptions.FxConfigException(f'HTTP command "{required}" must not be empty.', fatal=True)

            if (method := http_commands.get('Method', 'GET').upper()) not in self.allowed_methods:
                raise exceptions.FxConfigException(f'HTTP method "{method}" not supported.', fatal=True)

    def cleanup(self):
        pass
        

class HTTPServerThread(HTTPThread):

    module_io_type: ModuleIOType = ModuleIOType.Input

    # Copy from GPIThread
    pass

class HTTPClientThread(HTTPThread):

    module_io_type: ModuleIOType = ModuleIOType.Output

    def init(self):
        super(HTTPClientThread, self).init()

        self.initialized = True

    def show_manual_send_window(self):
        commands = self.config.get('OutputCommands', [])
        data = {
            'cmd_list': [ f"{self.module_id}: {cmd.get('Text', 'Unnamed')}" for cmd in commands ],
            'callback_safe': self.run_later('manual_send_callback').with_args
        } 

        self.parent.UI.create_window_later(HTTPManualSendWindow, user_data=data)

    def manual_send_callback(self, val):
        commands = self.config.get('OutputCommands', [])
        send_cmd = None
        for command in commands:
            if '{}: {}'.format(self.module_id, command['Text']) == val:
                send_cmd = command
                break
    
        if send_cmd is not None:
            self.send(send_cmd)

        # self.show_manual_send_window()

    def run_output_command_handler(self, output_command):
        # TODO: Make more efficient
        commands = self.config.get('OutputCommands', [])
        for command in commands:
            if command.get('Name', '') == output_command:
                self.send(command)
                break

    def send(self, http_command):
        method = http_command.get('Method', 'GET')
        url = http_command.get('Url', None)

        self.parent.update_module_status(self, ModuleStatus.ActivityRunning)
            
        exc = None
        try:
            if method == 'GET':
                return self.sendGet(url)
            elif method == 'POST':
                payload = http_command.get('Payload', None)
                return self.sendPost(url, payload)

        except requests.exceptions.HTTPError as e:
            exc = ('HTTP', e)
        except requests.exceptions.ConnectionError as e:
            exc = ('connection', e)
        except requests.exceptions.Timeout as e:
            exc = ('timeout', e)
        except requests.exceptions.RequestException as e:
            exc = ('an', e)

        if exc is not None:
            self.parent.update_module_status(self, ModuleStatus.ActivityError)
            self.parent.run_later('UI.show_error').with_args(
                f'HTTPClient returned with {exc[0]} error:',
                f'Additional Information:\n{exc[1]}'
            )

        return False

    def sendGet(self, url):
        logging.info(f'HTTPClient sent GET request to {url}')
        return requests.get(url).raise_for_status()

    def sendPost(self, url, data, content_type=None):
        logging.info(f'HTTPClient sent POST request to {url}, data={data}')
        return requests.post(url, data=data).raise_for_status()