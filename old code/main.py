# Entry point for the HUD system.
import cv2
import numpy as np
from threading import Thread
from modules.audio_visualizer import start_audio_visualizer
from modules.compass_widget import draw_compass
from modules.system_metrics import get_system_metrics
from modules.network_signals import get_wifi_signals
from utils.display_helpers import overlay_frames, draw_neon_text

def start_camera():
    """Capture live camera feed."""
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Error: Camera not found.")
        return

    try:
        while True:
            # Read the camera feed
            ret, camera_frame = camera.read()
            if not ret:
                print("Error: Could not read camera frame.")
                break

            # Resize camera feed to match display size
            camera_frame = cv2.resize(camera_frame, (800, 800))

            # Initialize overlay frame
            overlay_frame = np.zeros_like(camera_frame)

            # Audio Visualizer
            fft_frame = np.zeros((800, 800, 3), dtype="uint8")
            # Add your existing audio visualizer frame logic here...

            # Compass
            compass_frame = np.zeros((800, 800, 3), dtype="uint8")
            draw_compass(45, compass_frame)  # Replace 45 with actual heading

            # System Metrics
            metrics = get_system_metrics()
            draw_neon_text(overlay_frame, f"CPU: {metrics['CPU']}%", (10, 50), color=(255, 0, 255))
            draw_neon_text(overlay_frame, f"RAM: {metrics['RAM']}%", (10, 100), color=(0, 255, 0))
            draw_neon_text(overlay_frame, f"Temp: {metrics['Temp']}C", (10, 150), color=(0, 191, 255))

            # Wi-Fi Signal Strength
            wifi_signals = get_wifi_signals()[:5]  # Top 5 networks
            for idx, (ssid, signal) in enumerate(wifi_signals):
                draw_neon_text(overlay_frame, f"{ssid}: {signal}%", (10, 200 + idx * 30), color=(255, 165, 0))

            # Combine overlays with transparency
            combined_frame = cv2.addWeighted(camera_frame, 0.7, overlay_frame, 0.3, 0)

            # Show the final HUD frame
            cv2.imshow("Protogen HUD", combined_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # Start the HUD system
    start_camera()
