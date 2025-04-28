import os
import signal
os.environ["QT_QPA_PLATFORM"] = "xcb"  # Force X11 platform for OpenCV
os.environ["OPENCV_OPENCL_RUNTIME"] = "true"  # Enable OpenCV hardware acceleration

import cv2
import traceback
import numpy as np
import sounddevice as sd

# Select audio I/O devices by environment or name
input_name  = os.getenv("AUDIO_INPUT_DEVICE", "USB Audio Device")
output_name = os.getenv("AUDIO_OUTPUT_DEVICE", "Audio Adapter")
input_dev = None
output_dev = None
for idx, dev in enumerate(sd.query_devices()):
    name = dev['name']
    if input_dev is None and input_name in name and dev['max_input_channels'] > 0:
        input_dev = idx
    if output_dev is None and output_name in name and dev['max_output_channels'] > 0:
        output_dev = idx
# Fallback to system defaults
if input_dev is None or input_dev < 0:
    input_dev = sd.default.device[0]
if output_dev is None or output_dev < 0:
    output_dev = sd.default.device[1]
import math
import psutil
from time import time, sleep
import subprocess
from threading import Thread, Event
import gps
import sys
# Suppress ALSA lib errors to prevent flooding stderr with PortAudio messages
from ctypes import cdll, CFUNCTYPE, c_char_p, c_int
# Define the error handler signature: (filename, line, function, err, fmt)
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
def py_error_handler(filename, line, function, err, fmt):
    # no-op error handler
    pass
try:
    libasound = cdll.LoadLibrary('libasound.so.2')
    libasound.snd_lib_error_set_handler(ERROR_HANDLER_FUNC(py_error_handler))
except Exception:
    pass  # If ALSA lib isn't found or call fails, ignore
# import tkinter as tk
import tkinter as tk
import threading

# Thread-safe overlay buffers and locks
visualizer_lock = threading.Lock()
metrics_lock    = threading.Lock()
wifi_lock       = threading.Lock()
compass_lock    = threading.Lock()

latest_visualizer = None
latest_metrics    = None
latest_wifi       = None
latest_compass    = None

# Event to signal overlay workers to stop
stop_event = threading.Event()

# Detect display resolution
root = tk.Tk()
SCREEN_WIDTH = root.winfo_screenwidth()
SCREEN_HEIGHT = root.winfo_screenheight()
root.withdraw()

# Parameters for audio visualizer and dynamic layout
SAMPLERATE = 44100
FRAMES_PER_BUFFER = 1024
NUM_BARS = 60
# Dynamically compute radius and center based on screen resolution
RADIUS = min(SCREEN_WIDTH, SCREEN_HEIGHT) // 6
CENTER = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

# Initialize global variables
audio_data = np.zeros(FRAMES_PER_BUFFER, dtype=np.float32)
# Global FPS value for metrics display
current_fps = 0.0
metrics_data = {}
wifi_signals = []
heading = 0
update_event = Event()
frame_update_event = Event()
camera_stream = None
stream = None
output_stream = None  # For audio playback
gps_heading = None  # Shared variable for GPS heading
latitude = "N/A"     # Shared variable for GPS latitude
longitude = "N/A"    # Shared variable for GPS longitude
speed = 0.0          # Shared variable for GPS speed

# This buffer is no longer used for alpha blending; you can still reuse it for partial drawings if you wish.
# But in this version, we primarily draw directly onto the camera frame to eliminate transparency overhead.
overlay_buffer = None

VISUALIZER_UPDATE_INTERVAL = 0.2  # Update every 0.2 seconds

###############################################################################
# Class: CameraStream
###############################################################################
class CameraStream:
    def __init__(self, src=0):
        # Try using the V4L2 backend first for lower latency
        try:
            self.stream = cv2.VideoCapture(src, cv2.CAP_V4L2)
        except Exception:
            self.stream = cv2.VideoCapture(src)
        # Optional: use GStreamer if V4L2 isn't low‑latency enough
        # gst_str = (
        #     f"v4l2src device=/dev/video{src} ! "
        #     f"video/x-raw,width={SCREEN_WIDTH},height={SCREEN_HEIGHT},framerate=30/1 ! "
        #     "videoconvert ! appsink drop=true"
        # )
        # self.stream = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)
        # Match camera capture to screen resolution
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, SCREEN_WIDTH)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, SCREEN_HEIGHT)
        # Reduce buffering to lowest possible to minimize lag
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # Request a higher FPS for smoother, lower‑latency capture
        self.stream.set(cv2.CAP_PROP_FPS, 30)
        self.grabbed, self.frame = self.stream.read()
        self.stopped = False
        self.thread = Thread(target=self.update, args=(), daemon=True)
        self.thread.start()
        self.thread_priority()  # Attempt to ensure higher thread priority

    def update(self):
        """
        Continuously grabs and retrieves the latest frame, discarding older ones.
        Ensures self.frame always holds the most recent image.
        """
        while not self.stopped:
            # Grab the next frame (non-blocking)
            if not self.stream.grab():
                # If grab fails, stop the stream
                self.stop()
                break
            # Retrieve only the most recently grabbed frame
            self.grabbed, self.frame = self.stream.retrieve()

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.stream.release()

    def thread_priority(self):
        """Attempt to increase thread priority."""
        try:
            os.nice(-10)
        except PermissionError:
            pass  # Ignore if unable to change priority


###############################################################################
# Audio Visualizer Drawing
###############################################################################
def draw_audio_visualizer(frame):
    """
    Draws the FFT-based visualizer bars directly onto the camera frame.
    No alpha blending is performed, so the bars will appear fully opaque.
    """
    current_time = time()
    if current_time - draw_audio_visualizer.last_update >= VISUALIZER_UPDATE_INTERVAL:
        # Compute FFT
        fft = np.abs(np.fft.rfft(audio_data))[:NUM_BARS]
        max_val = np.max(fft)
        if max_val != 0:
            fft /= max_val

        angle_step = 360 / NUM_BARS

        # Draw the bars directly on the camera frame
        for i, amplitude in enumerate(fft):
            length = int(amplitude * (RADIUS / 2))
            angle = math.radians(i * angle_step)
            x1 = int(CENTER[0] + RADIUS * np.cos(angle))
            y1 = int(CENTER[1] + RADIUS * np.sin(angle))
            x2 = int(CENTER[0] + (RADIUS + length) * np.cos(angle))
            y2 = int(CENTER[1] + (RADIUS + length) * np.sin(angle))
            cv2.line(frame, (x1, y1), (x2, y2), (255 - i * 4, 0, 255), 2)

        draw_audio_visualizer.last_update = current_time

# Initialize the timestamp for visualizer updates
draw_audio_visualizer.last_update = 0

###############################################################################
# GPS Worker
###############################################################################
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

###############################################################################
# System Metrics Updater
###############################################################################
def update_metrics():
    global metrics_data, wifi_signals, heading
    while not update_event.is_set():
        # Get CPU temp
        cpu_temp = "N/A"
        temps = psutil.sensors_temperatures().get("cpu_thermal")
        if temps and isinstance(temps, list) and len(temps) > 0:
            cpu_temp = temps[0].current

        # Store metrics
        metrics_data = {
            "CPU": psutil.cpu_percent(interval=None),
            "RAM": psutil.virtual_memory().percent,
            "Temp": cpu_temp,
            "Net_Sent": psutil.net_io_counters().bytes_sent / 1024,
            "Net_Recv": psutil.net_io_counters().bytes_recv / 1024,
        }

        # Wi-Fi scanning (expensive! Consider reducing frequency)
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

        # If no GPS heading, just rotate heading for demonstration
        if gps_heading is None:
            heading = (heading + 1) % 360

        sleep(1)  # Avoid tight looping

###############################################################################
# Drawing Functions
###############################################################################
def draw_system_metrics(frame):
    """
    Draws CPU, RAM, Temperature, and Network usage directly onto the camera frame,
    with positions and spacing computed as percentages of screen size.
    """
    # Dynamic positioning based on screen size
    x       = int(SCREEN_WIDTH * 0.02)    # 2% from left edge
    y       = int(SCREEN_HEIGHT * 0.02)   # 2% from top edge (moved up)
    spacing = int(SCREEN_HEIGHT * 0.03)   # 3% of screen height between lines (tighter)

    cv2.putText(frame, f"CPU: {metrics_data.get('CPU', 0)}%",   (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 1)
    y += spacing
    cv2.putText(frame, f"RAM: {metrics_data.get('RAM', 0)}%",   (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
    y += spacing
    cv2.putText(frame, f"Temp: {metrics_data.get('Temp', 'N/A')} C", (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 191, 255), 1)
    y += spacing
    cv2.putText(frame, f"Net Sent: {metrics_data.get('Net_Sent', 0):.2f} KB", (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 1)
    y += spacing
    cv2.putText(frame, f"Net Recv: {metrics_data.get('Net_Recv', 0):.2f} KB", (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
    y += spacing
    cv2.putText(frame, f"FPS: {current_fps:.1f}", (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)

def draw_wifi_signals(frame):
    """
    Draws a short list of the nearest Wi‑Fi access points onto the camera frame,
    positioned in the top‑right corner with dynamic offsets.
    """
    x       = int(SCREEN_WIDTH * 0.65)   # 65% across the screen (more central)
    y       = int(SCREEN_HEIGHT * 0.02)  # 2% down from the top (move up)
    spacing = int(SCREEN_HEIGHT * 0.03)  # 3% spacing (tighter)

    for ssid, signal, channel, security in wifi_signals[:5]:
        cv2.putText(frame, f"SSID: {ssid}",     (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
        y += spacing
        cv2.putText(frame, f"Signal: {signal}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        y += spacing
        cv2.putText(frame, f"Channel: {channel}",  (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 191, 255), 1)
        y += spacing
        cv2.putText(frame, f"Security: {security}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        y += spacing * 2  # extra gap before the next AP

def draw_compass(frame):
    """
    Draws a compass in the lower‑left corner with dynamic sizing
    and text labels positioned relative to the compass radius.
    """
    global heading, gps_heading, latitude, longitude, speed

    # If GPS provided a heading, use it; otherwise our simulated heading is already updated.
    if gps_heading is not None:
        heading = gps_heading

    # Size and position parameters as percentages of screen size
    spacing  = int(SCREEN_HEIGHT * 0.03)                       # 3% spacing (tighter)
    base_x   = int(SCREEN_WIDTH * 0.02)                        # 2% from left
    base_y   = int(SCREEN_HEIGHT * 0.35)                       # 35% from top (move compass further up)
    radius   = int(min(SCREEN_WIDTH, SCREEN_HEIGHT) * 0.06)    # 6% of smaller dimension (smaller compass)
    center   = (base_x + radius, base_y + radius)

    # Draw outer circle
    cv2.circle(frame, center, radius, (128, 0, 128), 2)

    # Compass arrow
    angle = math.radians(-heading + 90)
    tip_x = int(center[0] + radius * math.cos(angle))
    tip_y = int(center[1] + radius * math.sin(angle))
    cv2.line(frame, center, (tip_x, tip_y), (255, 20, 147), 3)

    # Text labels below the compass, spaced by `spacing`
    text_x = base_x
    text_start_y = base_y + radius * 2 + spacing
    cv2.putText(frame, f"Heading: {heading:.1f}°", (text_x, text_start_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.putText(frame, f"Lat: {latitude}",             (text_x, text_start_y + spacing),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(frame, f"Lon: {longitude}",            (text_x, text_start_y + spacing*2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(frame, f"Speed: {speed:.2f} m/s",      (text_x, text_start_y + spacing*3),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

def visualizer_worker():
    while not stop_event.is_set():
        buf = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)
        draw_audio_visualizer(buf)
        with visualizer_lock:
            global latest_visualizer
            latest_visualizer = buf
        sleep(0.1)

def metrics_worker():
    while not stop_event.is_set():
        buf = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)
        draw_system_metrics(buf)
        with metrics_lock:
            global latest_metrics
            latest_metrics = buf
        sleep(0.5)

def wifi_worker():
    while not stop_event.is_set():
        buf = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)
        draw_wifi_signals(buf)
        with wifi_lock:
            global latest_wifi
            latest_wifi = buf
        sleep(1)

def compass_worker():
    while not stop_event.is_set():
        buf = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)
        draw_compass(buf)
        with compass_lock:
            global latest_compass
            latest_compass = buf
        sleep(0.5)
###############################################################################
# Main Functions
###############################################################################
def start_hud():
    global camera_stream, stream, overlay_buffer, current_fps

    # Create window at the very start of start_hud()
    cv2.namedWindow("Unified HUD", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("Unified HUD", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    print("Debug: HUD window created")

    # Start overlay worker threads
    stop_event.clear()
    threading.Thread(target=visualizer_worker, daemon=True).start()
    threading.Thread(target=metrics_worker,    daemon=True).start()
    threading.Thread(target=wifi_worker,       daemon=True).start()
    threading.Thread(target=compass_worker,    daemon=True).start()

    camera_stream = CameraStream(0)
    print("Debug: CameraStream initialized, stream object:", camera_stream.stream)
    # Initialize low-latency audio input/output streams
    try:
        audio_stream = sd.InputStream(
            device=input_dev,
            samplerate=SAMPLERATE,
            blocksize=FRAMES_PER_BUFFER,
            channels=1,
            dtype='float32',
            callback=audio_callback
        )
        output_stream = sd.OutputStream(
            device=output_dev,
            samplerate=SAMPLERATE,
            blocksize=FRAMES_PER_BUFFER,
            channels=1,
            dtype='float32'
        )
        output_stream.start()
        audio_stream.start()
        print(f"Debug: Audio I/O started (in dev={input_dev}, out dev={output_dev})")
    except Exception as e:
        print(f"Audio I/O disabled: {e}")
        audio_stream = None
        output_stream = None

    # Audio input initialization removed
    # try:
    #     stream = sd.InputStream(samplerate=SAMPLERATE, channels=1, callback=audio_callback)
    #     stream.start()
    # except Exception as e:
    #     print(f"Audio input disabled: {e}")
    #     stream = None

    # Audio playback initialization removed
    # init_audio_output()  # Initialize audio playback

    # Start threads for metrics and GPS
    update_event.clear()
    updater_thread = Thread(target=update_metrics, daemon=True)
    gps_thread = Thread(target=gps_worker, daemon=True)
    updater_thread.start()
    gps_thread.start()

    # We create the overlay buffer once (in case you decide to do partial drawings)
    # but we are no longer alpha-blending it. We'll just skip alpha blending altogether.
    # If you don't need an overlay at all, you can simply remove overlay_buffer usage entirely.
    grabbed, temp_frame = camera_stream.stream.read()
    print(f"Debug: overlay_buffer setup grabbed={grabbed}, temp_frame type={type(temp_frame)}")
    if grabbed:
        overlay_buffer = np.zeros_like(temp_frame)
    else:
        overlay_buffer = None
    # Setup FPS monitoring
    fps_last_time = time()
    fps_frame_count = 0

    try:
        while True:
            try:
                print("Debug: Loop iteration start")
                # Update FPS counter
                fps_frame_count += 1
                now = time()
                if now - fps_last_time >= 1.0:
                    current_fps = fps_frame_count / (now - fps_last_time)
                    fps_frame_count = 0
                    fps_last_time = now
                camera_frame = camera_stream.read()
                print(f"Debug: camera_frame retrieved type={type(camera_frame)}")
                # Rotate feed 180° for upside-down camera
                camera_frame = cv2.rotate(camera_frame, cv2.ROTATE_180)
                if camera_frame is None:
                    continue
 
                # Draw overlays directly (no blending)
                draw_audio_visualizer(camera_frame)
                draw_system_metrics(camera_frame)
                draw_wifi_signals(camera_frame)
                draw_compass(camera_frame)
 
 
                # Show the final frame
                cv2.imshow("Unified HUD", camera_frame)
 
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except Exception as e:
                print(f"Exception in HUD loop: {e}")
                traceback.print_exc()
                sleep(1)
    finally:
        cleanup()

def cleanup():
    global camera_stream, stream, output_stream
    print("Shutting down gracefully...")

    # Signal your worker threads to stop
    update_event.set()

    if camera_stream:
        camera_stream.stop()

    if stream:
        try:
            stream.stop()
            stream.close()  # <-- Add this
        except Exception as e:
            print(f"Error stopping/closing input stream: {e}")

    # Signal overlay workers to stop
    stop_event.set()

    if output_stream:
        try:
            output_stream.stop()
            output_stream.close()
        except Exception as e:
            print(f"Error stopping/closing output stream: {e}")

    cv2.destroyAllWindows()
    sys.exit(0)


def audio_callback(indata, frames, time_info, status):
    """Microphone input callback: fill buffer and pass through to output."""
    global audio_data, output_stream
    if status:
        print(f"Audio status: {status}")
    # Copy mono input for visualizer
    audio_data[:] = indata[:, 0]
    # Play back immediately
    if output_stream:
        try:
            output_stream.write(indata)
        except Exception:
            pass

def signal_handler(sig, frame):
    print("\nCtrl+C detected. Exiting...")
    cleanup()
    exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    start_hud()
