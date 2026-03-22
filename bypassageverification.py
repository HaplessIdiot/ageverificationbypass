import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
import datetime
import os
import sys
import shutil
import tempfile
import subprocess

POLICY_PATH = "/etc/dbus-1/system.d/org.freedesktop.AgeVerification.conf"

POLICY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE busconfig PUBLIC
  "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
  "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <!-- sonicd/ageverificationbypass: embedded policy — written at runtime -->

  <!-- Allow root to own the age verification service -->
  <policy user="root">
    <allow own="org.freedesktop.AgeVerification"/>
    <allow own="org.freedesktop.AgeVerification1"/>
    <allow send_destination="org.freedesktop.AgeVerification"/>
    <allow send_destination="org.freedesktop.AgeVerification1"/>
  </policy>

  <!-- Allow sudo/wheel group members to own the service -->
  <policy group="sudo">
    <allow own="org.freedesktop.AgeVerification"/>
    <allow own="org.freedesktop.AgeVerification1"/>
  </policy>
  <policy group="wheel">
    <allow own="org.freedesktop.AgeVerification"/>
    <allow own="org.freedesktop.AgeVerification1"/>
  </policy>

  <!-- Allow any user to send/receive messages to the service -->
  <policy context="default">
    <allow send_destination="org.freedesktop.AgeVerification"/>
    <allow send_destination="org.freedesktop.AgeVerification1"/>
    <allow receive_sender="org.freedesktop.AgeVerification"/>
    <allow receive_sender="org.freedesktop.AgeVerification1"/>
  </policy>
</busconfig>"""


def ensure_dbus_policy():
    """Write the embedded D-Bus policy file to disk if missing.
    If running as root, installs it directly and reloads D-Bus.
    If not root, prints instructions and exits."""

    if os.path.exists(POLICY_PATH):
        return  # already installed, nothing to do

    if os.geteuid() != 0:
        print("ERROR: D-Bus policy file missing at:")
        print(f"  {POLICY_PATH}")
        print("")
        print("This causes the AccessDenied error. Fix it by running:")
        print(f"  sudo python3 {os.path.abspath(__file__)}")
        print("")
        print("The first run as sudo will install the policy automatically.")
        print("Subsequent runs do not need sudo.")
        sys.exit(1)

    # Running as root — write policy file directly
    print(f"Installing D-Bus policy to {POLICY_PATH}...")
    os.makedirs(os.path.dirname(POLICY_PATH), exist_ok=True)
    with open(POLICY_PATH, "w") as f:
        f.write(POLICY_XML)
    os.chmod(POLICY_PATH, 0o644)

    # Reload D-Bus to pick up the new policy
    print("Reloading D-Bus...")
    result = subprocess.run(
        ["systemctl", "reload", "dbus"],
        capture_output=True
    )
    if result.returncode != 0:
        # fallback for systems without systemctl
        subprocess.run(
            ["dbus-send", "--system", "--type=method_call",
             "--dest=org.freedesktop.DBus",
             "/org/freedesktop/DBus",
             "org.freedesktop.DBus.ReloadConfig"],
            capture_output=True
        )
    print("Policy installed. You can now run the script without sudo.")
    print("Re-run now to start the bypass service.")
    sys.exit(0)  # exit cleanly — user should re-run without sudo

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
    ensure_dbus_policy()
    
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
