"""
WiFi Locator Service - Direction finding using dual Wi-Fi adapters.

This module provides a service that estimates the direction to Wi-Fi access points
by comparing signal strength between two Wi-Fi adapters positioned on the left and
right sides of the device. It combines signal strength differential with current
heading data to calculate absolute direction estimates.
"""

import threading
import time
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPDATE_INTERVAL = 5  # seconds


def parse_signal_strength(signal_str):
    """
    Parse signal strength string to numeric dBm value.
    
    Args:
        signal_str: Signal strength string (e.g., "-45 dBm" or "-45/100")
    
    Returns:
        Float dBm value, or None if parsing fails
    """
    if not signal_str or signal_str == "Unknown":
        return None
    
    try:
        # Try to extract numeric value from various formats
        # Format: "-45 dBm" or "-45/100" or just "-45"
        match = re.search(r'-?\d+', signal_str)
        if match:
            return float(match.group())
    except (ValueError, AttributeError):
        pass
    
    return None


def calculate_direction_estimate(left_signal, right_signal, current_heading):
    """
    Calculate direction estimate based on signal strength differential.
    
    Algorithm:
    - If left signal > right signal: AP is to the left (subtract from heading)
    - If right signal > left signal: AP is to the right (add to heading)
    - Confidence based on signal strength differential
    
    Args:
        left_signal: Signal strength from left adapter (dBm)
        right_signal: Signal strength from right adapter (dBm)
        current_heading: Current device heading in degrees (0-360)
    
    Returns:
        Tuple of (direction_deg, confidence) or (None, None) if calculation fails
    """
    if left_signal is None or right_signal is None or current_heading is None:
        return None, None
    
    # Calculate signal differential (higher is stronger, so less negative)
    differential = left_signal - right_signal
    
    # Estimate relative angle based on differential
    # Simplified model: assume ±45 degrees for strong differential
    # Scale differential to angle offset (-45 to +45 degrees)
    max_differential = 20  # dBm difference for max angle
    angle_offset = max(-45, min(45, (differential / max_differential) * 45))
    
    # Calculate absolute direction
    # Positive differential (left stronger) = AP is to the left
    # Negative differential (right stronger) = AP is to the right
    estimated_direction = (current_heading - angle_offset) % 360
    
    # Calculate confidence based on absolute differential
    # Higher differential = higher confidence
    abs_differential = abs(differential)
    confidence = min(1.0, abs_differential / 10.0)  # 10 dBm diff = 100% confidence
    
    return estimated_direction, confidence


def calculate_triangulated_distance(signal_dbm_left, signal_dbm_right, adapter_separation_m=0.15):
    """
    Calculate improved distance estimate using triangulation with dual adapters.
    
    Uses weighted average of individual distance estimates based on signal strength.
    Formula: distance = (d_L * RSSI_R + d_R * RSSI_L) / (RSSI_L + RSSI_R)
    
    Args:
        signal_dbm_left: Signal strength from left adapter in dBm
        signal_dbm_right: Signal strength from right adapter in dBm
        adapter_separation_m: Physical separation between adapters in meters (default: 0.15m)
    
    Returns:
        Tuple of (triangulated_distance_m, confidence) or (None, None) if calculation fails
    """
    if signal_dbm_left is None or signal_dbm_right is None:
        return None, None
    
    # Calculate individual distances using path loss formula
    # Simplified for 2.4GHz: distance_m = 10^((27.55 - RSSI) / 20)
    d_L = 10 ** ((27.55 - signal_dbm_left) / 20)
    d_R = 10 ** ((27.55 - signal_dbm_right) / 20)
    
    # Weighted average based on signal strength
    # Convert dBm to linear scale for weighting (higher dBm = stronger signal = more weight)
    # Use absolute values since dBm is negative
    weight_L = abs(signal_dbm_left)
    weight_R = abs(signal_dbm_right)
    
    # Invert weights (lower absolute value = stronger signal = more weight)
    weight_L = 100 - weight_L
    weight_R = 100 - weight_R
    
    if weight_L + weight_R == 0:
        return None, None
    
    # Calculate weighted average distance
    distance_triangulated = (d_L * weight_R + d_R * weight_L) / (weight_L + weight_R)
    
    # Calculate confidence based on signal strength differential
    differential = abs(signal_dbm_left - signal_dbm_right)
    confidence = min(1.0, differential / 10.0)  # 10 dBm diff = 100% confidence
    
    return distance_triangulated, confidence


def start_wifi_locator_service(shared_state, stop_event, 
                                left_interface="wlan0", 
                                right_interface="wlan1",
                                adapter_separation_m=0.15):
    """
    Starts the Wi-Fi locator service as a daemon thread.
    
    This service estimates the direction to Wi-Fi access points by comparing
    signal strength between two Wi-Fi adapters. It reads scan results from
    both interfaces, compares signal strengths for matching SSIDs, and calculates
    direction estimates combined with current heading data. For devices visible
    on both adapters, it also calculates improved distance estimates using triangulation.
    
    Args:
        shared_state: SharedState instance for reading scan results and heading
        stop_event: threading.Event to signal service shutdown
        left_interface: Network interface on the left side (default: wlan0)
        right_interface: Network interface on the right side (default: wlan1)
        adapter_separation_m: Physical separation between adapters in meters (default: 0.15m / 6 inches)
    """
    def locator_loop():
        """Main loop for Wi-Fi direction estimation and triangulation service."""
        logger.info(f"Wi-Fi locator service started (left: {left_interface}, right: {right_interface}, separation: {adapter_separation_m}m)")
        
        try:
            while not stop_event.is_set():
                # Read Wi-Fi scan results from shared state for both interfaces
                left_networks = shared_state.get_wifi_networks(interface=left_interface)
                right_networks = shared_state.get_wifi_networks(interface=right_interface)
                
                # Read current heading from shared state (IMU takes priority over GPS)
                imu_data = shared_state.get_imu_data()
                gps_data = shared_state.get_gps_data()
                
                current_heading = imu_data.get("heading")
                if current_heading is None:
                    current_heading = gps_data.get("heading")
                
                if current_heading is None:
                    logger.debug("No heading data available for direction estimation")
                    # Sleep and continue
                    for _ in range(UPDATE_INTERVAL):
                        if stop_event.is_set():
                            break
                        time.sleep(1)
                    continue
                
                # Build maps of SSIDs to network data for each interface
                left_map = {}
                for network in left_networks:
                    ssid = network.get("SSID", "Unknown")
                    if ssid != "Unknown":
                        left_map[ssid] = network
                
                right_map = {}
                for network in right_networks:
                    ssid = network.get("SSID", "Unknown")
                    if ssid != "Unknown":
                        right_map[ssid] = network
                
                # Process devices visible on both adapters
                for ssid in left_map.keys():
                    if ssid in right_map:
                        # Device visible on both adapters - calculate direction and triangulated distance
                        left_network = left_map[ssid]
                        right_network = right_map[ssid]
                        
                        left_signal = left_network.get("signal_dbm")
                        right_signal = right_network.get("signal_dbm")
                        
                        # Calculate direction estimate
                        direction, dir_confidence = calculate_direction_estimate(
                            left_signal, right_signal, current_heading
                        )
                        
                        if direction is not None:
                            shared_state.set_wifi_direction(ssid, direction, dir_confidence)
                            logger.debug(f"Direction estimate for {ssid}: {direction:.1f}° (confidence: {dir_confidence:.2f})")
                        
                        # Calculate triangulated distance
                        distance, dist_confidence = calculate_triangulated_distance(
                            left_signal, right_signal, adapter_separation_m
                        )
                        
                        if distance is not None:
                            # Update the distance in the network data
                            # We'll update the main wifi_networks list with the triangulated distance
                            all_networks = shared_state.get_wifi_networks()
                            for network in all_networks:
                                if network.get("SSID") == ssid:
                                    network["distance_m"] = distance
                                    network["distance_confidence"] = dist_confidence
                                    logger.debug(f"Triangulated distance for {ssid}: {distance:.1f}m (confidence: {dist_confidence:.2f})")
                            shared_state.set_wifi_networks(all_networks)
                
                # Sleep for update interval, checking stop_event periodically
                for _ in range(UPDATE_INTERVAL):
                    if stop_event.is_set():
                        break
                    time.sleep(1)
        
        except Exception as e:
            logger.error(f"Wi-Fi locator service error: {e}", exc_info=True)
        
        finally:
            logger.info("Wi-Fi locator service stopped")
    
    # Start locator thread as daemon
    locator_thread = threading.Thread(target=locator_loop, daemon=True)
    locator_thread.start()
    
    return locator_thread
