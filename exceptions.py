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
        display = "Fatal " if self.fatal else ""
        display += f'{self.error_type} Error: '
        display += self.msg
        display += f' ({self.exc})' if self.exc is not None else ''
        return display

    def get_caught_str(self):
        return f'(Caught Exception) {self.__str__()}'

    def get_alert_str(self):
        return self.__str__()

class FxInternalException(FxBaseException):
    error_type = 'Internal'

class FxNetworkException(FxBaseException):
    error_type = 'Network'

class FxConfigException(FxBaseException):
    error_type = 'Configuration'

class FxUIException(FxBaseException):
    error_type = 'User Interface'