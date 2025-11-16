"""
config.py
---------
Configuration system for the Protogen HUD.

This module defines the configuration structure for enabling/disabling optional
hardware modules and setting interface parameters. The configuration supports
plug-and-play hardware modules including GPS, IMU, Wi-Fi adapters, and audio devices.

Configuration Options:
----------------------

Service Enable Flags:
- enable_system_metrics: Enable system performance monitoring (CPU, RAM, temp, network)
  Default: True (always recommended)
  
- enable_gps: Enable GPS tracking service for location and heading data
  Default: False (requires USB GPS device connected to gpsd)
  Hardware: USB GPS receiver (e.g., GlobalSat BU-353-S4)
  
- enable_imu: Enable IMU tracking service for precise heading/pitch/roll
  Default: False (requires BNO085 IMU sensor connected via I2C)
  Hardware: Adafruit BNO085 9-DOF IMU
  Note: IMU heading takes priority over GPS heading when both are enabled
  
- enable_wifi_scanner: Enable Wi-Fi network scanning
  Default: True (requires at least one Wi-Fi adapter)
  Hardware: Any Wi-Fi adapter supported by iwlist
  
- enable_wifi_locator: Enable Wi-Fi direction finding using dual adapters
  Default: False (requires two Wi-Fi adapters positioned left/right)
  Hardware: Two Wi-Fi adapters (e.g., dual USB Wi-Fi dongles)
  Note: Adapters must be positioned on left and right sides of device
  
- enable_audio: Enable audio visualizer with microphone input
  Default: True (requires audio input device)
  Hardware: Any microphone or audio input device

Interface Configuration:
- wifi_interface: Primary Wi-Fi interface name for scanning
  Default: "wlan0"
  Common values: "wlan0", "wlp2s0", "wlan1"
  Use 'ip link' or 'ifconfig' to find your interface name
  
- wifi_left_interface: Left-side Wi-Fi adapter for direction finding
  Default: "wlan0"
  Required when enable_wifi_locator is True
  
- wifi_right_interface: Right-side Wi-Fi adapter for direction finding
  Default: "wlan1"
  Required when enable_wifi_locator is True

Platform Notes:
---------------
- LattePanda Alpha (x86-64): All features supported
- Raspberry Pi 5 (ARM64): All features supported
- Temperature reading: Platform-specific, falls back to "N/A" if unavailable
- I2C bus: Typically /dev/i2c-1 on Raspberry Pi, /dev/i2c-0 on some x86 systems

Graceful Degradation:
---------------------
When a service is disabled or hardware is unavailable:
- The HUD continues to operate with remaining services
- Renderer displays "N/A" for missing data
- Service threads exit gracefully without crashing the system
"""

# Default configuration for the HUD system
# Modify these values based on your hardware setup
HUD_CONFIG = {
    # ===== Core Services =====
    # System metrics (CPU, RAM, temperature, network)
    # Recommended: Always enabled for system monitoring
    "enable_system_metrics": True,
    
    # ===== GPS Service =====
    # Provides: latitude, longitude, speed, heading
    # Requires: USB GPS device connected to gpsd daemon
    # Set to True if you have GPS hardware installed
    "enable_gps": False,
    
    # ===== IMU Service =====
    # Provides: precise heading, pitch, roll from BNO085 sensor
    # Requires: BNO085 IMU connected via I2C
    # Set to True if you have IMU hardware installed
    # Note: IMU heading overrides GPS heading when both are enabled
    "enable_imu": False,
    
    # ===== Wi-Fi Services =====
    # Wi-Fi Scanner: Scans for nearby networks and displays SSID/signal/channel
    # Requires: At least one Wi-Fi adapter
    # Set to True to enable Wi-Fi network scanning
    "enable_wifi_scanner": True,
    
    # Wi-Fi Locator: Estimates direction to Wi-Fi access points
    # Requires: Two Wi-Fi adapters positioned on left and right sides
    # Requires: GPS or IMU for heading reference
    # Set to True if you have dual Wi-Fi adapters for direction finding
    "enable_wifi_locator": False,
    
    # ===== Audio Service =====
    # Provides: Audio visualizer with FFT display
    # Requires: Microphone or audio input device
    # Set to True to enable audio visualization
    "enable_audio": True,
    
    # ===== Wi-Fi Interface Configuration =====
    # IMPORTANT: For Wi-Fi scanning and direction finding, use USB Wi-Fi adapters
    # DO NOT use the onboard wireless interface (typically wlan0 or wlp1s0)
    # Onboard wireless should be reserved for system connectivity
    #
    # USB Wi-Fi adapters are typically named:
    # - wlan1, wlan2 (if onboard is wlan0)
    # - wlx[mac_address] (e.g., wlx00c0ca123456)
    #
    # To identify your Wi-Fi interfaces, use these commands:
    # - 'ip link show' - list all network interfaces
    # - 'iwconfig' - show wireless interfaces
    # - 'lsusb' - verify USB Wi-Fi adapters are connected
    # - 'iw dev' - show detailed interface information
    #
    # Example output from 'iw dev':
    #   phy#0
    #     Interface wlan0
    #       type managed
    #   phy#1
    #     Interface wlan1
    #       type managed
    #
    # Primary Wi-Fi interface for scanning
    # RECOMMENDED: Use a USB Wi-Fi adapter (wlan1, wlan2, or wlx*)
    # WARNING: Do NOT use onboard wireless (wlan0, wlp1s0, wlp*)
    "wifi_scan_interface": "wlan1",
    
    # Left-side Wi-Fi adapter for direction finding
    # Only used when enable_wifi_locator is True
    # MUST be a USB adapter positioned on the LEFT side of the device
    # RECOMMENDED: Use wlan1 or first USB adapter
    "wifi_left_interface": "wlan1",
    
    # Right-side Wi-Fi adapter for direction finding
    # Only used when enable_wifi_locator is True
    # MUST be a USB adapter positioned on the RIGHT side of the device
    # RECOMMENDED: Use wlan2 or second USB adapter
    "wifi_right_interface": "wlan2",
    
    # Physical separation between left and right adapters (in meters)
    # Used for triangulation distance calculations
    # Typical fursuit head width: 15-20cm
    # Default: 0.15m (15cm / 6 inches)
    # Adjust based on your actual adapter placement
    "adapter_separation_m": 0.15,
}


def get_config():
    """
    Returns the HUD configuration dictionary.
    
    This function can be extended to load configuration from a file
    (e.g., JSON, YAML, INI) in future versions.
    
    Returns:
        dict: Configuration dictionary with service enable flags and parameters
    """
    return HUD_CONFIG.copy()


def validate_config(config):
    """
    Validates the configuration dictionary for common issues.
    
    Checks for:
    - Wi-Fi locator enabled without dual adapters configured
    - Wi-Fi locator enabled without heading source (GPS or IMU)
    - Invalid interface names (basic validation)
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        tuple: (is_valid, list_of_warnings)
    """
    warnings = []
    
    # Check Wi-Fi locator requirements
    if config.get("enable_wifi_locator", False):
        left_if = config.get("wifi_left_interface", "")
        right_if = config.get("wifi_right_interface", "")
        
        if not left_if or not right_if:
            warnings.append(
                "Wi-Fi locator enabled but interfaces not configured. "
                "Set wifi_left_interface and wifi_right_interface."
            )
        
        if left_if == right_if:
            warnings.append(
                "Wi-Fi locator requires two different interfaces. "
                f"Both are set to '{left_if}'."
            )
        
        # Warn if using onboard wireless for direction finding
        if left_if in ["wlan0", "wlp1s0"] or left_if.startswith("wlp"):
            warnings.append(
                f"WARNING: Using onboard wireless interface '{left_if}' for left adapter. "
                "This is NOT recommended. Use a USB Wi-Fi adapter (wlan1, wlan2, or wlx*) instead."
            )
        
        if right_if in ["wlan0", "wlp1s0"] or right_if.startswith("wlp"):
            warnings.append(
                f"WARNING: Using onboard wireless interface '{right_if}' for right adapter. "
                "This is NOT recommended. Use a USB Wi-Fi adapter (wlan1, wlan2, or wlx*) instead."
            )
        
        if not config.get("enable_gps", False) and not config.get("enable_imu", False):
            warnings.append(
                "Wi-Fi locator requires heading data from GPS or IMU. "
                "Enable either enable_gps or enable_imu."
            )
        
        # Validate adapter separation
        adapter_sep = config.get("adapter_separation_m", 0.15)
        if adapter_sep < 0.05 or adapter_sep > 0.5:
            warnings.append(
                f"Adapter separation {adapter_sep}m is outside typical range (0.05m - 0.5m). "
                "Triangulation accuracy may be affected."
            )
    
    # Check Wi-Fi scanner requirements
    if config.get("enable_wifi_scanner", False):
        wifi_if = config.get("wifi_scan_interface", "")
        if not wifi_if:
            warnings.append(
                "Wi-Fi scanner enabled but wifi_scan_interface not configured."
            )
        
        # Warn if using onboard wireless
        if wifi_if in ["wlan0", "wlp1s0"] or wifi_if.startswith("wlp"):
            warnings.append(
                f"WARNING: Using onboard wireless interface '{wifi_if}' for scanning. "
                "This is NOT recommended. Use a USB Wi-Fi adapter (wlan1, wlan2, or wlx*) instead."
            )
    
    is_valid = len(warnings) == 0
    return is_valid, warnings
