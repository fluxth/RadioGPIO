from threads import SubThreadBase
import socket
import logging

import exceptions

class GPIOThread(SubThreadBase):
    socket = None
    config = {}

    def init(self):
        self.config = self.parent.config['Modules'].get(self.module_id, {})
        self.init_socket()

    def init_socket(self):
        protocol = self.config.get('Protocol', '')

        logging.debug(f'Initializing socket as protocol: {protocol}')

        if protocol == 'tcp':
            sock_type = socket.SOCK_STREAM
        elif protocol == 'udp':
            sock_type = socket.SOCK_DGRAM
        else:
            raise exceptions.FxConfigException(f'Protocol "{protocol}" not supported.', fatal=True)

        try:
            self.socket = socket.socket(socket.AF_INET, sock_type)
        except socket.error as e:
            raise exceptions.FxNetworkException(f'Error creating socket', e, fatal=True)

class GPIThread(GPIOThread):
    def listen(self):
        address = self.config.get('Listen', '')
        port = self.config.get('Port', 0)
        protocol = self.config.get('Protocol', '')

        logging.info(f'Listening for GPI on {protocol}://{address}:{port}')
        
        self.socket.bind((address, port))
        self.socket.listen(4)

class GPOThread(GPIOThread):
    def init(self):
        super(GPOThread, self).init()

        self.connect()
        #self.show_manual_send_dialog()

    def show_manual_send_dialog(self):
        commands = self.config.get('OutputCommands', [])
        cmd_list = [ f"{self.module_id}: {cmd.get('Text', 'Unnamed')}" for cmd in commands ]

        self.parent.run_later('UI.gpo_manual_send')\
            .attach_callback(self.run_later('manual_send_callback').with_args)\
            .with_args(cmd_list)

    def manual_send_callback(self, val):
        if val is False:
            self.parent.run_later('shutdown').run()
        else:
            commands = self.config.get('OutputCommands', [])
            payload = None
            for command in commands:
                if '{}: {}'.format(self.module_id, command['Text']) == val:
                    payload = command.get('Payload', None)
                    break
        
            if payload is not None:
                self.send(payload)

            self.show_manual_send_dialog()

    def connect(self):
        address = self.config.get('Hostname', '')
        port = self.config.get('Port', 0)
        protocol = self.config.get('Protocol', '')

        logging.info(f'GPO will send on {protocol}://{address}:{port}')

        try:
            conn = self.socket.connect((address, port))
        except socket.gaierror as e:
            raise exceptions.FxConfigException(f'Hostname or address error', e, fatal=True)
        except socket.error as e:
            raise exceptions.FxNetworkException(f'Connection error', e)

    def send(self, data):

        if self.socket is None:
            return False

        encoding = self.config.get('Encoding', 'utf-8')
        separator = self.config.get('Separator', '').encode(encoding)

        if type(data) is str:
            data = data.encode(encoding)
        
        try:
            logging.debug(f'GPO sent data: {data}')
            self.socket.send(data + separator)
        except socket.error as e:
            raise exceptions.FxNetworkException(f'Error sending data', e)

        return True