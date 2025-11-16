# service_threads.py
# Starts and manages worker threads for HUD services
# This module now delegates to ServiceManager for all service lifecycle management

from service_manager import ServiceManager
from shared_state import SharedState

# Global reference to ServiceManager instance
_service_manager = None
_shared_state = None


def start_all_services(shared_state=None, config=None):
    """
    Starts all background services needed for the HUD.
    
    This function now delegates to ServiceManager for all service lifecycle management.
    
    Args:
        shared_state: SharedState instance for thread-safe data storage (optional)
        config: Configuration dictionary specifying which services to enable (optional)
                If not provided, uses default configuration.
    """
    global _service_manager, _shared_state
    
    # Create SharedState if not provided
    if shared_state is None:
        _shared_state = SharedState()
    else:
        _shared_state = shared_state
    
    # Use default config if not provided
    if config is None:
        config = {
            "enable_system_metrics": True,
            "enable_gps": True,
            "enable_imu": False,
            "enable_wifi_scanner": True,
            "enable_wifi_locator": False,
            "enable_audio": True,
            "wifi_interface": "wlan0",
            "wifi_left_interface": "wlan0",
            "wifi_right_interface": "wlan1"
        }
    
    # Initialize ServiceManager with shared_state and config
    _service_manager = ServiceManager(_shared_state, config)
    
    # Delegate to ServiceManager to start all services
    _service_manager.start_all()


def stop_all_services():
    """
    Signals all services to stop gracefully.
    
    This function now delegates to ServiceManager for graceful shutdown.
    """
    global _service_manager
    
    # Delegate to ServiceManager to stop all services
    if _service_manager is not None:
        _service_manager.stop_all()


def get_shared_state():
    """
    Returns the SharedState instance used by the services.
    
    Returns:
        SharedState instance or None if services haven't been started
    """
    return _shared_state
