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

# Parameters for audio visualizer
SAMPLERATE = 44100
FRAMES_PER_BUFFER = 1024
NUM_BARS = 60
RADIUS = 200
CENTER = (640, 400)

# Initialize global variables
audio_data = np.zeros(FRAMES_PER_BUFFER, dtype=np.float32)
metrics_data = {}
wifi_signals = []
heading = 0
update_event = Event()
camera = None
stream = None

# Audio visualizer callback
def audio_callback(indata, frames, time, status):
    global audio_data
    if status:
        print(f"Audio Status: {status}")
    audio_data = np.frombuffer(indata, dtype=np.float32)

# System metrics updater
def update_metrics():
    global metrics_data, wifi_signals, heading
    while not update_event.is_set():
        # Update system metrics
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

        # Update Wi-Fi signals
        result = subprocess.run(["iwlist", "wlan0", "scan"], capture_output=True, text=True)
        wifi_signals = [(line.split(":")[1].strip('"'), 50) for line in result.stdout.split("\n") if "ESSID" in line]

        # Simulate compass heading
        heading = (heading + 1) % 360
        update_event.wait(1)  # Update every second

# Full feature set of draw functions
def draw_system_metrics(frame):
    y = 50
    spacing = 40
    x = 20  # Align to the left side
    cv2.putText(frame, f"CPU: {metrics_data.get('CPU', 0)}%", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
    y += spacing
    cv2.putText(frame, f"RAM: {metrics_data.get('RAM', 0)}%", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    y += spacing
    cv2.putText(frame, f"Temp: {metrics_data.get('Temp', 'N/A')} C", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 191, 255), 2)
    y += spacing
    cv2.putText(frame, f"Net Sent: {metrics_data.get('Net_Sent', 0):.2f} KB", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 165, 0), 2)
    y += spacing
    cv2.putText(frame, f"Net Recv: {metrics_data.get('Net_Recv', 0):.2f} KB", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

def draw_wifi_signals(frame):
    x = 900  # Align to the right side
    max_width = 300
    bar_height = 30
    start_y = 20
    for i, (ssid, signal) in enumerate(wifi_signals[:5]):
        bar_width = int((signal / 100) * max_width)
        x1 = x
        y1 = start_y + i * (bar_height + 10)
        x2 = x1 + bar_width
        y2 = y1 + bar_height
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), -1)
        cv2.putText(frame, ssid, (x1 - 200, y1 + bar_height - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

def draw_compass(frame):
    global heading
    center = (640, 650)  # Centered at the bottom of the screen
    radius = 100
    cv2.circle(frame, center, radius, (128, 0, 128), 3)
    angle = math.radians(-heading + 90)
    x = int(center[0] + radius * math.cos(angle))
    y = int(center[1] + radius * math.sin(angle))
    cv2.line(frame, center, (x, y), (255, 20, 147), 5)
    cv2.putText(frame, f"Heading: {heading}°", (center[0] - 100, center[1] + 140), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

def draw_audio_visualizer(frame):
    fft = np.abs(np.fft.rfft(audio_data))[:NUM_BARS]
    fft = fft / np.max(fft) if np.max(fft) != 0 else fft
    angle_step = 360 / NUM_BARS
    for i, amplitude in enumerate(fft):
        length = int(amplitude * 400)
        angle = math.radians(i * angle_step)
        x1 = int(CENTER[0] + RADIUS * np.cos(angle))
        y1 = int(CENTER[1] + RADIUS * np.sin(angle))
        x2 = int(CENTER[0] + (RADIUS + length) * np.cos(angle))
        y2 = int(CENTER[1] + (RADIUS + length) * np.sin(angle))
        cv2.line(frame, (x1, y1), (x2, y2), (255 - i * 4, 0, 255), 2)

# Unified HUD
def start_hud():
    global camera, stream
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 800)

    if not camera.isOpened():
        print("Error: Camera not found.")
        return

    stream = sd.InputStream(samplerate=SAMPLERATE, channels=1, callback=audio_callback)
    stream.start()

    # Start background thread for updates
    update_event.clear()
    updater_thread = Thread(target=update_metrics, daemon=True)
    updater_thread.start()

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
    """Release resources and clean up gracefully."""
    global camera, stream
    print("Shutting down gracefully...")
    update_event.set()  # Stop the updater thread
    if camera:
        camera.release()
    if stream:
        stream.stop()
    cv2.destroyAllWindows()

def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) for graceful shutdown."""
    print("\nCtrl+C detected. Exiting...")
    cleanup()
    exit(0)

if __name__ == "__main__":
    # Register the signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    start_hud()
