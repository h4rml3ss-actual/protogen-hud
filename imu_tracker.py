"""
IMUTrackerService - Background service for reading BNO085 IMU sensor data.

This module provides a service thread that continuously reads heading, pitch, and roll
data from the BNO085 IMU sensor via I2C, writing the data to the SharedState manager.
IMU heading takes priority over GPS heading for compass display.
"""

import threading
import time
import logging
import math
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def quaternion_to_euler(qw: float, qx: float, qy: float, qz: float) -> tuple:
    """
    Convert quaternion to Euler angles (heading, pitch, roll).
    
    Args:
        qw: Quaternion w component
        qx: Quaternion x component
        qy: Quaternion y component
        qz: Quaternion z component
    
    Returns:
        Tuple of (heading, pitch, roll) in degrees
        - heading: 0-360 degrees (0 = North, 90 = East, 180 = South, 270 = West)
        - pitch: -180 to 180 degrees (nose up/down)
        - roll: -180 to 180 degrees (wing up/down)
    """
    # Roll (x-axis rotation)
    sinr_cosp = 2 * (qw * qx + qy * qz)
    cosr_cosp = 1 - 2 * (qx * qx + qy * qy)
    roll = math.atan2(sinr_cosp, cosr_cosp)
    
    # Pitch (y-axis rotation)
    sinp = 2 * (qw * qy - qz * qx)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)  # Use 90 degrees if out of range
    else:
        pitch = math.asin(sinp)
    
    # Yaw/Heading (z-axis rotation)
    siny_cosp = 2 * (qw * qz + qx * qy)
    cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    
    # Convert to degrees
    roll_deg = math.degrees(roll)
    pitch_deg = math.degrees(pitch)
    heading_deg = math.degrees(yaw)
    
    # Normalize heading to 0-360 range
    heading_deg = (heading_deg + 360) % 360
    
    return heading_deg, pitch_deg, roll_deg


def initialize_bno085():
    """
    Initialize I2C connection to BNO085 sensor.
    
    Tries common I2C addresses (0x4A, 0x4B) and configures the sensor
    for rotation vector output.
    
    Returns:
        BNO08X sensor object if successful, None if initialization fails
    """
    try:
        import board
        import busio
        from adafruit_bno08x import BNO08X_I2C
        from adafruit_bno08x.i2c import BNO_REPORT_ROTATION_VECTOR
    except ImportError as e:
        logger.error(f"[IMU] Failed to import required libraries: {e}")
        logger.error("[IMU] Install with: pip install adafruit-circuitpython-bno08x")
        return None
    
    # Try common I2C addresses
    addresses = [0x4A, 0x4B]
    
    for addr in addresses:
        try:
            logger.info(f"[IMU] Attempting to connect to BNO085 at address 0x{addr:02X}...")
            i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
            sensor = BNO08X_I2C(i2c, address=addr)
            
            # Configure sensor for rotation vector output
            sensor.enable_feature(BNO_REPORT_ROTATION_VECTOR)
            
            logger.info(f"[IMU] Successfully connected to BNO085 at address 0x{addr:02X}")
            return sensor
            
        except Exception as e:
            logger.debug(f"[IMU] Failed to connect at address 0x{addr:02X}: {e}")
            continue
    
    logger.error("[IMU] Failed to initialize BNO085 sensor at any known address")
    return None


def _imu_tracking_loop(shared_state, stop_event):
    """
    Main loop for IMU tracking service thread.
    
    Continuously reads sensor data from BNO085 and writes to SharedState until
    stop_event is set. Polls at approximately 50Hz (20ms intervals).
    
    Args:
        shared_state: SharedState instance to write IMU data to
        stop_event: threading.Event to signal thread shutdown
    """
    logger.info("[IMU] IMU tracking service started")
    
    # Initialize sensor
    sensor = initialize_bno085()
    if sensor is None:
        logger.error("[IMU] Sensor initialization failed, service exiting")
        return
    
    try:
        # Import here after successful initialization
        from adafruit_bno08x.i2c import BNO_REPORT_ROTATION_VECTOR
        
        poll_interval = 0.02  # 20ms = ~50Hz
        
        while not stop_event.is_set():
            try:
                # Read quaternion from sensor
                quat_i, quat_j, quat_k, quat_real = sensor.quaternion
                
                if quat_real is not None:
                    # Convert quaternion to Euler angles
                    heading, pitch, roll = quaternion_to_euler(
                        quat_real, quat_i, quat_j, quat_k
                    )
                    
                    # Write to SharedState
                    shared_state.set_imu_data(
                        heading=heading,
                        pitch=pitch,
                        roll=roll
                    )
                else:
                    logger.debug("[IMU] Received None quaternion from sensor")
                
            except Exception as e:
                logger.error(f"[IMU] Error reading sensor data: {e}", exc_info=True)
            
            # Sleep for poll interval (~50Hz)
            time.sleep(poll_interval)
    
    except Exception as e:
        logger.error(f"[IMU] Fatal error in IMU tracking service: {e}", exc_info=True)
    
    finally:
        logger.info("[IMU] IMU tracking service stopped")


def start_imu_tracker_service(shared_state, stop_event):
    """
    Start the IMU tracking service as a daemon thread.
    
    Creates and starts a background thread that continuously reads heading, pitch,
    and roll data from the BNO085 IMU sensor and writes it to the SharedState manager.
    IMU heading takes priority over GPS heading.
    
    Args:
        shared_state: SharedState instance to write IMU data to
        stop_event: threading.Event to signal thread shutdown
    
    Returns:
        threading.Thread: The started daemon thread
    """
    thread = threading.Thread(
        target=_imu_tracking_loop,
        args=(shared_state, stop_event),
        daemon=True,
        name="IMUTrackerService"
    )
    thread.start()
    logger.info("[IMU] IMU tracker service thread started")
    return thread
