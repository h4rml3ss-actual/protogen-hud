import os
import signal
os.environ["QT_QPA_PLATFORM"] = "xcb"  # Force X11 platform for OpenCV
os.environ["OPENCV_OPENCL_RUNTIME"] = "true"  # Enable OpenCV hardware acceleration
import cv2
import numpy as np
import math
import psutil
from time import time
import subprocess
import sounddevice as sd
from threading import Thread, Event
import gps

# Parameters for audio visualizer
SAMPLERATE = 44100
FRAMES_PER_BUFFER = 1024
NUM_BARS = 60
RADIUS = 300
CENTER = (960, 540)  # Center updated for 1920x1080 resolution

# Initialize global variables
audio_data = np.zeros(FRAMES_PER_BUFFER, dtype=np.float32)
metrics_data = {}
wifi_signals = []
heading = 0
update_event = Event()
camera = None
stream = None
gps_heading = None  # Shared variable for GPS heading
latitude = "N/A"  # Shared variable for GPS latitude
longitude = "N/A"  # Shared variable for GPS longitude
speed = 0.0  # Shared variable for GPS speed

# Audio visualizer callback
def audio_callback(indata, frames, time, status):
    global audio_data
    if status:
        print(f"Audio Status: {status}")
    audio_data = np.frombuffer(indata, dtype=np.float32)

# GPS worker
def gps_worker():
    """Fetch GPS data in a separate thread."""
    global gps_heading
    gps_session = gps.gps(mode=gps.WATCH_ENABLE)
    while not update_event.is_set():
        try:
            report = gps_session.next()
            if report['class'] == 'TPV' and hasattr(report, 'track'):
                gps_heading = report.track  # Update shared heading
        except StopIteration:
            pass
        except Exception as e:
            print(f"GPS error: {e}")

# System metrics updater
def update_metrics():
    global metrics_data, wifi_signals, heading
    while not update_event.is_set():
        cpu_temp = "N/A"
        temps = psutil.sensors_temperatures().get("cpu_thermal")
        if temps and isinstance(temps, list) and len(temps) > 0:
            cpu_temp = temps[0].current

        metrics_data = {
            "CPU": psutil.cpu_percent(interval=None),
            "RAM": psutil.virtual_memory().percent,
            "Temp": cpu_temp,
            "Net_Sent": psutil.net_io_counters().bytes_sent / 1024,
            "Net_Recv": psutil.net_io_counters().bytes_recv / 1024,
        }

        result = subprocess.run(["iwlist", "wlan0", "scan"], capture_output=True, text=True)
        wifi_signals = [(line.split(":")[1].strip('"'), 50) for line in result.stdout.split("\n") if "ESSID" in line]

        if gps_heading is None:
            heading = (heading + 1) % 360

        update_event.wait(1)

# Unified HUD
def start_hud():
    global camera, stream
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    if not camera.isOpened():
        print("Error: Camera not found.")
        return

    stream = sd.InputStream(samplerate=SAMPLERATE, channels=1, callback=audio_callback)
    stream.start()

    update_event.clear()
    updater_thread = Thread(target=update_metrics, daemon=True)
    gps_thread = Thread(target=gps_worker, daemon=True)
    updater_thread.start()
    gps_thread.start()

    cv2.namedWindow("Unified HUD", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("Unified HUD", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    try:
        while True:
            ret, camera_frame = camera.read()
            if not ret:
                print("Error: Could not read camera frame.")
                break

            overlay = np.zeros_like(camera_frame)
            draw_audio_visualizer(overlay)
            draw_system_metrics(overlay)
            draw_wifi_signals(overlay)
            draw_compass(overlay)

            combined = cv2.addWeighted(camera_frame, 0.7, overlay, 0.3, 0)
            cv2.imshow("Unified HUD", combined)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cleanup()

def cleanup():
    global camera, stream
    print("Shutting down gracefully...")
    update_event.set()
    if camera:
        camera.release()
    if stream:
        stream.stop()
    cv2.destroyAllWindows()

def signal_handler(sig, frame):
    print("\nCtrl+C detected. Exiting...")
    cleanup()
    exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    start_hud()
