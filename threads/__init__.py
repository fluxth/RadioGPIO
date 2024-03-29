from threading import Thread
from queue import Queue, Empty
import logging
import time

import exceptions

from helpers import multi_getattr
from helpers.enum import ModuleStatus, ModuleIOType

class ThreadBase():

    # Thread Name
    name: str = None

    # Thread queue
    queue: Queue = None

    # Thread exit flag
    exit: bool = False

    # Queue settings
    queue_blocking: bool = True
    queue_rate: int = 5      # Hz
    queue_timeout: int = 10  # sec
    queue_cooldown: float = 0.2 # sec

    # Consts for self checking
    is_mainthread = False
    is_subthread = False

    # Properties of children
    UI = None
    parent = None

    def __init__(self):
        logging.info(f'Initializing thread for {self.__class__.__name__}')
        self.init_queue()

    def init_queue(self) -> None:
        self.queue = Queue()

    def run_later(self, method_name):
        return FxQueueItem(self.__class__, method_name).set_sender(self, auto_add_queue_sender=True) 

    def pre_start(self):
        pass

    def tick(self):
        pass

    def wait_for_queue(self):
        logging.debug(f'Waiting for queue, block={self.queue_blocking}, timeout={self.queue_timeout}')
        try:
            item = self.queue.get(block=self.queue_blocking, timeout=self.queue_timeout)
        except Empty:
            item = None

        if item is None:
            if self.queue_cooldown != 0:
                logging.debug(f'QueueItem is None, waiting {self.queue_cooldown} sec cooldown...')
                time.sleep(self.queue_cooldown)
            return False

        if item.target is not self.__class__:
            logging.debug(f'Skipping QueueItem for targeted for "{item.target}"')
            return False

        return self.process_queue(item)

    def process_queue(self, item):
        logging.debug(f'Process queue triggered: {item}')

        to_call = multi_getattr(self, item.method)
        try:
            result = to_call(*item.args, **item.kwargs)
        except exceptions.FxBaseException as e:
            logging.error(e)

            args = ('Runtime Error', e.get_alert_str())
            kwargs = { 'custom_text': ('Exit' if e.fatal else 'OK') }

            if self.is_mainthread:
                self.UI.show_error(*args, **kwargs)
            else:
                self.parent.run_later('UI.show_error').with_args(*args, **kwargs)

            if e.fatal:
                self.shutdown()

            return False

        if item.callback is not None:
            logging.debug(f'{item} returned result: {result}, forwarding to callback function {item.callback}')
            item.callback(result)
        else:
            logging.debug(f'{item} returned result: {result}')

    def main_loop(self):
        logging.debug('Main loop started')

        self.pre_start()
        logging.debug('Pre-start finished')

        while not self.exit:
            self.tick()

            queue_result = self.wait_for_queue()
            if queue_result is not False:
                logging.debug('Queue result is not False, continuing...')
                continue

            if not self.queue_blocking and self.queue_rate != 0:
                time.sleep(1 / self.queue_rate)

    def run(self):
        logging.info(f'{self.name} started.')

        try:
            self.main_loop()
        except exceptions.FxBaseException as e:
            self.handle_runtime_exception(e)

        logging.info(f'{self.name} exited.')

    def shutdown(self):
        pass

    def handle_initialization_exception(self, exception):
        raise exception

    def handle_runtime_exception(self, exception):
        raise exception

    def handle_shutdown_exception(self, exception):
        raise exception

class SubThreadBase(ThreadBase, Thread):

    # Display name for main window status
    display_name: str = None

    # Parent Thread
    parent: ThreadBase = None

    # Module ID
    module_id: str = ''

    # Module IO type
    module_io_type: ModuleIOType = ModuleIOType.Invalid

    # Init Successful
    initialized = False

    # Consts for self checking
    is_subthread = True

    def __init__(self, parent, module_id, *args, **kwargs):
        Thread.__init__(self, *args, **kwargs)
        ThreadBase.__init__(self, *args, **kwargs)

        self.initialized = False
        self.parent = parent
        self.module_id = module_id

        self.parent.update_module_status(self, ModuleStatus.Enabled)

        self.init_identity()
        self.init()

        if self.initialized:
            self.parent.update_module_status(self, ModuleStatus.Initialized, update_if=ModuleStatus.Enabled)

    def init(self):
        pass
        
    def init_identity(self):
        self.name = self.__class__.__name__
        if self.display_name is None:
            self.display_name = self.module_id

    def main_loop(self):
        self.parent.update_module_status(self, ModuleStatus.Running, update_if=ModuleStatus.Initialized)
        super(SubThreadBase, self).main_loop()

    def run_output_command(self, output_command, delay=None):
        if delay is not None:
            logging.info(f'Delaying action execution by {delay} sec...')
            time.sleep(delay)

        self.run_output_command_handler(output_command)

    def run_output_command_handler(self, output_command):
        pass

    def cleanup(self):
        pass

    def shutdown(self):
        if self.exit:
            return

        logging.warning(f'Thread {self.name} shutting down!')
        self.cleanup()
        self.exit = True

class FxQueueItem():
    # Class of target thread
    target: ThreadBase.__class__ = None

    # Object of sender
    sender: object = None
    auto_add_queue_sender: bool = False

    # Callback
    callback = None

    # str of target thread's class method
    method: str = None

    args: list = []
    kwargs: dict = {}

    def __init__(self, target_class, method):
        self.target = target_class
        self.method = method

    def __str__(self):
        return f'<FxQueueItem for={self.target.__name__} method={self.method} args={self.args} kwargs={self.kwargs}>'

    def set_sender(self, sender, auto_add_queue_sender=False):
        self.sender = sender
        self.auto_add_queue_sender = auto_add_queue_sender

        return self

    def attach_callback(self, callback):
        self.callback = callback

        return self

    def with_args(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

        return self.run()

    def run(self):
        if self.auto_add_queue_sender:
            self.sender.queue.put(self)

        return self