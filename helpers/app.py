import logging
import sys

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
        while self.index < len(self.module_map):
            value = None
            
            module = self.module_map[self.index]
            key = module[0]

            module_config = self.config.get(key, None)
            if module_config is not None:
                if module_config.get('Enabled', False) is True:
                    value = module

            self.index += 1
            if value is not None and value[1] is not None:
                return value

        if self.index >= len(self.config):
            raise StopIteration