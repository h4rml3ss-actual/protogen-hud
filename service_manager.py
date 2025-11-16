"""
ServiceManager - Coordinates lifecycle of all HUD service threads.

This module provides centralized management for starting and stopping all background
service threads. It handles graceful shutdown with timeout logic and provides logging
for service lifecycle events.
"""

import threading
import logging
import time
from typing import Dict, List, Tuple, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages lifecycle of all HUD service threads."""
    
    def __init__(self, shared_state, config: Dict[str, Any]):
        """
        Initialize ServiceManager with shared state and configuration.
        
        Args:
            shared_state: SharedState instance for thread-safe data storage
            config: Configuration dictionary specifying which services to enable
                    and their parameters. Use config.get_config() to obtain the
                    default configuration. See config.py for detailed documentation
                    of all configuration options.
        """
        self.shared_state = shared_state
        self.config = config
        self.services: List[Tuple[str, threading.Event, threading.Thread]] = []
        logger.info("ServiceManager initialized")
    
    def _validate_interface(self, interface: str) -> bool:
        """
        Validate that a network interface exists on the system.
        
        Args:
            interface: Interface name to validate (e.g., "wlan1")
            
        Returns:
            True if interface exists, False otherwise
        """
        import subprocess
        try:
            result = subprocess.run(
                ["ip", "link", "show", interface],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"Interface validation failed for '{interface}': {e}")
            return False
    
    def start_all(self):
        """
        Start all enabled services based on configuration.
        
        Creates daemon threads for each enabled service and tracks their
        stop events for graceful shutdown.
        """
        logger.info("Starting all enabled services...")
        
        # Import service modules
        try:
            from system_metrics import start_system_metrics_service
            from gps_tracker import start_gps_tracker_service
            from imu_tracker import start_imu_tracker_service
            from wifi_scanner import start_wifi_scanner_service
            from wifi_locator import start_wifi_locator_service
            from audio_service import start_audio_service
        except ImportError as e:
            logger.error(f"Failed to import service modules: {e}")
            raise
        
        # System Metrics Service
        if self.config.get("enable_system_metrics", True):
            stop_event = threading.Event()
            start_system_metrics_service(self.shared_state, stop_event)
            self.services.append(("SystemMetrics", stop_event, None))
            logger.info("Service 'SystemMetrics' started")
        
        # GPS Tracker Service
        if self.config.get("enable_gps", False):
            stop_event = threading.Event()
            start_gps_tracker_service(self.shared_state, stop_event)
            self.services.append(("GPSTracker", stop_event, None))
            logger.info("Service 'GPSTracker' started")
        else:
            logger.info("Service 'GPSTracker' disabled in configuration")
        
        # IMU Tracker Service
        if self.config.get("enable_imu", False):
            stop_event = threading.Event()
            start_imu_tracker_service(self.shared_state, stop_event)
            self.services.append(("IMUTracker", stop_event, None))
            logger.info("Service 'IMUTracker' started")
        else:
            logger.info("Service 'IMUTracker' disabled in configuration")
        
        # Wi-Fi Scanner Service
        if self.config.get("enable_wifi_scanner", False):
            stop_event = threading.Event()
            interface = self.config.get("wifi_scan_interface", "wlan1")
            
            # Validate interface exists
            if not self._validate_interface(interface):
                logger.warning(f"Wi-Fi interface '{interface}' not found. Service may fail to start.")
            
            # Warn if using onboard wireless
            if interface in ["wlan0", "wlp1s0"] or interface.startswith("wlp"):
                logger.warning(
                    f"Using onboard wireless interface '{interface}' for scanning. "
                    "Consider using a USB Wi-Fi adapter instead."
                )
            
            start_wifi_scanner_service(self.shared_state, stop_event, interface)
            self.services.append(("WiFiScanner", stop_event, None))
            logger.info(f"Service 'WiFiScanner' started on interface {interface}")
        else:
            logger.info("Service 'WiFiScanner' disabled in configuration")
        
        # Wi-Fi Locator Service
        if self.config.get("enable_wifi_locator", False):
            stop_event = threading.Event()
            left_interface = self.config.get("wifi_left_interface", "wlan1")
            right_interface = self.config.get("wifi_right_interface", "wlan2")
            adapter_separation_m = self.config.get("adapter_separation_m", 0.15)
            
            # Validate interfaces exist
            if not self._validate_interface(left_interface):
                logger.warning(f"Left Wi-Fi interface '{left_interface}' not found. Service may fail to start.")
            if not self._validate_interface(right_interface):
                logger.warning(f"Right Wi-Fi interface '{right_interface}' not found. Service may fail to start.")
            
            # Warn if using onboard wireless
            if left_interface in ["wlan0", "wlp1s0"] or left_interface.startswith("wlp"):
                logger.warning(
                    f"Using onboard wireless interface '{left_interface}' for left adapter. "
                    "Consider using a USB Wi-Fi adapter instead."
                )
            if right_interface in ["wlan0", "wlp1s0"] or right_interface.startswith("wlp"):
                logger.warning(
                    f"Using onboard wireless interface '{right_interface}' for right adapter. "
                    "Consider using a USB Wi-Fi adapter instead."
                )
            
            start_wifi_locator_service(
                self.shared_state, stop_event, 
                left_interface, right_interface, 
                adapter_separation_m
            )
            self.services.append(("WiFiLocator", stop_event, None))
            logger.info(
                f"Service 'WiFiLocator' started "
                f"(left: {left_interface}, right: {right_interface}, separation: {adapter_separation_m}m)"
            )
        else:
            logger.info("Service 'WiFiLocator' disabled in configuration")
        
        # Audio Service
        if self.config.get("enable_audio", False):
            stop_event = threading.Event()
            start_audio_service(self.shared_state, stop_event)
            self.services.append(("Audio", stop_event, None))
            logger.info("Service 'Audio' started")
        else:
            logger.info("Service 'Audio' disabled in configuration")
        
        logger.info(f"Started {len(self.services)} service(s)")

    def stop_all(self):
        """
        Signal all services to stop and wait for graceful shutdown.
        
        Sets stop events for all running services and waits up to 5 seconds
        for each thread to terminate gracefully. Logs warnings for threads
        that don't stop within the timeout period.
        """
        if not self.services:
            logger.info("No services to stop")
            return
        
        logger.info(f"Stopping {len(self.services)} service(s)...")
        
        # Signal all services to stop
        for service_name, stop_event, thread in self.services:
            logger.info(f"Signaling service '{service_name}' to stop")
            stop_event.set()
        
        # Wait for graceful shutdown with timeout
        timeout = 5.0  # seconds
        for service_name, stop_event, thread in self.services:
            if thread is not None:
                thread.join(timeout=timeout)
                if thread.is_alive():
                    logger.warning(
                        f"Service '{service_name}' did not stop within {timeout}s timeout"
                    )
                else:
                    logger.info(f"Service '{service_name}' stopped successfully")
            else:
                # Thread reference not stored, just wait a moment
                logger.info(f"Service '{service_name}' stop signal sent")
        
        # Clear the services list
        self.services.clear()
        logger.info("All services stopped")
