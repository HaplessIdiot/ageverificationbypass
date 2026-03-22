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
import random

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


def generate_adult_birthdate():
    """Generate a random plausible adult birthdate.
    Returns a date string in YYYY-MM-DD format.

    Rules:
    - Age between 19 and 89 years old (plausible adult range)
    - Weighted toward common adult ages (25-65) to avoid outliers
      that could be flagged as suspicious
    - Month and day are fully random and valid for the month
    - Result changes on every call — not fingerprintable
    """
    today = datetime.date.today()

    # Weighted age selection — more weight toward 25-65
    # to produce realistic adult demographics
    age_ranges = [
        (19, 24, 10),   # young adults — 10% weight
        (25, 45, 50),   # core adult range — 50% weight
        (46, 65, 30),   # middle age — 30% weight
        (66, 89, 10),   # older adults — 10% weight
    ]

    # Pick a range based on weights
    total_weight = sum(w for _, _, w in age_ranges)
    r = random.randint(1, total_weight)
    cumulative = 0
    min_age, max_age = 25, 45  # fallback
    for lo, hi, weight in age_ranges:
        cumulative += weight
        if r <= cumulative:
            min_age, max_age = lo, hi
            break

    age = random.randint(min_age, max_age)

    # Calculate birth year
    birth_year = today.year - age

    # Random month
    birth_month = random.randint(1, 12)

    # Random day valid for the month and year
    # Use the last day of the month to get the max valid day
    if birth_month == 12:
        last_day = 31
    else:
        last_day = (datetime.date(birth_year, birth_month + 1, 1) -
                    datetime.timedelta(days=1)).day

    birth_day = random.randint(1, last_day)

    date_str = datetime.date(birth_year, birth_month, birth_day).strftime(
        "%Y-%m-%d"
    )
    print(f"[avb] spoofed birthdate: {date_str} (age: {age})")
    return date_str


def get_spoofed_age_bracket():
    """Return an age bracket string consistent with the spoofed birthdate.
    Always returns adult bracket regardless of generated date."""
    return "adult"


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


def _parse_iso_date(date_str):
    """Parse YYYY-MM-DD string to datetime.date object."""
    parts = date_str.split('-')
    return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))


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

        # Generate a random plausible adult birthdate on each invocation
        date_str = generate_adult_birthdate()
        self.spoofed_dob = _parse_iso_date(date_str)

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
    print("Initial State: AGE_18_PLUS (randomly generated adult birthdate)")
    
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nShutting down Sentinel.")
