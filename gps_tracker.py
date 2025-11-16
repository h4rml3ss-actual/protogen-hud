import gps
import threading
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def start_gps_tracker_service(shared_state, stop_event):
    """
    Starts a background thread that polls GPS data using gpsd and writes to SharedState.
    
    Args:
        shared_state: SharedState instance for thread-safe data storage
        stop_event: threading.Event to signal thread stop
    
    Returns:
        The started thread object
    """
    def gps_thread():
        retry_delay = 1  # Initial retry delay in seconds
        max_retry_delay = 60  # Maximum retry delay (exponential backoff cap)
        
        while not stop_event.is_set():
            try:
                logger.info("[GPS] Connecting to gpsd...")
                session = gps.gps(mode=gps.WATCH_ENABLE)
                logger.info("[GPS] Connected to gpsd successfully")
                retry_delay = 1  # Reset retry delay on successful connection
                
                while not stop_event.is_set():
                    try:
                        report = session.next()
                        
                        if report['class'] == 'TPV':
                            # Extract GPS data from report
                            lat = report.lat if hasattr(report, 'lat') else None
                            lon = report.lon if hasattr(report, 'lon') else None
                            spd = report.speed if hasattr(report, 'speed') else None
                            track = report.track if hasattr(report, 'track') else None
                            
                            # Check if IMU heading exists before writing GPS heading
                            imu_data = shared_state.get_imu_data()
                            if imu_data.get('heading') is not None:
                                # IMU heading takes priority, don't override it
                                track = None
                            
                            # Write GPS data to shared state
                            shared_state.set_gps_data(
                                latitude=lat,
                                longitude=lon,
                                speed=spd,
                                heading=track
                            )
                            
                    except KeyError:
                        pass  # Ignore key errors in the report
                    except StopIteration:
                        logger.warning("[GPS] GPS session ended, reconnecting...")
                        break  # Break inner loop to reconnect
                    except Exception as e:
                        logger.error(f"[GPS] Error reading GPS data: {e}")
                        time.sleep(1)
                        
            except Exception as e:
                logger.error(f"[GPS] Connection error: {e}")
                logger.info(f"[GPS] Retrying in {retry_delay} seconds...")
                
                # Wait with exponential backoff, but check stop_event periodically
                for _ in range(retry_delay):
                    if stop_event.is_set():
                        break
                    time.sleep(1)
                
                # Exponential backoff with cap
                retry_delay = min(retry_delay * 2, max_retry_delay)
        
        logger.info("[GPS] GPS tracker service stopped")
    
    thread = threading.Thread(target=gps_thread, daemon=True)
    thread.start()
    logger.info("[GPS] GPS tracker service started")
    return thread


