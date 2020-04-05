import socket
import logging
import ipaddress

from helpers import Map
from helpers.enum import ModuleStatus, ModuleIOType
from threads import SubThreadBase

from ui.gpio import GPOManualSendWindow

import exceptions

class GPIOThread(SubThreadBase):
    socket = None
    config = {}

    address: Map = None
    
    command_required = ('Name', 'Payload')

    def init(self):
        self.config = self.parent.config['Modules'].get(self.module_id, {})

        self.address = Map({})

        self.init_address()
        self.init_gpio_commands()
        self.init_socket()

    def init_address(self):
        if self.module_id == 'GPI':
            self.address['hostname'] = self.config.get('Listen', '')
        elif self.module_id == 'GPO':
            self.address['hostname'] = self.config.get('Hostname', '')

        self.address['port'] = self.config.get('Port', 0)
        self.address['protocol'] = self.config.get('Protocol', '')

    def init_gpio_commands(self):
        for gpio_commands in self.config.get('OutputCommands', []):

            for required in self.command_required:
                if (val := gpio_commands.get(required, None)) is None or len(val.strip()) == 0:
                    raise exceptions.FxConfigException(f'GPIO command "{required}" must not be empty.', fatal=True)


    def init_socket(self):
        protocol = self.address.protocol

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

        # Check ip validity in whitelist
        whitelist_str = self.config.get('AllowedIP', [])
        self.address['whitelist'] = []
        for addr_str in whitelist_str:
            try:
                self.address.whitelist.append(ipaddress.IPv4Network(addr_str))
                logging.debug(f'{self.module_id} whitelist address valid: {addr_str}')
            except (ValueError, ipaddress.AddressValueError) as e:
                raise exceptions.FxConfigException(f'{self.module_id} whitelist address invalid: {addr_str}', e, fatal=True)

    def cleanup(self):
        self.socket.close()
        

class GPIThread(GPIOThread):

    module_io_type: ModuleIOType = ModuleIOType.Input

    queue_blocking: bool = False
    queue_rate: int = 2 # Hz

    conn_backlogs: int = 4
    recv_buffer: int = 1024

    def init(self):
        super(GPIThread, self).init()

        # TODO: Implement keep open listener
        if self.config.get('KeepOpen', False):
            raise exceptions.FxConfigException('GPI option "KeepOpen" is not implemented this version.', fatal=True)

        self.listen()

    def listen(self):
        # TODO: Add Error handling
        address = self.address.hostname
        port = self.address.port
        protocol = self.address.protocol

        logging.info(f'Listening for GPI on {protocol}://{address}:{port}')
        
        sock_timeout = 1 / self.queue_rate if self.queue_rate != 0 else 0
        self.socket.settimeout(sock_timeout)

        self.queue_rate = 0
        self.queue_cooldown = 0

        self.socket.bind((address, port))

        if protocol == 'tcp':
            self.socket.listen(self.conn_backlogs)

        self.initialized = True

    def receive(self):
        pass

    def sender_whitelisted(self, addr):
        conn_uri = f'{self.address.protocol}://{addr[0]}:{addr[1]}'

        logging.debug(f'New GPI connection from {conn_uri}')
        addr_net = ipaddress.IPv4Network(addr[0])

        for subnet in self.address.whitelist:
            if subnet.supernet_of(addr_net):
                return True

        return False

    def tick(self):
        try:
            if self.address.protocol == 'tcp':
                conn, addr = self.socket.accept()

                if type(conn) is socket.socket and type(addr) is tuple:
                    if self.sender_whitelisted(addr):
                        data = conn.recv(self.recv_buffer)
                        if data:
                            self.process_command(data)
                        else:
                            conn.close()
                    else:
                        conn.close()
                        self.parent.update_module_status(self, ModuleStatus.ActivityWarning)
                        logging.warning(f'Rejected GPI connection from tcp://{addr[0]}:{addr[1]}, not on whitelist!')

            elif self.address.protocol == 'udp':
                # TODO: Recv more than buffer 1024
                data, addr = self.socket.recvfrom(self.recv_buffer)

                if len(data) > 0 and type(addr) is tuple:
                    if self.sender_whitelisted(addr):
                        self.process_command(data)
                    else:
                        self.parent.update_module_status(self, ModuleStatus.ActivityWarning)
                        logging.warning(f'Ignored GPI command from udp://{addr[0]}:{addr[1]}, not on whitelist!')

        except socket.timeout:
            return

    def parse_command(self, gpi_data):
        encoding = self.config.get('Encoding', 'utf-8')
        separator = self.config.get('Separator', None)

        gpi_cmds = gpi_data.decode(encoding)

        if separator in gpi_cmds:
            return gpi_cmds.split(separator)
        
        return [gpi_cmds]
        
    def process_command(self, gpi_data):
        inp_cmds = self.config.get('InputCommands', [])
        gpi_cmds = self.parse_command(gpi_data)

        for gpi_cmd in gpi_cmds:
            gpi_cmd = gpi_cmd.strip()
            if len(gpi_cmd) <= 0:
                continue

            run_cmd = None
            for inp_cmd in inp_cmds:
                if inp_cmd.get('Payload', None) == gpi_cmd:
                    run_cmd = inp_cmd
                    break

            if run_cmd is not None:
                actions = run_cmd.get('Actions', [])
                logging.info(f'GPI received command: "{run_cmd.get("Payload", None)}", running {len(actions)} action(s)...')

                for action in actions:
                    self.parent.run_action_later(action)

                self.parent.update_module_status(self, ModuleStatus.ActivityRunning)

            else:
                self.parent.update_module_status(self, ModuleStatus.ActivityWarning)


class GPOThread(GPIOThread):

    module_io_type: ModuleIOType = ModuleIOType.Output

    def init(self):
        super(GPOThread, self).init()

        self.connect()

    def show_manual_send_window(self):
        commands = self.config.get('OutputCommands', [])
        data = {
            'cmd_list': [ f"{self.module_id}: {cmd.get('Text', 'Unnamed')}" for cmd in commands ],
            'callback_safe': self.run_later('manual_send_callback').with_args
        } 

        self.parent.UI.create_window_later(GPOManualSendWindow, user_data=data)

    def manual_send_callback(self, val):
        commands = self.config.get('OutputCommands', [])
        payload = None
        for command in commands:
            if '{}: {}'.format(self.module_id, command['Text']) == val:
                payload = command.get('Payload', None)
                break
    
        if payload is not None:
            self.send(payload)

        # self.show_manual_send_window()

    def connect(self):
        address = self.address.hostname
        port = self.address.port
        protocol = self.address.protocol

        logging.info(f'GPO will send on {protocol}://{address}:{port}')

        try:
            self.socket.settimeout(self.config.get('Timeout', 2))
            conn = self.socket.connect((address, port))
        except socket.gaierror as e:
            raise exceptions.FxConfigException(f'GPO hostname error', e, fatal=True)
        except socket.error as e:
            # raise exceptions.FxNetworkException(f'GPO connection error', e)
            # TODO: Show messagebox
            self.parent.update_module_status(self, ModuleStatus.ActivityKeepError)
            logging.error(f'GPO connection error: {e}')
            return False

        self.initialized = True
        return conn

    def run_output_command_handler(self, output_command):
        # TODO: Make more efficient
        commands = self.config.get('OutputCommands', [])
        for command in commands:
            if command.get('Name', '') == output_command:
                self.send(command.get('Payload', None))
                break

    def send(self, data):
        if self.socket is None:
            self.parent.update_module_status(self, ModuleStatus.ActivityError)
            return False

        if data is None:
            self.parent.update_module_status(self, ModuleStatus.ActivityError)
            return False

        encoding = self.config.get('Encoding', 'utf-8')
        separator = self.config.get('Separator', '').encode(encoding)

        if type(data) is str:
            data = data.encode(encoding)
        
        try:
            logging.info(f'GPO sent data: {data}')
            self.socket.send(data + separator)
            self.parent.update_module_status(self, ModuleStatus.ActivityRunning)
        except socket.error as e:
            # raise exceptions.FxNetworkException(f'Error sending data', e)
            # TODO: Show messagebox
            self.parent.update_module_status(self, ModuleStatus.ActivityError)
            logging.error(f'GPO cannot send data: {e}')
            return False

        return True