"""
SharedState - Thread-safe centralized data store for HUD variables.

This module provides a thread-safe storage mechanism for all HUD data including
GPS, IMU, system metrics, Wi-Fi scan results, Wi-Fi direction estimates, and audio buffers.
All read and write operations are protected by threading locks to prevent race conditions.
"""

import threading
from typing import Optional, List, Dict, Any
import numpy as np


class SharedState:
    """Thread-safe centralized storage for all HUD data."""
    
    def __init__(self):
        """Initialize SharedState with safe defaults and threading lock."""
        self._lock = threading.Lock()
        
        # GPS data
        self._gps_data = {
            "latitude": None,
            "longitude": None,
            "speed": None,
            "heading": None
        }
        
        # IMU data
        self._imu_data = {
            "heading": None,
            "pitch": None,
            "roll": None
        }
        
        # System metrics
        self._system_metrics = {
            "cpu_percent": 0.0,
            "ram_percent": 0.0,
            "temp_celsius": "N/A",
            "net_sent_kb": 0.0,
            "net_recv_kb": 0.0
        }
        
        # Wi-Fi scan results (list of network dicts)
        self._wifi_networks = []
        
        # Wi-Fi scan results per interface (dict keyed by interface name)
        self._wifi_networks_by_interface = {}
        
        # Wi-Fi direction estimates (dict keyed by SSID)
        self._wifi_directions = {}
        
        # Audio buffer
        self._audio_buffer = None
    
    # GPS data methods
    def set_gps_data(self, latitude: Optional[float] = None, 
                     longitude: Optional[float] = None,
                     speed: Optional[float] = None, 
                     heading: Optional[float] = None):
        """
        Thread-safe write of GPS data.
        
        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            speed: Speed in meters per second
            heading: Heading in degrees (0-360)
        """
        with self._lock:
            self._gps_data = {
                "latitude": latitude,
                "longitude": longitude,
                "speed": speed,
                "heading": heading
            }
    
    def get_gps_data(self) -> Dict[str, Optional[float]]:
        """
        Thread-safe read of GPS data.
        
        Returns:
            Dictionary containing latitude, longitude, speed, and heading
        """
        with self._lock:
            return self._gps_data.copy()
    
    # IMU data methods
    def set_imu_data(self, heading: Optional[float] = None,
                     pitch: Optional[float] = None,
                     roll: Optional[float] = None):
        """
        Thread-safe write of IMU data.
        
        Args:
            heading: Heading in degrees (0-360)
            pitch: Pitch in degrees
            roll: Roll in degrees
        """
        with self._lock:
            self._imu_data = {
                "heading": heading,
                "pitch": pitch,
                "roll": roll
            }
    
    def get_imu_data(self) -> Dict[str, Optional[float]]:
        """
        Thread-safe read of IMU data.
        
        Returns:
            Dictionary containing heading, pitch, and roll
        """
        with self._lock:
            return self._imu_data.copy()
    
    # System metrics methods
    def set_system_metrics(self, cpu_percent: float = 0.0,
                          ram_percent: float = 0.0,
                          temp_celsius: Any = "N/A",
                          net_sent_kb: float = 0.0,
                          net_recv_kb: float = 0.0):
        """
        Thread-safe write of system metrics.
        
        Args:
            cpu_percent: CPU usage percentage
            ram_percent: RAM usage percentage
            temp_celsius: CPU temperature in Celsius or "N/A"
            net_sent_kb: Network bytes sent in KB
            net_recv_kb: Network bytes received in KB
        """
        with self._lock:
            self._system_metrics = {
                "cpu_percent": cpu_percent,
                "ram_percent": ram_percent,
                "temp_celsius": temp_celsius,
                "net_sent_kb": net_sent_kb,
                "net_recv_kb": net_recv_kb
            }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Thread-safe read of system metrics.
        
        Returns:
            Dictionary containing CPU, RAM, temperature, and network stats
        """
        with self._lock:
            return self._system_metrics.copy()
    
    # Wi-Fi scan results methods
    def set_wifi_networks(self, networks: List[Dict[str, Any]], interface: Optional[str] = None):
        """
        Thread-safe write of Wi-Fi scan results.
        
        Args:
            networks: List of network dictionaries containing SSID, signal, channel, security,
                     device_type, frequency, distance_m, color, and signal_dbm
            interface: Optional interface name to store results per-interface
        """
        with self._lock:
            self._wifi_networks = networks.copy() if networks else []
            if interface:
                self._wifi_networks_by_interface[interface] = networks.copy() if networks else []
    
    def get_wifi_networks(self, interface: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Thread-safe read of Wi-Fi scan results.
        
        Args:
            interface: Optional interface name to get results for specific interface
        
        Returns:
            List of network dictionaries with enhanced RF device information
        """
        with self._lock:
            if interface:
                return self._wifi_networks_by_interface.get(interface, []).copy()
            return self._wifi_networks.copy()
    
    # Wi-Fi direction estimates methods
    def set_wifi_direction(self, ssid: str, direction_deg: float, confidence: float):
        """
        Thread-safe write of Wi-Fi direction estimate for a specific SSID.
        
        Args:
            ssid: Network SSID
            direction_deg: Estimated direction in degrees (0-360)
            confidence: Confidence level (0.0-1.0)
        """
        with self._lock:
            self._wifi_directions[ssid] = {
                "direction_deg": direction_deg,
                "confidence": confidence
            }
    
    def get_wifi_directions(self) -> Dict[str, Dict[str, float]]:
        """
        Thread-safe read of all Wi-Fi direction estimates.
        
        Returns:
            Dictionary keyed by SSID containing direction and confidence
        """
        with self._lock:
            return self._wifi_directions.copy()
    
    # Audio buffer methods
    def set_audio_buffer(self, buffer: Optional[np.ndarray]):
        """
        Thread-safe write of audio buffer.
        
        Args:
            buffer: Numpy array containing audio samples
        """
        with self._lock:
            self._audio_buffer = buffer.copy() if buffer is not None else None
    
    def get_audio_buffer(self) -> Optional[np.ndarray]:
        """
        Thread-safe read of audio buffer.
        
        Returns:
            Numpy array containing audio samples, or None
        """
        with self._lock:
            return self._audio_buffer.copy() if self._audio_buffer is not None else None
    
    # Complete snapshot method
    def get_snapshot(self) -> Dict[str, Any]:
        """
        Thread-safe read of all HUD data in a single lock acquisition.
        
        This method is more efficient than calling individual getters when
        multiple data types are needed, as it acquires the lock only once.
        
        Returns:
            Dictionary containing all HUD data:
                - gps: GPS data dict
                - imu: IMU data dict
                - system_metrics: System metrics dict
                - wifi_networks: List of Wi-Fi networks
                - wifi_directions: Dict of Wi-Fi direction estimates
                - audio_buffer: Audio buffer numpy array or None
        """
        with self._lock:
            return {
                "gps": self._gps_data.copy(),
                "imu": self._imu_data.copy(),
                "system_metrics": self._system_metrics.copy(),
                "wifi_networks": self._wifi_networks.copy(),
                "wifi_networks_by_interface": {k: v.copy() for k, v in self._wifi_networks_by_interface.items()},
                "wifi_directions": self._wifi_directions.copy(),
                "audio_buffer": self._audio_buffer.copy() if self._audio_buffer is not None else None
            }
