"""
SystemMetricsService - Background service for collecting system performance metrics.

This module provides a service thread that continuously collects CPU usage, RAM usage,
CPU temperature, and network statistics, writing them to the SharedState manager.
"""

import threading
import time
import logging
import psutil
from typing import Union


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def read_cpu_temp() -> Union[float, str]:
    """
    Read CPU temperature using platform-agnostic methods with fallback.
    
    Tries multiple methods in order:
    1. Linux thermal zone file (/sys/class/thermal/thermal_zone0/temp)
    2. psutil.sensors_temperatures() if available
    3. Returns "N/A" if all methods fail
    
    Returns:
        CPU temperature in degrees Celsius, or "N/A" if unavailable
    """
    # Try Linux thermal zone file
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            millideg = int(f.read().strip())
            return millideg / 1000.0  # Convert millidegrees to Celsius
    except (FileNotFoundError, PermissionError, ValueError):
        pass
    
    # Try psutil sensors_temperatures (if available on platform)
    try:
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if temps:
                # Try to find CPU temperature from common sensor names
                for name in ["coretemp", "cpu_thermal", "cpu-thermal"]:
                    if name in temps and temps[name]:
                        return temps[name][0].current
                # If no known sensor name, use first available
                first_sensor = next(iter(temps.values()))
                if first_sensor:
                    return first_sensor[0].current
    except Exception:
        pass
    
    # All methods failed
    return "N/A"


def collect_system_metrics() -> dict:
    """
    Collect current system metrics including CPU, RAM, temperature, and network stats.
    
    Returns:
        Dictionary containing:
            - cpu_percent: CPU usage percentage
            - ram_percent: RAM usage percentage
            - temp_celsius: CPU temperature in Celsius or "N/A"
            - net_sent_kb: Network bytes sent in KB
            - net_recv_kb: Network bytes received in KB
    """
    metrics = {}
    
    # Get CPU utilization as a percentage
    metrics["cpu_percent"] = psutil.cpu_percent(interval=None)
    
    # Get RAM usage as a percentage
    metrics["ram_percent"] = psutil.virtual_memory().percent
    
    # Get CPU temperature
    metrics["temp_celsius"] = read_cpu_temp()
    
    # Get network I/O statistics
    net_io = psutil.net_io_counters()
    metrics["net_sent_kb"] = net_io.bytes_sent / 1024
    metrics["net_recv_kb"] = net_io.bytes_recv / 1024
    
    return metrics


def _metrics_collection_loop(shared_state, stop_event):
    """
    Main loop for metrics collection service thread.
    
    Continuously collects system metrics and writes to SharedState until
    stop_event is set.
    
    Args:
        shared_state: SharedState instance to write metrics to
        stop_event: threading.Event to signal thread shutdown
    """
    logger.info("System metrics collection service started")
    
    try:
        while not stop_event.is_set():
            try:
                # Collect current system metrics
                metrics = collect_system_metrics()
                
                # Write to SharedState
                shared_state.set_system_metrics(
                    cpu_percent=metrics["cpu_percent"],
                    ram_percent=metrics["ram_percent"],
                    temp_celsius=metrics["temp_celsius"],
                    net_sent_kb=metrics["net_sent_kb"],
                    net_recv_kb=metrics["net_recv_kb"]
                )
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}", exc_info=True)
            
            # Sleep for 1 second between updates
            time.sleep(1.0)
    
    except Exception as e:
        logger.error(f"Fatal error in system metrics service: {e}", exc_info=True)
    
    finally:
        logger.info("System metrics collection service stopped")


def start_system_metrics_service(shared_state, stop_event):
    """
    Start the system metrics collection service as a daemon thread.
    
    Creates and starts a background thread that continuously collects system
    performance metrics (CPU, RAM, temperature, network) and writes them to
    the SharedState manager.
    
    Args:
        shared_state: SharedState instance to write metrics to
        stop_event: threading.Event to signal thread shutdown
    
    Returns:
        threading.Thread: The started daemon thread
    """
    thread = threading.Thread(
        target=_metrics_collection_loop,
        args=(shared_state, stop_event),
        daemon=True,
        name="SystemMetricsService"
    )
    thread.start()
    logger.info("System metrics service thread started")
    return thread
