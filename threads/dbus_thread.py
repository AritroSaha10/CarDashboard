import os, sys, logging, threading

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GObject

# Parent class for all threads that use DBus
class DBusThread:
    # Logging settings
    LOG_NAME = None
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = "%(name)s[%(process)d]: %(message)s"
    logger = None

    mainLoopThread = None

    sysBus = None

    def __init__(self, loggerName, logLevel):
        # Set all variables
        self.LOG_NAME = loggerName
        self.LOG_LEVEL = logLevel

        # Setup logger
        self.logger = logging.getLogger(self.LOG_NAME)
        self.logger.setLevel(self.LOG_LEVEL)

        # ch = logging.handlers.SysLogHandler(address = '/dev/log')
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter(fmt=self.LOG_FORMAT))
        self.logger.addHandler(ch)
        self.logger.info('Started')

        # Get the system bus
        try:
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            self.sysBus = dbus.SystemBus()
            self.mainLoop = GObject.MainLoop()
            
        except Exception as ex:
            self.logger.error('Unable to get the system dbus: "{0}". Exiting. Is dbus running?'.format(str(ex)))
            sys.exit(1)

    # Should be run after signal recievers are added
    def runMainLoop(self):
        # Runs DBus main loop
        def mainloop():
            GObject.MainLoop().run()
        
        self.mainLoopThread = threading.Thread(target=mainloop)
        self.mainLoopThread.daemon = True
        self.mainLoopThread.start()

        self.logger.info("Started DBus main loop thread")

