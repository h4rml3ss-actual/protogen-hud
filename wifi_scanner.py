# wifi_scanner.py
# Scans for nearby Wi-Fi networks and parses output

import subprocess
import time

_last_wifi_scan = []
_last_scan_time = 0
_current_index = 0
SCAN_INTERVAL = 15  # seconds
ROTATE_INTERVAL = 5  # seconds
GROUP_SIZE = 3       # number of networks to show at a time

def scan_wifi():
    """
    Scans for nearby Wi-Fi networks using 'iwlist' and returns
    a list of dictionaries with SSID, signal strength, channel, and encryption.
    """
    networks = []
    try:
        result = subprocess.run(["iwlist", "wlan0", "scan"], capture_output=True, text=True, timeout=5)
        output = result.stdout

        for block in output.split("Cell "):
            if "ESSID" not in block:
                continue

            ssid = "Unknown"
            signal = "Unknown"
            channel = "Unknown"
            security = "Open"

            for line in block.split("\n"):
                line = line.strip()
                if "ESSID:" in line:
                    ssid = line.split("ESSID:")[1].strip().strip('"')
                elif "Signal level=" in line:
                    signal = line.split("Signal level=")[1].strip()
                elif "Channel:" in line:
                    channel = line.split("Channel:")[1].strip()
                elif "Encryption key:" in line:
                    key = line.split("Encryption key:")[1].strip()
                    if key == "on":
                        security = "Secured"

            networks.append({
                "SSID": ssid,
                "Signal": signal,
                "Channel": channel,
                "Security": security
            })
    except Exception as e:
        print(f"Wi-Fi scan error: {e}")

    return networks[:5]  # Limit to top 5 results

def get_display_wifi():
    """
    Returns a rotating subset of nearby Wi-Fi networks to display,
    updating the scan no more than once every SCAN_INTERVAL seconds.
    """
    global _last_wifi_scan, _last_scan_time, _current_index

    now = time.time()
    # Check if the scan interval has passed to perform a fresh Wi-Fi scan and reset rotation index
    if now - _last_scan_time > SCAN_INTERVAL:
        _last_wifi_scan = scan_wifi()
        _last_scan_time = now
        _current_index = 0

    # If no networks were found during the scan, return an empty list
    if not _last_wifi_scan:
        return []

    total = len(_last_wifi_scan)
    # Calculate the starting index for the current display group based on the rotation index and group size
    start = (_current_index * GROUP_SIZE) % total
    end = start + GROUP_SIZE
    # Slice the cached network list to obtain the current group of networks to display
    display = _last_wifi_scan[start:end]

    # If the rotation interval has passed, update the rotation index to show the next group of networks
    if now - _last_scan_time > ROTATE_INTERVAL:
        _current_index += 1
        # Update the last scan time to delay the next rotation cycle
        _last_scan_time = now

    return display
