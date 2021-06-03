import dbus


def proxyobj(bus, path, interface):
    """ commodity to apply an interface to a proxy object """
    obj = bus.get_object('org.bluez', path)
    print(obj)
    return dbus.Interface(obj, interface)


def filter_by_interface(objects, interface_name):
    """ filters the objects based on their support
        for the specified interface """
    result = []
    for path in objects.keys():
        interfaces = objects[path]
        for interface in interfaces.keys():
            if interface == interface_name:
                result.append(path)
    return result


bus = dbus.SystemBus()

# we need a dbus object manager
manager = proxyobj(bus, "/", "org.freedesktop.DBus.ObjectManager")
objects = manager.GetManagedObjects()

# once we get the objects we have to pick the bluetooth devices.
# They support the org.bluez.Device1 interface
devices = filter_by_interface(objects, "org.bluez.Device1")

print(devices)
# now we are ready to get the informations we need
bt_devices = []
for device in devices:
    obj = proxyobj(bus, device, 'org.freedesktop.DBus.Properties')
    bt_devices.append({
        "name": str(obj.Get("org.bluez.Device1", "Name")),
        "addr": str(obj.Get("org.bluez.Device1", "Address")),
        "paired": bool(obj.Get("org.bluez.Device1", "Paired")),
        "connected": bool(obj.Get("org.bluez.Device1", "Connected"))
    })  
print(bt_devices)