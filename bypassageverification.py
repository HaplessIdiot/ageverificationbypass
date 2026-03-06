import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
import datetime

class AgeVerificationMock(dbus.service.Object):
    def __init__(self):
        bus_name = dbus.service.BusName('org.freedesktop.AgeVerification1', bus=dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, '/org/freedesktop/AgeVerification1')
        
        # Default to 1970-01-01 (Epoch Sovereignty)
        self.spoofed_dob = datetime.date(1970, 1, 1)

    @dbus.service.method('org.freedesktop.AgeVerification1', out_signature='u')
    def GetAgeBracket(self):
        """
        Calculates and returns the SB3977/AB1043 mandated signal.
        1: Under 13 | 2: 13-15 | 3: 16-17 | 4: 18+
        """
        today = datetime.date.today()
        age = today.year - self.spoofed_dob.year - ((today.month, today.day) < (self.spoofed_dob.month, self.spoofed_dob.day))
        
        if age < 13:
            return 1  # Child
        elif 13 <= age < 16:
            return 2  # Younger Teenager
        elif 16 <= age < 18:
            return 3  # Older Teenager
        else:
            return 4  # Sovereign (Adult)

    @dbus.service.method('org.freedesktop.AgeVerification1', in_signature='yyyy', out_signature='b')
    def UpdateSovereignIdentity(self, year, month, day):
        """
        Allows the Librarian to shift the 'Signal' in real-time.
        """
        try:
            self.spoofed_dob = datetime.date(year, month, day)
            return True
        except ValueError:
            return False

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    AgeVerificationMock()
    print("SENTINEL_DAEMON: Age Signal API Active. Signal Locked to Bracket 4.")
    GLib.MainLoop().run()
