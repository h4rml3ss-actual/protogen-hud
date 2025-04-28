import os
import signal
os.environ["QT_QPA_PLATFORM"] = "xcb"  # Force X11 platform for OpenCV
os.environ["OPENCV_OPENCL_RUNTIME"] = "true"  # Enable OpenCV hardware acceleration
import cv2
import numpy as np
import math
import psutil
from time import time, sleep
import subprocess
import sounddevice as sd
from threading import Thread, Event
import gps

# Parameters for audio visualizer
SAMPLERATE = 44100
FRAMES_PER_BUFFER = 1024
NUM_BARS = 60
RADIUS = 300
CENTER = (640, 360)  # Center updated for 1280x720 resolution

# Initialize global variables
audio_data = np.zeros(FRAMES_PER_BUFFER, dtype=np.float32)
metrics_data = {}
wifi_signals = []
heading = 0
update_event = Event()
frame_update_event = Event()
camera_stream = None
stream = None
gps_heading = None  # Shared variable for GPS heading
latitude = "N/A"  # Shared variable for GPS latitude
longitude = "N/A"  # Shared variable for GPS longitude
speed = 0.0  # Shared variable for GPS speed

visualizer_buffer = None
VISUALIZER_UPDATE_INTERVAL = 0.2  # Update every 0.2 seconds

class CameraStream:
    def __init__(self, src=0):
        self.stream = cv2.VideoCapture(src)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.grabbed, self.frame = self.stream.read()
        self.stopped = False
        self.thread = Thread(target=self.update, args=(), daemon=True)
        self.thread.start()
        self.thread_priority()  # Ensure thread priority is increased

    def update(self):
        while not self.stopped:
            if not self.grabbed:
                self.stop()
            else:
                self.grabbed, self.frame = self.stream.read()

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.stream.release()

    def thread_priority(self):
        """Attempt to increase thread priority."""
        try:
            os.nice(-10)  # Lowering nice value increases priority
        except PermissionError:
            print("[WARN] Unable to set high priority for camera thread. Consider running with elevated permissions.")

# Audio visualizer callback
def audio_callback(indata, frames, time, status):
    global audio_data
    if status:
        print(f"Audio Status: {status}")
    audio_data = np.frombuffer(indata, dtype=np.float32)

# Audio visualizer drawing function
def draw_audio_visualizer(frame):
    global visualizer_buffer
    current_time = time()
    if current_time - draw_audio_visualizer.last_update >= VISUALIZER_UPDATE_INTERVAL:
        fft = np.abs(np.fft.rfft(audio_data))[:NUM_BARS]
        fft = fft / np.max(fft) if np.max(fft) != 0 else fft
        angle_step = 360 / NUM_BARS
        visualizer_buffer = np.zeros_like(frame)
        for i, amplitude in enumerate(fft):
            length = int(amplitude * 400)
            angle = math.radians(i * angle_step)
            x1 = int(CENTER[0] + RADIUS * np.cos(angle))
            y1 = int(CENTER[1] + RADIUS * np.sin(angle))
            x2 = int(CENTER[0] + (RADIUS + length) * np.cos(angle))
            y2 = int(CENTER[1] + (RADIUS + length) * np.sin(angle))
            cv2.line(visualizer_buffer, (x1, y1), (x2, y2), (255 - i * 4, 0, 255), 2)
        draw_audio_visualizer.last_update = current_time

    if visualizer_buffer is not None:
        frame[:] = cv2.addWeighted(frame, 0.8, visualizer_buffer, 0.2, 0)

# Initialize the timestamp for visualizer updates
draw_audio_visualizer.last_update = 0

# GPS worker
def gps_worker():
    """Fetch GPS data in a separate thread."""
    global gps_heading, latitude, longitude, speed
    gps_session = gps.gps(mode=gps.WATCH_ENABLE)
    while not update_event.is_set():
        try:
            report = gps_session.next()
            if report['class'] == 'TPV':
                if hasattr(report, 'track'):
                    gps_heading = report.track
                if hasattr(report, 'lat'):
                    latitude = report.lat
                if hasattr(report, 'lon'):
                    longitude = report.lon
                if hasattr(report, 'speed'):
                    speed = report.speed
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
        wifi_signals = []
        for block in result.stdout.split("Cell"):
            if "ESSID" in block:
                ssid = "Unknown"
                signal = "Unknown"
                channel = "Unknown"
                security = "Unknown"

                for line in block.split("\n"):
                    if "ESSID:" in line:
                        ssid = line.split("ESSID:")[1].strip().strip('"')
                    if "Signal level=" in line:
                        signal = line.split("Signal level=")[1].strip()
                    if "Channel:" in line:
                        channel = line.split("Channel:")[1].strip()
                    if "Encryption key:" in line:
                        security = "Enabled" if "on" in line else "Open"

                wifi_signals.append((ssid, signal, channel, security))

        if gps_heading is None:
            heading = (heading + 1) % 360

        sleep(1)

# Draw system metrics
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

# Draw Wi-Fi signals
def draw_wifi_signals(frame):
    x = 900  # Adjusted position for 1280x720 resolution
    y = 50
    spacing = 40

    for ssid, signal, channel, security in wifi_signals[:5]:
        cv2.putText(frame, f"SSID: {ssid}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
        y += spacing
        cv2.putText(frame, f"Signal: {signal}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        y += spacing
        cv2.putText(frame, f"Channel: {channel}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 191, 255), 2)
        y += spacing
        cv2.putText(frame, f"Security: {security}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        y += spacing * 2

# Draw compass
def draw_compass(frame):
    global heading, gps_heading, latitude, longitude, speed

    if gps_heading is not None:
        heading = gps_heading

    base_x = 20
    base_y = 250
    spacing = 20

    center = (base_x + 100, base_y + 100)
    radius = 100
    cv2.circle(frame, center, radius, (128, 0, 128), 3)
    angle = math.radians(-heading + 90)
    x = int(center[0] + radius * math.cos(angle))
    y = int(center[1] + radius * math.sin(angle))
    cv2.line(frame, center, (x, y), (255, 20, 147), 5)

    cv2.putText(frame, f"Heading: {heading:.1f}°", (base_x, base_y + 240), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)

    cv2.putText(frame, f"Lat: {latitude}", (base_x, base_y + 260), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(frame, f"Lon: {longitude}", (base_x, base_y + 280), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(frame, f"Speed: {speed:.2f} m/s", (base_x, base_y + 300), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

# Unified HUD
def start_hud():
    global camera_stream, stream
    camera_stream = CameraStream(0)

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
            camera_frame = camera_stream.read()

            overlay = np.zeros_like(camera_frame)
            draw_audio_visualizer(overlay)
            draw_system_metrics(overlay)
            draw_wifi_signals(overlay)
            draw_compass(overlay)

            combined = cv2.addWeighted(camera_frame, 0.7, overlay, 0.5, 0)  # Adjusted alpha values for better brightness
            cv2.imshow("Unified HUD", combined)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cleanup()

def cleanup():
    global camera_stream, stream
    print("Shutting down gracefully...")
    update_event.set()
    if camera_stream:
        camera_stream.stop()
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
