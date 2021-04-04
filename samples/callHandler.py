import sys
import time

from gi.repository import GLib
import dbus.mainloop.glib
import dbus

import threading

class VoiceCallHandler:
    calls = []    

    # DBus
    _modem = None
    _manager = None
    _bus = None
    _ofonoVCM = None
    _mainContext = None

    _mainLoopThread = None

    _debug = True

    # While also running normal code when there are new events, these functions are also run
    # Both funcs should have 1 parameter, the call object that was removed
    handleCallAddExtra = None
    handleCallRemoveExtra = None

    # This func is an extra callback for when a call property changes, useful for detecting when call gets accepted or whatever
    # Should have 3 params: voiceCallObj, prop, value
    handleCallPropertyChangeExtra = None

    def __init__(self, handleCallAddExtra = None, handleCallRemoveExtra = None, handleCallPropertyChangeExtra = None, debug = True):
        # Set debug variable
        self._debug = debug

        # Start DBus main loop for callbacks
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        # Get DBus managers and variables
        self.bus = dbus.SystemBus()
        try:
            self.manager = dbus.Interface(self.bus.get_object("org.ofono", "/"), "org.ofono.Manager")
            self.modem = self.manager.GetModems()[0][0]
        except:
            # Give a more descriptive error of what likely happened.
            raise Exception("VoiceCallHandler could not start because ofono could not be found. Please check your configuration and try again.")
        
        self.ofonoVCM = dbus.Interface(self.bus.get_object('org.ofono', self.modem), 'org.ofono.VoiceCallManager')
        self.main_context = GLib.MainContext.default()

        # Connect voice call manager callbacks to our functions
        self.ofonoVCM.connect_to_signal("CallAdded", self.handleCallAdd)
        self.ofonoVCM.connect_to_signal("CallRemoved", self.handleCallRemove)

        # Fetch any current calls, will fail if there is no VoiceCallManager
        try:
            self.calls = self.ofonoVCM.GetCalls()
        except:
            # Give a more descriptive error of what likely happened.
            raise Exception("VoiceCallHandler could not start because no modem is connected. Please connect a modem and try again.")

        # Update global extra handlers
        self.handleCallAddExtra = handleCallAddExtra
        self.handleCallRemoveExtra = handleCallRemoveExtra

        if self._debug:
            print("Started!")

        self.mainLoopThread = threading.Thread(target=self.mainloop)
        self.mainLoopThread.daemon = True
        self.mainLoopThread.start()
            
    def mainloop(self):
        while True:
            self.main_context.iteration(False)

    def sendCall(self, number: str):
        self.ofonoVCM.Dial(number, "default")

    def acceptCall(self, callObj):
        callObj.Answer()

    def endCall(self, callObj):
        callObj.Hangup()

    def endAllCalls(self):
        self.ofonoVCM.HangupAll()
    
    def handleCallAdd(self, path, properties):
        if self._debug:
            print(f"Call added: {path} - {properties}")

        # Get the VoiceCall object and add it to the list
        voiceCallObj = {
            "path": path, # Path to call
            "object": dbus.Interface(self.bus.get_object(f"org.ofono", path), 'org.ofono.VoiceCall'), # Interface to call, properties always updated
            "staticProps": dbus.Interface(self.bus.get_object(f"org.ofono", path), 'org.ofono.VoiceCall').GetProperties() # Properties of call when first started
        }

        self.calls.append(voiceCallObj)

        # Generate a callback function that also identifies the voicecall
        def handleCallPropertyChange(prop, value):
            # Print property change
            if self._debug:
                print(f"Property '{prop}' in call '{path}' changed: {value}")
            
            # Run extra callback
            if callable(self.handleCallPropertyChangeExtra):
                self.handleCallPropertyChangeExtra(voiceCallObj, prop, value)
        
        voiceCallObj["object"].connect_to_signal("PropertyChanged", handleCallPropertyChange)

        # Check if incoming, only useful for debug
        if self._debug:
            if properties["State"] == "incoming":
                if properties["Name"] != "":
                    print(f"Incoming call from {properties['Name']}")
                elif properties["LineIdentification"] != "":
                    print(f"Incoming call from {properties['LineIdentification']}")
                else:
                    print("Incoming call from unknown")
            elif properties["State"] == "dialing":
                if properties["Name"] != "":
                    print(f"Dialing {properties['Name']}")
                elif properties["LineIdentification"] != "":
                    print(f"Dialing {properties['LineIdentification']}")
                else:
                    print("Dialing unknown number")

        # Run extra callback if we can
        if callable(self.handleCallAddExtra):
            self.handleCallAddExtra(voiceCallObj)

    def handleCallRemove(self, path):
        if self._debug:
            print(f"Call removed: {path}")

        # Get which call obj it is
        callIndex = next((i for i, call in enumerate(self.calls) if call["path"] == path), None)
        
        if callIndex != None:
            # Let us know what the number is
            phoneNum = self.calls[callIndex]["staticProps"]["LineIdentification"]
            if self._debug:
                if phoneNum != "":
                    print(f"Disconnected call from/to {phoneNum}")
                else:
                    print(f"Disconnected call from/to unknown number")

        # Run extra callback if we can
        if callable(self.handleCallRemoveExtra):
            self.handleCallRemoveExtra(self.calls[callIndex])
        
        if callIndex != None:
            # Delete from list
            del self.calls[callIndex]

if __name__ == "__main__":
    callHandler = VoiceCallHandler()

    while True:
        time.sleep(100000)



