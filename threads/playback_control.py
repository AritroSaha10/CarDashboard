from threads.dbus_thread import DBusThread
import os, sys, logging

import dbus
from gi.repository import GLib

import threading

class PlaybackControlThread(DBusThread):
    _btObj = None # DBus bluetooth object
    _btMgr = None # DBus object manager

    playerInterface = None # DBus bluetooth media player interface
    transportPropInterface = None # DBus bluetooth media transport properties interface

    playbackStatus = None
    trackInfo = None

    def __init__(self):
        super().__init__("PlaybackControlThread", logging.DEBUG)

        # Initialize vars
        self.btObj = self.sysBus.get_object("org.bluez", "/")
        self.btMgr = dbus.Interface(self.btObj, "org.freedesktop.DBus.ObjectManager")

        # TODO: Get playback status and track info immediately


        # Get bluetooth player and transport interfaces
        for path, interfaces in self.btMgr.GetManagedObjects().items():
            if "org.bluez.MediaPlayer1" in interfaces:
                # Get player interface
                self.playerInterface = dbus.Interface(
                    self.sysBus.get_object("org.bluez", path),
                    "org.bluez.MediaPlayer1"
                )
            elif dbus.String("org.bluez.MediaTransport1") in interfaces:
                self.transportPropInterface = dbus.Interface(
                    self.sysBus.get_object("org.bluez", path),
                    "org.freedesktop.DBus.Properties"
                )
        
        # Throw error if couldn't find
        if not self.playerInterface:
            self.logger.error(u"Unable to get the bluetooth player interface.")
            sys.exit(1)
        if not self.transportPropInterface:
            self.logger.error(u"Unable to get the bluetooth media transport properties.")
            sys.exit(1)

        # Attach reciever
        self.sysBus.add_signal_receiver(
            self.on_property_changed,
            bus_name="org.bluez",
            signal_name="PropertiesChanged",
            dbus_interface="org.freedesktop.DBus.Properties"
        )

        super().runMainLoop()

    # Callback
    def on_property_changed(self, interface, changed, invalidated):
        if interface != "org.bluez.MediaPlayer1":
            # Not bluetooth device, doesn't matter
            return
        
        for prop, value in changed.items():
            if prop == "Status":
                self.logger.debug(f"Playback status: {value}")
                self.playbackStatus = value
            elif prop == "Track":
                self.logger.debug(f"Track info: ")
                for key in ["Title", "Artist", "Album"]:
                    self.logger.debug(f"\t{key}: {value.get(key, '')}")
                self.trackInfo = value

    # Playback functions, self-explanatory
    def play(self):
        self.playerInterface.Play()
    
    def pause(self):
        self.playerInterface.Pause()

    def nextTrack(self):
        self.playerInterface.Next()
    
    def prevTrack(self):
        self.playerInterface.Previous()
    
    def changeVol(self, newVol):
        if newVol not in range(0, 128):
            self.logger.info(f"New volume must be between 0 and 127, value of {newVol} was given. Ignoring...")
            return
        
        self.transportPropInterface.Set(
            "org.bluez.MediaTransport1",
            dbus.UInt16(newVol)
        )