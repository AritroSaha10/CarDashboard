from threads.dbus_thread import DBusThread
import os, sys, logging, subprocess
import dbus
import threading
from time import sleep

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
    
    def __init__(self, logLevel):
        super().__init__("BluetoothThread", logLevel) # Initializes DBus stuff

        # Initialize DBus variables
        self.agent = BluetoothAgent(self.sysBus, AGENT_PATH)
        self.obj = self.sysBus.get_object(SERVICE_NAME, "/org/bluez");
        self.manager = dbus.Interface(self.obj, "org.bluez.AgentManager1")

        # Turn on power
        self.find_adapter_in_objects(self.get_managed_objects()).Powered = True

        # Pairable and discoverable
        self.find_adapter_in_objects(self.get_managed_objects()).Pairable = True
        self.find_adapter_in_objects(self.get_managed_objects()).Discoverable = True

        # Register agent
        self.manager.RegisterAgent(AGENT_PATH, CAPABILITY)
        self.logger.info("Agent registered")

        # Request default agent
        self.manager.RequestDefaultAgent(AGENT_PATH)

        # I think this is the thing that makes it actually discoverable
        subprocess.run("./turnOnPair", stdout=subprocess.PIPE)

        # Start mainloop
        super().runMainLoop()
    
    def wait_for_connection(self):
        starting = self.get_all_connected()
        addrs = [device["addr"] for device in starting]
        
        # Wait for device to connect
        while True:
            curr = self.get_all_connected()
            if len(curr) == 1:
                self.logger.info(f"{curr[0]['name']} is connecting...")

                # Check if it was paired before
                wasPairedBefore = False
                for i, dic in enumerate(curr):
                    if dic["addr"] in addrs:
                        wasPairedBefore = True
                        break

                # If not paired, wait for a service authorization before continuing
                if not wasPairedBefore:
                    self.logger.debug("Device is being paired, waiting for authorization before continuing...")
                    while True:
                        if self.agent.auth_count > 0:
                            self.logger.info("At least 1 service has been authorized!")
                            break
                        self.logger.info("Waiting...")
                        sleep(1.5)
                
                # Wait 1 second for services to authorize (takes less time but better to be safe since relying on time)
                sleep(1)

                # Should be connected
                self.logger.info(f"{curr[0]['name']} has connected!")
                
                # Make device undiscoverable so others can't connect
                subprocess.run("./makeUndiscoverable", stdout=subprocess.PIPE)
                break
            else:
                self.logger.info("Waiting for connection...")
            sleep(1)
    
    # Util functions
    def get_all_connected(self):
        interface_name = "org.bluez.Device1"
        objects = self.get_managed_objects()
        results = []

        for path in objects.keys():
            interfaces = objects[path]
            for interface in interfaces.keys():
                if interface == interface_name:
                    results.append(path)

        real_result = []

        for result in results:
            obj = self.sysBus.get_object('org.bluez', result)
            iface = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
            real_result.append({
                "obj": dbus.Interface(obj, "org.bluez.Device1"),
                "name": str(iface.Get("org.bluez.Device1", "Name")),
                "addr": str(iface.Get("org.bluez.Device1", "Address")),
                "paired": bool(iface.Get("org.bluez.Device1", "Paired")),
                "connected": bool(iface.Get("org.bluez.Device1", "Connected"))
            })
        
        real_result = [result for result in real_result if result["connected"]]
        return real_result
    
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
    auth_count = 0

    def set_exit_on_release(self, exit_on_release):
        self.exit_on_release = exit_on_release

    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        print("AuthorizeService (%s, %s)" % (device, uuid))
        self.auth_count += 1
        return

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        print("RequestAuthorization (%s)" % (device))
        return

    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Cancel(self):
        print("Cancel")