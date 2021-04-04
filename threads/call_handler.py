from threads.dbus_thread import DBusThread
import os, sys, logging

import dbus
from gi.repository import GLib

import threading

class VoiceCallHandlerThread(DBusThread):
    calls = []

    # Ofono settings
    _modem = None
    _manager = None
    _bus = None
    _ofonoVCM = None

    # Extra callbacks for adding / ending call
    # Both funcs should have 1 param, call obj that was added / removed
    handleCallAddExtra = None
    handleCallRemoveExtra = None
    
    # Extra callback for when call property changes
    # Should have 3 params, voice call obj, the changed property, and the changed value
    handleCallPropertyChangeExtra = None

    def __init__(self, handleCallAddExtra = None, handleCallRemoveExtra = None, handleCallPropertyChangeExtra = None):
        super().__init__("VoiceCallHandlerThread", logging.DEBUG)

        # Initialize variables
        try:
            self._manager = dbus.Interface(
                self.sysBus.get_object("org.ofono", "/"),
                "org.ofono.Manager"
            )
            self._modem = self._manager.GetModems()[0][0]
        except:
            self.logger.error("Could not start because ofono was not found")
            sys.exit(1)
        
        # Fetch dbus vcm
        self._ofonoVCM = dbus.Interface(
            self.sysBus.get_object("org.ofono", self._modem),
            "org.ofono.VoiceCallManager"
        )

        # Add callbacks
        self._ofonoVCM.connect_to_signal(
            "CallAdded",
            self.handleCallAdd
        )
        self._ofonoVCM.connect_to_signal(
            "CallRemoved",
            self.handleCallRemove
        )

        # Fetch any current calls, also check if vcm obj exists
        try:
            self.calls = self._ofonoVCM.GetCalls()
        except:
            self.logger.error("Could not start because no modem is connected")
            sys.exit(1)

        # Update global extra handlers
        self.handleCallAddExtra = handleCallAddExtra
        self.handleCallRemoveExtra = handleCallRemoveExtra

        super().runMainLoop()

    def sendCall(self, number: str):
        self._ofonoVCM.Dial(number, "default")

    def acceptCall(self, callObj):
        callObj.Answer()

    def endCall(self, callObj):
        callObj.Hangup()

    def endAllCalls(self):
        self._ofonoVCM.HangupAll()