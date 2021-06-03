#!/usr/bin/env python

import sys
import signal
import logging
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GObject as gobject

LOG_LEVEL = logging.INFO
#LOG_LEVEL = logging.DEBUG
LOG_FILE = "/dev/stdout"
#LOG_FILE = "/var/log/syslog"
LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"

def device_property_changed_cb(property_name, value, path, interface):
    device = dbus.Interface(bus.get_object("org.bluez", path), "org.bluez.Device")
    properties = device.GetProperties()

    if (property_name == "Connected"):
        action = "connected" if value else "disconnected"
#
# Replace with your code to write to the PiFace
#
        print("The device %s [%s] is %s " % (properties["Alias"], properties["Address"], action))

def shutdown(signum, frame):
    mainloop.quit()

if __name__ == "__main__":
    # shut down on a TERM signal
    signal.signal(signal.SIGTERM, shutdown)

    # start logging
    # Setup logger
    logger = logging.getLogger("BTMinder")
    logger.setLevel(LOG_LEVEL)

    # ch = logging.handlers.SysLogHandler(address = '/dev/log')
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(fmt=LOG_FORMAT))
    logger.addHandler(ch)

    logger.info("Starting btminder to monitor Bluetooth connections")

    # Get the system bus
    try:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
    except Exception as ex:
        logger.error("Unable to get the system dbus: '{0}'. Exiting btminder. Is dbus running?".format(ex.message))
        sys.exit(1)

    # listen for signals on the Bluez bus
    bus.add_signal_receiver(device_property_changed_cb, bus_name="org.bluez", signal_name="PropertyChanged",
            dbus_interface="org.bluez.Device", path_keyword="path", interface_keyword="interface")

    try:
        mainloop = gobject.MainLoop()
        mainloop.run()
    except KeyboardInterrupt:
        pass
    except:
        logger.error("Unable to run the gobject main loop")

    logger.info("Shutting down btminder")
    sys.exit(0)