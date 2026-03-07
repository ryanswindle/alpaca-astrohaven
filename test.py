import time

from alpaca.dome import Dome
from config import config


SHUTTER_STATES = {0: "Open", 1: "Closed", 2: "Opening", 3: "Closing", 4: "Error"}
def label(status_code):
    return SHUTTER_STATES.get(status_code, f"Unknown ({status_code})")

def wait_for(dome, target, timeout=60, interval=2):
    """Poll ShutterStatus until it matches *target* or timeout."""
    elapsed = 0
    while elapsed < timeout:
        status = dome.ShutterStatus
        print(f"  ShutterStatus: {label(status)}")
        if status == target:
            return status
        time.sleep(interval)
        elapsed += interval
    print(f"  Timed out waiting for {label(target)}")
    return dome.ShutterStatus

dome = Dome(f"localhost:{config.server.port}", 0)

print(f"  Name:   {dome.Name}")
print(f"  Driver: {dome.DriverVersion}\n")

# Connect
print("Connecting...")
dome.Connected = True
t0 = time.time()
while not dome.Connected:
    time.sleep(0.1)
    if (time.time()-t0) > 30:
        import pdb; pdb.set_trace()
print(f"  Connected: {dome.Connected}")

# Status
status = dome.ShutterStatus
print(f"  ShutterStatus: {label(status)}")
print(f"  Slewing: {dome.Slewing}")

print("\nOpening shutters in 10 seconds...")
time.sleep(10)

# Open
print("\nOpening shutters...")
dome.OpenShutter()
wait_for(dome, 0)  # 0 = Open

print("\nClosing shutters in 10 seconds...")
time.sleep(10)

# Close
print("\nClosing shutters...")
dome.CloseShutter()
wait_for(dome, 1)  # 1 = Closed

print("\nOpening shutters in 10 seconds, followed 1 second later by an abort and a close...")
time.sleep(10)

# Abort test: open, wait 1s, abort, wait 1s, close
print("\n--- Abort test ---")
print("Opening shutters...")
dome.OpenShutter()
time.sleep(1)
print("Aborting slew...")
dome.AbortSlew()
print(f"  ShutterStatus: {label(dome.ShutterStatus)}")
time.sleep(1)
print("Closing shutters...")
dome.CloseShutter()
wait_for(dome, 1)  # 1 = Closed

# Disconnect
print("\nDisconnecting...")
dome.Connected = False
print(f"  Connected: {dome.Connected}")
print()