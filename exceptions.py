import PySimpleGUI as sg
import traceback

class FxBaseException(Exception):
    error_type = 'Generic'

    msg = None
    exc = None
    fatal = False

    def __init__(self, msg, exc=None, fatal=False, **kwargs):
        super(FxBaseException, self).__init__(**kwargs)
        self.msg = msg
        self.exc = exc
        self.fatal = fatal

    def __str__(self):
        display = f'{self.get_error_title()}: '
        display += self.msg
        display += f' ({self.get_attached_exc_message()})' if self.exc is not None else ''
        return display

    def get_error_title(self):
        display = "Fatal " if self.fatal else ""
        display += f'{self.error_type} Error'
        return display

    def get_attached_exc_message(self):
        return str(self.exc) if self.exc is not None else ''

    def get_caught_str(self):
        return f'(Caught Exception) {self.__str__()}'

    def get_alert_str(self):
        display = f'{self.get_error_title()}:\n'
        display += self.msg
        if self.exc is not None:
            display += '\n\nAdditional error details:\n'
            display += self.get_attached_exc_message()

        return display

class FxInternalException(FxBaseException):
    error_type = 'Internal'

class FxNetworkException(FxBaseException):
    error_type = 'Network'

class FxConfigException(FxBaseException):
    error_type = 'Configuration'

class FxUIException(FxBaseException):
    error_type = 'User Interface'

def exception_handler_window(exc):
    layout = [
        [sg.Text('Uncaught Exception:')],
        [sg.Output(size=(60,15), key='output', background_color='red', text_color='white', font=('Consolas', 10))],
        [sg.Button('COPY TO CLIPBOARD', key='copy', button_color=('white', 'black')), sg.Button('EXIT', button_color=('white', 'red'))]
    ]

    window = sg.Window('Crash Report', layout, keep_on_top=True, disable_minimize=True)
    window.Finalize()

    traceback.print_exc()
    # stacktrace = traceback.format_exception_only(exc.__class__, exc)
    # window['output'].Update(value=stacktrace)

    while True:
        event, _ = window.Read()
        # window['output'].Update(value=stacktrace)
        if event in (None, 'EXIT'):
            break

        elif event == 'copy':
            window['copy'].Update(text='Copied!', disabled=True)

    window.Close()