# wifi_scanner.py
# Scans for nearby Wi-Fi networks and parses output

import subprocess
import time
import threading
import logging
import re
import math
from theme import assign_device_color

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCAN_INTERVAL = 15  # seconds

# Drone manufacturer patterns for device classification
DRONE_PATTERNS = [
    r'DJI',
    r'Phantom',
    r'Mavic',
    r'Parrot',
    r'Autel',
    r'Bebop',
    r'Anafi',
    r'EVO',
]

# Common router channels for 2.4GHz
COMMON_24GHZ_CHANNELS = ['1', '6', '11']


def classify_device(ssid, frequency, channel):
    """
    Classify RF device type based on SSID patterns, frequency, and channel.
    
    Args:
        ssid: Network SSID
        frequency: Frequency band ("2.4GHz" or "5.8GHz")
        channel: Channel number as string
        
    Returns:
        Device type: "drone", "router", or "unknown"
    """
    # Check for drone manufacturer patterns in SSID
    for pattern in DRONE_PATTERNS:
        if re.search(pattern, ssid, re.IGNORECASE):
            return "drone"
    
    # 5.8GHz devices are more likely to be drones (FPV video transmission)
    if frequency == "5.8GHz":
        # If on 5.8GHz and not a common router SSID pattern, likely a drone
        if not any(common in ssid.lower() for common in ['router', 'wifi', 'network', 'home', 'guest']):
            return "drone"
    
    # Standard Wi-Fi on common channels is likely a router
    if frequency == "2.4GHz" and channel in COMMON_24GHZ_CHANNELS:
        return "router"
    
    # If we have a reasonable SSID and it's on 2.4GHz, assume router
    if frequency == "2.4GHz" and ssid and ssid != "Unknown":
        return "router"
    
    # Default to unknown for unrecognized patterns
    return "unknown"


def estimate_distance(signal_dbm, frequency, device_type):
    """
    Estimate distance to RF device using path loss formula.
    
    Formula: distance_m = 10^((TxPower - RSSI - PathLoss) / 20)
    Simplified for 2.4GHz: distance_m = 10^((27.55 - RSSI) / 20)
    Simplified for 5.8GHz: distance_m = 10^((27.55 - RSSI - 7.6) / 20)
    
    Args:
        signal_dbm: Signal strength in dBm (negative value)
        frequency: Frequency band ("2.4GHz" or "5.8GHz")
        device_type: Device type ("router", "drone", "unknown")
        
    Returns:
        Estimated distance in meters
    """
    # Adjust transmit power based on device type
    if device_type == "drone" and frequency == "5.8GHz":
        # Drones typically use higher power for video transmission
        tx_power = 27  # dBm (500mW)
    else:
        # Standard router transmit power
        tx_power = 20  # dBm (100mW)
    
    # Calculate distance based on frequency
    if frequency == "5.8GHz":
        # 5.8GHz has higher path loss
        # Simplified: distance_m = 10^((27.55 - RSSI - 7.6) / 20)
        distance_m = 10 ** ((tx_power + 7.55 - signal_dbm - 7.6) / 20)
    else:
        # 2.4GHz
        # Simplified: distance_m = 10^((27.55 - RSSI) / 20)
        distance_m = 10 ** ((tx_power + 7.55 - signal_dbm) / 20)
    
    return distance_m


def extract_frequency_from_channel(channel):
    """
    Determine frequency band from channel number.
    
    Args:
        channel: Channel number as string
        
    Returns:
        Frequency band: "2.4GHz" or "5.8GHz"
    """
    try:
        channel_num = int(channel)
        # 2.4GHz uses channels 1-14
        # 5GHz uses channels 36+ (including 5.8GHz range)
        if channel_num <= 14:
            return "2.4GHz"
        else:
            # Channels 149+ are in the 5.8GHz range, but we'll classify all 5GHz as 5.8GHz
            return "5.8GHz"
    except (ValueError, TypeError):
        # Default to 2.4GHz if channel is unknown
        return "2.4GHz"


def parse_signal_dbm(signal_str):
    """
    Parse signal strength string to extract dBm value.
    
    Args:
        signal_str: Signal string like "-45 dBm" or "45/100"
        
    Returns:
        Signal strength in dBm as integer, or None if parsing fails
    """
    try:
        # Try to extract dBm value
        if "dBm" in signal_str:
            # Format: "-45 dBm"
            return int(signal_str.split("dBm")[0].strip())
        elif "/" in signal_str:
            # Format: "45/100" - convert to approximate dBm
            # Assuming 0/100 = -100 dBm, 100/100 = -30 dBm
            quality = int(signal_str.split("/")[0])
            return -100 + int(quality * 0.7)  # Rough conversion
        else:
            # Try to parse as integer
            return int(signal_str)
    except (ValueError, AttributeError):
        return None


def scan_wifi(interface="wlan0"):
    """
    Scans for nearby Wi-Fi networks using 'iwlist' and returns
    a list of dictionaries with SSID, signal strength, channel, security,
    device type, frequency, distance estimate, and unique color.
    
    Args:
        interface: Network interface to scan (default: wlan0)
    
    Returns:
        List of network dictionaries with enhanced RF device information
    """
    networks = []
    try:
        result = subprocess.run(
            ["iwlist", interface, "scan"], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
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

            # Extract frequency from channel
            frequency = extract_frequency_from_channel(channel)
            
            # Parse signal strength to dBm
            signal_dbm = parse_signal_dbm(signal)
            
            # Classify device type
            device_type = classify_device(ssid, frequency, channel)
            
            # Estimate distance
            distance_m = 0.0
            if signal_dbm is not None:
                distance_m = estimate_distance(signal_dbm, frequency, device_type)
            
            # Assign unique color to device
            color = assign_device_color(ssid)

            networks.append({
                "SSID": ssid,
                "Signal": signal,
                "signal_dbm": signal_dbm if signal_dbm is not None else -100,
                "Channel": channel,
                "Security": security,
                "device_type": device_type,
                "frequency": frequency,
                "distance_m": distance_m,
                "color": color
            })
    except subprocess.TimeoutExpired:
        logger.error(f"Wi-Fi scan timeout on interface {interface}")
    except FileNotFoundError:
        logger.error(f"iwlist command not found - ensure wireless-tools is installed")
    except PermissionError:
        logger.error(f"Permission denied scanning interface {interface} - may need sudo/root")
    except Exception as e:
        logger.error(f"Wi-Fi scan error on interface {interface}: {e}")

    return networks


def start_wifi_scanner_service(shared_state, stop_event, interface="wlan0"):
    """
    Starts the Wi-Fi scanner service as a daemon thread.
    
    This service continuously scans for Wi-Fi networks on the specified interface
    and writes the results to the shared state. The scan runs every SCAN_INTERVAL
    seconds and can be stopped gracefully via the stop_event.
    
    Args:
        shared_state: SharedState instance for storing scan results
        stop_event: threading.Event to signal service shutdown
        interface: Network interface to scan (default: wlan0)
    """
    def scanner_loop():
        """Main loop for Wi-Fi scanning service."""
        logger.info(f"Wi-Fi scanner service started on interface {interface}")
        
        try:
            while not stop_event.is_set():
                # Perform Wi-Fi scan
                networks = scan_wifi(interface)
                
                # Write results to shared state (both global and per-interface)
                shared_state.set_wifi_networks(networks, interface=interface)
                
                if networks:
                    logger.debug(f"Scanned {len(networks)} Wi-Fi networks on {interface}")
                else:
                    logger.warning(f"No Wi-Fi networks found on {interface}")
                
                # Sleep for scan interval, checking stop_event periodically
                for _ in range(SCAN_INTERVAL):
                    if stop_event.is_set():
                        break
                    time.sleep(1)
        
        except Exception as e:
            logger.error(f"Wi-Fi scanner service error: {e}", exc_info=True)
        
        finally:
            logger.info(f"Wi-Fi scanner service stopped on interface {interface}")
    
    # Start scanner thread as daemon
    scanner_thread = threading.Thread(target=scanner_loop, daemon=True)
    scanner_thread.start()
    
    return scanner_thread
