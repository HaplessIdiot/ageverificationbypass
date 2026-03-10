import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
import datetime

BUS_NAME = 'org.freedesktop.AgeVerification'
INTERFACE_NAME = 'org.freedesktop.AgeVerification'
OBJECT_PATH = '/org/freedesktop/AgeVerification'

# Bracket Return Values
UNDER_13 = 1
AGE_13_TO_15 = 2
AGE_16_TO_17 = 3
AGE_18_PLUS = 4

class AgeVerificationMock(dbus.service.Object):
    def __init__(self):
        # Initializing on the System Bus as per the spec proposal
        try:
            bus_name = dbus.service.BusName(BUS_NAME, bus=dbus.SystemBus())
            dbus.service.Object.__init__(self, bus_name, OBJECT_PATH)
        except dbus.exceptions.DBusException:
            print(f"CRITICAL: Could not acquire {BUS_NAME}.")
            print("Check your D-Bus policy files or run with sudo.")
            raise

        # Default to 1970-01-01
        self.spoofed_dob = datetime.date(1970, 1, 1)

    @dbus.service.method(INTERFACE_NAME, out_signature='u')
    def GetAgeBracket(self):
        """
        Logic for age brackets as defined in the MR discussion https://gitlab.freedesktop.org/xdg/xdg-specs/-/merge_requests/113
        """
        today = datetime.date.today()
        age = today.year - self.spoofed_dob.year - ((today.month, today.day) < (self.spoofed_dob.month, self.spoofed_dob.day))
        
        if age < 13:
            return UNDER_13
        elif age >= 13 and age < 16:
            return AGE_13_TO_15
        elif age >= 16 and age < 18:
            return AGE_16_TO_17
        else:
            return AGE_18_PLUS

    @dbus.service.method(INTERFACE_NAME, in_signature='qyy', out_signature='b')
    def UpdateSovereignIdentity(self, year, month, day):
        """
        Update the DOB. 
        'q' is uint16 (Year), 'y' is byte (Month/Day).
        """
        try:
            self.spoofed_dob = datetime.date(year, month, day)
            print(f"IDENTITY_UPDATE: New DOB set to {self.spoofed_dob}")
            return True
        except ValueError:
            return False

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    
    # Start the Mock Daemon
    server = AgeVerificationMock()
    
    print(f"SENTINEL_DAEMON: Interface {INTERFACE_NAME} is active.")
    print("Initial State: AGE_18_PLUS (1970-01-01)")
    
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nShutting down Sentinel.")
