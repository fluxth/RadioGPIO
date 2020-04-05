import logging
import time

import exceptions
from helpers.enum import ActionSequenceItemType

class Action():

    name: str = None
    text: str = None
    sequence = None

    app = None

    def __str__(self):
        return f'<Action {self.name} seq={self.sequence}>'

    def __init__(self, app, action_dict):
        self.app = app

        self.name = action_dict.get('Name', '').strip()

        if len(self.name) <= 0:
            raise exceptions.FxConfigException('Action requires a "Name" property.', fatal=True)

        self.text = action_dict.get('Text', None)
        self.sequence = ActionSequence(self, action_dict.get('Sequence', []))

    def run(self):
        logging.info(f'Running action {self}...')
        if self.sequence.pre_run() is not False:
            self.sequence.run()
        else:
            logging.error(f'Cannot run action {self}!')

class ActionSequence():

    sequence_list: list = []

    action = None

    def __str__(self):
        return f'<ActionSequence items={len(self.sequence_list)}>'

    def __init__(self, action, sequence_list):
        self.action = action

        self.sequence_list = []
        for sequence_dict in sequence_list:
            self.sequence_list.append(ActionSequenceItem(self, sequence_dict))

    def pre_run(self):
        for sequence_item in self.sequence_list:
            if sequence_item.pre_run() is False:
                return False

    def run(self):
        logging.debug(f'Action sequence of action "{self.action}" running {len(self.sequence_list)} tasks.')
        for sequence_item in self.sequence_list:
            sequence_item.run()


class ActionSequenceItem():

    item_type: ActionSequenceItemType = None
    item_data: dict = {}

    module = None
    command: str = None
    extra_params: dict = {}

    action_sequence = None

    def __init__(self, action_sequence, sequence_item_dict):
        self.action_sequence = action_sequence
        self.item_data = {}
        self.extra_params = {}

        enabled = sequence_item_dict.get('Enabled', True)
        if enabled is False:
            self.item_type = ActionSequenceItemType.NoOp
            return

        item_type = sequence_item_dict.get('Type', None)
        if item_type is None:
            raise exceptions.FxConfigException('Action sequence item requires a "Type" property.', fatal=True)

        if item_type == 'Wait':
            self.item_type = ActionSequenceItemType.Wait
            self.init_type_wait(sequence_item_dict)
        elif item_type == 'RunOutputCommand':
            self.item_type = ActionSequenceItemType.RunOutputCommand
            self.init_type_output_command(sequence_item_dict)
        else:
            raise exceptions.FxConfigException(f'Unknown action sequence item type: {self.item_type}.', fatal=True)

    def init_type_wait(self, sequence_item_dict):
        self.item_data['delay'] = float(sequence_item_dict.get('Delay', 0))
        
    def init_type_output_command(self, sequence_item_dict):
        self.command = sequence_item_dict.get('OutputCommand', None)
        if self.command is None:
            raise exceptions.FxConfigException('Action sequence item requires a "Command" property.', fatal=True)

        module_ptr = sequence_item_dict.get('Module', None) 
        if module_ptr is None:
            raise exceptions.FxConfigException('Action sequence item requires a "Module" property.', fatal=True)

        self.module = self.map_module(module_ptr)

        if (delay := sequence_item_dict.get('Delay', None)) is not None:
            self.extra_params['delay'] = float(delay)


    def map_module(self, module_ptr):
        module = self.action_sequence.action.app.subthread.get(module_ptr.lower(), None)
        if module is None:
            raise exceptions.FxInternalException(f'Cannot map action sequence item to module "{module_ptr}"', fatal=True)

        return module

    def pre_run(self):
        if self.item_type == ActionSequenceItemType.RunOutputCommand:
            if not self.module.initialized:
                self.action_sequence.action.app.UI.show_error(
                    f'Error while preparing to run action "{self.action_sequence.action.name}":', 
                    f'Output command "{self.command}" failed to run because module {self.module.name} is not initialized!'
                )
                return False

        return True

    def run(self):
        if self.item_type == ActionSequenceItemType.NoOp:
            return True

        elif self.item_type == ActionSequenceItemType.RunOutputCommand:
            kwargs = self.extra_params
            logging.debug(f'Running module {self.module} with command "{self.command}" + {kwargs}')
            self.module.run_later('run_output_command').with_args(self.command, **kwargs)

            return True
        elif self.item_type == ActionSequenceItemType.Wait:
            delay = self.item_data['delay']
            logging.debug(f'Waiting {delay} seconds...')
            time.sleep(delay)

            return True

        return False
