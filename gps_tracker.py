import gps
import threading
import time
import cv2
import math
from theme import NEON_BLUE, NEON_GREEN, NEON_PINK

# Shared state variables for GPS data
gps_heading = None  # Current heading from GPS
latitude = "N/A"    # Latitude from GPS
longitude = "N/A"   # Longitude from GPS
speed = 0.0         # Speed from GPS
stop_event = threading.Event()  # Event to signal thread stop

def start_gps_worker():
    """
    Starts a background thread that polls GPS data using gpsd.
    This function initializes a thread that continuously retrieves GPS data
    until the stop_event is set.
    """
    def gps_thread():
        global gps_heading, latitude, longitude, speed  # Access shared state variables
        session = gps.gps(mode=gps.WATCH_ENABLE)  # Create a GPS session in watch mode
        while not stop_event.is_set():  # Continue polling until the stop event is triggered
            try:
                report = session.next()  # Get the next GPS report
                if report['class'] == 'TPV':  # Check if the report contains time-position-velocity data
                    if hasattr(report, 'track'):  # If heading data is available
                        gps_heading = report.track  # Update the global gps_heading variable
                    if hasattr(report, 'lat'):  # If latitude data is available
                        latitude = report.lat  # Update the global latitude variable
                    if hasattr(report, 'lon'):  # If longitude data is available
                        longitude = report.lon  # Update the global longitude variable
                    if hasattr(report, 'speed'):  # If speed data is available
                        speed = report.speed  # Update the global speed variable
            except KeyError:
                pass  # Ignore key errors in the report
            except StopIteration:
                break  # Exit the loop if there are no more reports
            except Exception as e:
                print(f"[GPS] Error: {e}")  # Print any other exceptions that occur
            time.sleep(1)  # Wait for 1 second before polling again

    thread = threading.Thread(target=gps_thread, daemon=True)  # Create a daemon thread for GPS polling
    thread.start()  # Start the GPS thread
    return stop_event  # Return the stop event for external control

def draw_compass(frame, heading, center=(100, 600), radius=40):
    """
    Draws a compass with heading indicator.
    :param frame: The OpenCV frame to draw on
    :param heading: The current heading in degrees
    :param center: Tuple (x, y) for compass center
    :param radius: Radius of the compass circle
    """
    # Draw compass circle
    cv2.circle(frame, center, radius, NEON_BLUE, 2)  # Draw the outer circle of the compass

    # Direction markers and angles
    directions = [
        ("N", 270), ("NE", 315), ("E", 0), ("SE", 45),
        ("S", 90), ("SW", 135), ("W", 180), ("NW", 225)
    ]  # Define the cardinal directions and their corresponding angles
    for label, angle_deg in directions:  # Iterate through each direction
        angle_rad = math.radians(angle_deg)  # Convert angle from degrees to radians
        x = int(center[0] + (radius + 10) * math.cos(angle_rad))  # Calculate x position for the label
        y = int(center[1] + (radius + 10) * math.sin(angle_rad))  # Calculate y position for the label
        cv2.putText(frame, label, (x - 10, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, NEON_PINK, 1)  # Draw the label on the frame

    # Draw heading needle
    angle_rad = math.radians(-heading + 90)  # Offset so 0 degrees points up
    x2 = int(center[0] + radius * math.cos(angle_rad))  # Calculate x position for the needle tip
    y2 = int(center[1] - radius * math.sin(angle_rad))  # Calculate y position for the needle tip
    cv2.line(frame, center, (x2, y2), NEON_GREEN, 2)  # Draw the needle pointing to the current heading
