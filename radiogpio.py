import logging
import os
import sys

import exceptions
from __init__ import FxGpioApp
from helpers.app import terminate_process

# Entrypoint for app
if __name__ == '__main__':

    # Setup logging
    logging.basicConfig(format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s', datefmt='%d %b %Y %H:%M:%S', level=logging.INFO)
    logging.debug('Logging initialized.')

    # Check if running from freezed environment
    run_dir = getattr(sys, '_MEIPASS', False)
    if not run_dir:
        run_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Initialize main app
    exit_code: int = 0
    logging.info('Creating main application...')
    try:
        app = FxGpioApp(run_dir=run_dir)
        try:
            logging.debug('Running main app')
            exit_code = app.run()
        except KeyboardInterrupt:
            logging.warning('SIGINT Detected!')
            exit_code = app.shutdown(True)

        if app.restart is True:
            logging.warning('Restart flag detected, restarting main app...')
            os.execl(sys.executable, *sys.argv)

    except Exception as e:
        logging.exception(e)
        exceptions.exception_handler_window(e)
        os._exit(1)

    terminate_process(exit_code)