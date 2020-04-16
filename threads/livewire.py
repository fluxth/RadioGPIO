import logging

from threads import SubThreadBase

import exceptions
from helpers.enum import ModuleStatus, ModuleIOType

class LivewireThread(SubThreadBase):

    module_io_type: ModuleIOType = ModuleIOType.Bidirectional

    def init(self):
        pass

    def cleanup(self):
        pass
    