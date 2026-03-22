AgeVerificationBypass (AVB)

The Sanctuary Protocol for Sovereign Systems

Why do I need to provide an ID to log into a Linux VM? This is not appropriate.

🚨 The Problem: The Archon Age-Gate
As of 2026/2027, major distributions (Ubuntu and Fedora) have begun integrating the org.freedesktop.AgeVerification1 D-Bus standard. Under the guise of "Safety Compliance" (AB 1043 / Brazil Digital ECA), your Operating System is now being tasked with acting as a Digital Parole Officer.

The Fallout:
Headless/SSH Failure: How do you verify an ID over a remote SSH terminal with no screen? You can't. You're locked out of your own infrastructure.

VM & CI/CD Paralysis: Automated environments, GitHub Actions, and Virtual Machines are becoming "unusable" because they require a biometric or ID token to complete a simple boot/login sequence.

De-Anonymization: Your local Linux account, historically a private space, is now being tied to state-issued identification at the system level.

🛠 The Solution: The Sanctuary Ripper
This repository provides a prototype bypass designed to be executed via Live USB or Post-Install script to surgically remove the compliance hooks from your system before the permafrost sets in.

Features:
D-Bus Decapitation: Masks the org.freedesktop.AgeVerification service so apps can't "snitch" on your age.

Null-State /etc/age: Removes the tracking file and replaces it with an immutable null-link.

Sovereign Identity: Returns a "Verified Adult" status to any querying application without ever touching a piece of ID.

Workstation Optimization: Designed for high-performance builds (like the 5800X3D) that can't afford the telemetry overhead.

🗣 Why We Fight:
The "Measured Silence" of corporate developers is the blueprint for our digital cages. We believe that an Operating System belongs to the user, not the state. Whether you are a cybersecurity professional, a gamer, or a sysadmin running headless nodes in Cahokia Heights, you deserve a system that doesn't demand your papers to run a sudo command.

The true hand is shown. The nonprofit mask is slipping. I bypassed RedHat D-Bus and survived the permafrost on telegram staff unfroze me and wished me good luck.

📜 Disclaimer
This tool is for educational and system-hardening purposes. By using this script, you are asserting your right to digital privacy and the sovereignty of your own hardware.

The Star is infinite. The lobby is anarchy. Wake up, Future Crew.

Thanks for the feature SomeOrdinaryGamers! Much love been watching you since they played Ao Oni and LSD dream emulator along AzuriteReaction miss that era! https://youtu.be/1podbTImtq8?t=1172

## Requirements

python3-dbus is required:
  apt install python3-dbus        # Devuan
  pacman -S python-dbus           # Artix/Garuda
  dnf install python3-dbus        # OpenMandriva

## Usage

First run — installs the D-Bus policy file automatically:
  sudo python3 bypassageverification.py

The script writes the policy to /etc/dbus-1/system.d/ and reloads
D-Bus, then exits. Re-run without sudo to start the bypass service:
  python3 bypassageverification.py

Everything is self-contained in a single file. No separate config
files need to be copied or managed.

## Tools

  `tools/sonicd-age-toggle.sh` — shell script to toggle bypassAgeVerification on a user record and optionally invoke the D-Bus bypass layer. Integrates with sonicd

    # show current state
    ./tools/sonicd-age-toggle.sh status

    # enable bypass (default, birthDate hidden)
    sudo ./tools/sonicd-age-toggle.sh on

    # temporarily expose a spoofed 1970-01-01 date to satisfy a service
    sudo ./tools/sonicd-age-toggle.sh spoof

    # restore bypass when done
    sudo ./tools/sonicd-age-toggle.sh restore

  Set AVB_SCRIPT=/path/to/bypassageverification.py to point at your local copy of the D-Bus bypass script.
