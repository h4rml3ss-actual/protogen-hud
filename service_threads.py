# service_threads.py
# Starts and manages worker threads for HUD services

from audio_visualizer import start_audio_stream
from gps_tracker import start_gps_worker

# Global reference to stop signals
stop_handles = {}

def start_all_services():
    """
    Starts all background services needed for the HUD.
    """
    # Start the audio stream service for the HUD
    start_audio_stream()
    
    # Start the GPS worker service and store its stop handle in the dictionary
    stop_handles["gps"] = start_gps_worker()
    # Add future services and their stop handles to this dictionary

def stop_all_services():
    """
    Signals all services to stop gracefully.
    """
    # Check if the GPS service is running and signal it to stop
    if "gps" in stop_handles:
        stop_handles["gps"].set()
    # Extend this as needed for additional stoppable services
