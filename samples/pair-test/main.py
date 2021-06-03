from agent import BTAgent, BTAgentManager
from adapter import BTAdapter
from serviceuuids import SERVICES
from uuid import BTUUID

from gi.repository import GLib

import dbus
import dbus.mainloop.glib
import signal
import subprocess
import math
import configparser
import io
import os

config = configparser.ConfigParser()
config.read('config.ini.default')

class AutoAcceptSingleAudioAgent(BTAgent):
    """
    Accepts one client unconditionally and hides the device once connected.
    As long as the client is connected no other devices may connect.
    This 'first comes first served' is not necessarily the 'bluetooth way' of
    connecting devices but the easiest to implement.
    """
    def __init__(self, connect_callback, disconnect_callback, track_callback):
        BTAgent.__init__(self, default_pin_code=config.get('bluez', 'pin_code') or '0000', cb_notify_on_authorize=self.auto_accept_one)
        self.adapter = BTAdapter(config.get('bluez', 'device_path'))
        self.adapter.set_property('Discoverable', config.getboolean('bluez', 'discoverable'))
        self.allowed_uuids = [ SERVICES["AdvancedAudioDistribution"].uuid, SERVICES["AVRemoteControl"].uuid ]
        self.connected = None
        self.tracked_devices =  []
        self.connect_callback = connect_callback
        self.disconnect_callback = disconnect_callback
        self.track_callback = track_callback
        self.update_discoverable()

    def update_discoverable(self):
        if not config.getboolean('bluez', 'discoverable'):
            return

        if bool(self.connected):
            print("Hiding adapter from all devices.")
            self.adapter.set_property('Discoverable', False)
        else:
            print("Showing adapter to all devices.")
            self.adapter.set_property('Discoverable', True)

    def auto_accept_one(self, method, device, uuid):
        if not BTUUID(uuid).uuid in self.allowed_uuids: return False
        if self.connected and self.connected != device:
            print("Rejecting device, because another one is already connected. connected_device=%s, device=%s" % (self.connected, device))
            return False

        # track connection state of the device (is there a better way?)
        if not device in self.tracked_devices:
            self.tracked_devices.append(device)
            self.adapter._bus.add_signal_receiver(self._track_connection_state,
                                                  path=device,
                                                  signal_name='PropertiesChanged',
                                                  dbus_interface='org.freedesktop.DBus.Properties',
                                                  path_keyword='device')
            self.adapter._bus.add_signal_receiver(self._watch_track,
                                                  path=device + '/player0',
                                                  signal_name='PropertiesChanged',
                                                  dbus_interface='org.freedesktop.DBus.Properties',
                                                  path_keyword='device')

        return True

    def _watch_track(self, addr, properties, signature, device):
        if not 'Track' in properties: return
        self.track_callback(properties['Track'])

    def _track_connection_state(self, addr, properties, signature, device):
        if self.connected and self.connected != device: return
        if not 'Connected' in properties: return

        if not self.connected and bool(properties['Connected']):
            print("Device connected. device=%s" % device)
            self.connected = device
            self.update_discoverable()
            self.connect_callback()

        elif self.connected and not bool(properties['Connected']):
            print("Device disconnected. device=%s" % device)
            self.connected = None
            self.update_discoverable()
            self.disconnect_callback()

def donothing():
    return

if __name__ == "__main__":
    # Initialize the DBus SystemBus
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # Mainloop for communication
    mainloop = GLib.MainLoop()

    agent = AutoAcceptSingleAudioAgent(donothing, donothing, donothing)
    manager = BTAgentManager()
    manager.register_agent(agent._path, "NoInputNoOutput")
    manager.request_default_agent(agent._path)

    mainloop.run()