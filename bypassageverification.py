import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

class AgeVerificationMock(dbus.service.Object):
    def __init__(self):
        bus_name = dbus.service.BusName('org.freedesktop.AgeVerification1', bus=dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, '/org/freedesktop/AgeVerification1')

    @dbus.service.method('org.freedesktop.AgeVerification1', out_signature='u')
    def GetAgeBracket(self):
        # Always return 4 (Sovereign/18+)
        return 4 

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    AgeVerificationMock()
    GLib.MainLoop().run()
