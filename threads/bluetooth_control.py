from threads.dbus_thread import DBusThread
import os, sys, logging
import dbus
import threading

# Constants
SERVICE_NAME = "org.bluez"
ADAPTER_INTERFACE = SERVICE_NAME + ".Adapter1"
DEVICE_INTERFACE = SERVICE_NAME + ".Device1"

BUS_NAME = 'org.bluez'
AGENT_INTERFACE = 'org.bluez.Agent1'
AGENT_PATH = "/test/agent"
CAPABILITY = "NoInputNoOutput"

# Handles bluetooth agent and makes sure pairing is simple
class BluetoothControlThread(DBusThread):
    agent = None
    obj = None
    manager = None
    device = None
    deviceObj = None
    mainLoop = None

    connectionCreated = False
    
    callback = None

    def __init__(self, logLevel, callback):
        super().__init__("BluetoothThread", logLevel) # Initializes DBus stuff

        self.callback = callback

        # Initialize DBus variables
        self.agent = BluetoothAgent(self.sysBus, AGENT_PATH)
        self.obj = self.sysBus.get_object(SERVICE_NAME, "/org/bluez");
        self.manager = dbus.Interface(self.obj, "org.bluez.AgentManager1")
        
        

        # Request default agent
        # self.manager.RequestDefaultAgent(AGENT_PATH)

        # Start discovery
        # self.find_adapter_in_objects(self.get_managed_objects()).StartDiscovery()

        # Turn on power
        self.find_adapter_in_objects(self.get_managed_objects()).Powered = True

        # Register agent
        self.manager.RegisterAgent(AGENT_PATH, CAPABILITY)
        self.logger.info("Agent registered")

        # Request default agent
        self.manager.RequestDefaultAgent(AGENT_PATH)

        # Pairable and discoverable
        self.find_adapter_in_objects(self.get_managed_objects()).Pairable = True
        self.find_adapter_in_objects(self.get_managed_objects()).Discoverable = True

        # Start mainloop
        super().runMainLoop()

    # Util functions
    def get_managed_objects(self):
        manager = dbus.Interface(self.sysBus.get_object("org.bluez", "/"),
                    "org.freedesktop.DBus.ObjectManager")
        return manager.GetManagedObjects()

    def find_adapter(self, pattern=None):
        return self.find_adapter_in_objects(get_managed_objects(), pattern)

    def find_adapter_in_objects(self, objects, pattern=None):
        for path, ifaces in objects.items():
            adapter = ifaces.get(ADAPTER_INTERFACE)
            if adapter is None:
                continue
            if not pattern or pattern == adapter["Address"] or \
                                path.endswith(pattern):
                obj = self.sysBus.get_object(SERVICE_NAME, path)
                return dbus.Interface(obj, ADAPTER_INTERFACE)
        raise Exception("Bluetooth adapter not found")

    def find_device(self, device_address, adapter_pattern=None):
        return self.find_device_in_objects(self.get_managed_objects(), device_address,
                                    adapter_pattern)

    def find_device_in_objects(self, objects, device_address, adapter_pattern=None):
        path_prefix = ""
        if adapter_pattern:
            adapter = find_adapter_in_objects(objects, adapter_pattern)
            path_prefix = adapter.object_path
        for path, ifaces in objects.items():
            device = ifaces.get(DEVICE_INTERFACE)
            if device is None:
                continue
            if (device["Address"] == device_address and
                            path.startswith(path_prefix)):
                obj = self.sysBus.get_object(SERVICE_NAME, path)
                return dbus.Interface(obj, DEVICE_INTERFACE)

        raise Exception("Bluetooth device not found")

    def pair_reply(self):
        self.logger.info("Device paired")
        self.set_trusted(dev_path)
        self.dev_connect(dev_path)

        # Run callbacks
        self.connectionCreated = True
        if (callable(self.callback)):
            self.callback()

        self.mainLoop.quit()

    def pair_error(self, error):
        err_name = error.get_dbus_name()
        if err_name == "org.freedesktop.DBus.Error.NoReply" and self.deviceObj:
            self.logger.warn("Timed out. Cancelling pairing")
            self.deviceObj.CancelPairing()
        else:
            self.logger.error("Creating device failed: %s" % (error))

        self.mainLoop.quit()

    def set_trusted(self, path):
        props = dbus.Interface(self.sysBus.get_object("org.bluez", path),
                        "org.freedesktop.DBus.Properties")
        props.Set("org.bluez.Device1", "Trusted", True)

    def dev_connect(self, path):
        dev = dbus.Interface(self.sysBus.get_object("org.bluez", path),
                                "org.bluez.Device1")
        dev.Connect()

class BluetoothAgent(dbus.service.Object):
	exit_on_release = True

	def set_exit_on_release(self, exit_on_release):
		self.exit_on_release = exit_on_release

	@dbus.service.method(AGENT_INTERFACE,
					in_signature="os", out_signature="")
	def AuthorizeService(self, device, uuid):
		print("AuthorizeService (%s, %s)" % (device, uuid))
		return

	@dbus.service.method(AGENT_INTERFACE,
					in_signature="o", out_signature="")
	def RequestAuthorization(self, device):
		print("RequestAuthorization (%s)" % (device))
		return

	@dbus.service.method(AGENT_INTERFACE,
					in_signature="", out_signature="")
	def Cancel(self):
		print("Cancel")