from threads.dbus_thread import DBusThread
import os, sys, logging
import dbus
import threading

# Transports volume control on phone to actual volume on pi
class VolumeControlThread(DBusThread):
    VOLUME_MAX = 127

    def __init__(self):
        super().__init__("VolumeControlThread", logging.DEBUG) # Initializes DBus stuff
        
        # Add listeners to org.bluez
        self.sysBus.add_signal_receiver(
            self.device_property_changed,
            bus_name='org.bluez',
            signal_name='PropertiesChanged',
            dbus_interface='org.freedesktop.DBus.Properties',
            path_keyword='path'
        )

        # Start mainloop
        super().runMainLoop()

    # Given a bluetooth address in format AA:BB:CC:DD:EE:FF, fetch the index number to the pulseaudio source
    def addressToIndex(self, address: str) -> int:
        paSrc = os.popen('pactl list short sources | grep bluez_source.{}'.format(address.replace(':', '_'))).read()

        if not paSrc:
             self.logger.debug(u"Cannot find PulseAudio A2DP source {}".format(address))
             return
            
        # Source index is first field in tab separated string
        paIdx = paSrc.split("\t")[0]
        self.logger.debug(u"PulseAudio A2DP source {} is #{}".format(address, paIdx))
        return paIdx

    # Sets volume of pulseaudio source
    def setVolume(self, address, volume):
        paIdx = self.addressToIndex(address)
        if paIdx:
            self.logger.debug(u'Running pactl set-source-volume {} {}'.format(paIdx, format(float(volume) / self.VOLUME_MAX, '.2f')))
            os.system('pactl set-source-volume {} {}'.format(paIdx, format(float(volume) / self.VOLUME_MAX, '.2f')))
        else:
            self.logger.debug(u'Skipping volume change')
    
    # Callback for when property changes
    # TODO: Add comments
    def device_property_changed(self, interface, properties, invalidated, path):
        if interface == 'org.bluez.MediaTransport1':
            self.sysBus = dbus.SystemBus()
            mediatransport_object = self.sysBus.get_object('org.bluez', path)
            mediatransport_properties_interface = dbus.Interface(mediatransport_object, 'org.freedesktop.DBus.Properties')
            device_path = mediatransport_properties_interface.Get('org.bluez.MediaTransport1', 'Device')
            device_object = self.sysBus.get_object('org.bluez', device_path)
            device_properties_interface = dbus.Interface(device_object, 'org.freedesktop.DBus.Properties')
            name = device_properties_interface.Get('org.bluez.Device1', 'Name')
            address = device_properties_interface.Get('org.bluez.Device1', 'Address')
            if 'State' in properties:
                state = properties['State']
                self.logger.info(u'Bluetooth A2DP source: {} ({}) is now {}'.format(name, address, state))
                if state == 'active':
                    codec =  mediatransport_properties_interface.Get('org.bluez.MediaTransport1', 'Codec')
                    self.logger.debug(u'Bluetooth A2DP source: {} ({}) codec is {}'.format(name, address, int(codec)))
                    volume = mediatransport_properties_interface.Get('org.bluez.MediaTransport1', 'Volume')
                    self.logger.debug(u'Bluetooth A2DP source: {} ({}) volume is {}'.format(name, address, volume))
                    self.setVolume(address, volume)
            elif 'Volume' in properties:
                volume = properties['Volume']
                self.logger.debug(u'Bluetooth A2DP source: {} ({}) volume is now {}'.format(name, address, volume))
                self.setVolume(address, volume)
            elif 'Codec' in properties:
                codec = properties['Codec']
                self.logger.debug(u'Bluetooth A2DP source: {} ({}) codec is {}'.format(name, address, int(codec)))

