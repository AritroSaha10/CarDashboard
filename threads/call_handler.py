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

    def handleCallAdd(self, path, properties):
        self.logger.debug(f"Call added: {path} - {properties}")

        # Get the VoiceCall object and add it to the list
        voiceCallObj = {
            "path": path, # Path to call
            "object": dbus.Interface(self.sysBus.get_object(f"org.ofono", path), 'org.ofono.VoiceCall'), # Interface to call, properties always updated
            "staticProps": dbus.Interface(self.sysBus.get_object(f"org.ofono", path), 'org.ofono.VoiceCall').GetProperties() # Properties of call when first started
        }

        self.calls.append(voiceCallObj)

        # Generate a callback function that also identifies the voicecall
        def handleCallPropertyChange(prop, value):
            # Print property change
            self.logger.debug(f"Property '{prop}' in call '{path}' changed: {value}")
            
            # Run extra callback
            if callable(self.handleCallPropertyChangeExtra):
                self.handleCallPropertyChangeExtra(voiceCallObj, prop, value)
        
        voiceCallObj["object"].connect_to_signal("PropertyChanged", handleCallPropertyChange)

        # Check if incoming, only useful for debug
        if properties["State"] == "incoming":
            if properties["Name"] != "":
                self.logger.info(f"Incoming call from {properties['Name']}")
            elif properties["LineIdentification"] != "":
                self.logger.info(f"Incoming call from {properties['LineIdentification']}")
            else:
                self.logger.info("Incoming call from unknown")
        elif properties["State"] == "dialing":
            if properties["Name"] != "":
                self.logger.info(f"Dialing {properties['Name']}")
            elif properties["LineIdentification"] != "":
                self.logger.info(f"Dialing {properties['LineIdentification']}")
            else:
                self.logger.info(f"Dialing unknown number")

        # Run extra callback if we can
        if callable(self.handleCallAddExtra):
            self.handleCallAddExtra(voiceCallObj)

    def handleCallRemove(self, path):
        self.logger.debug(f"Call removed: {path}")

        # Get which call obj it is
        callIndex = next((i for i, call in enumerate(self.calls) if call["path"] == path), None)
        
        if callIndex != None:
            # Let us know what the number is
            phoneNum = self.calls[callIndex]["staticProps"]["LineIdentification"]
            if phoneNum != "":
                self.logger.info(f"Disconnected call from/to {phoneNum}")
            else:
                self.logger.info(f"Disconnected call from/to unknown number")

        # Run extra callback if we can
        if callable(self.handleCallRemoveExtra):
            self.handleCallRemoveExtra(self.calls[callIndex])
        
        if callIndex != None:
            # Delete from list
            del self.calls[callIndex]