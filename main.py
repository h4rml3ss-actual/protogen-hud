# main.py
# Entrypoint: starts HUD and orchestrates modules

import cv2
from camera import CameraStream
from metrics import get_system_metrics
from draw_utils import draw_text
from audio_visualizer import draw_audio_visualizer
from wifi_scanner import get_display_wifi
from gps_tracker import gps_heading, latitude, longitude, speed, draw_compass
from service_threads import start_all_services, stop_all_services
from theme import NEON_PINK, NEON_GREEN, NEON_ORANGE, NEON_BLUE, NEON_PURPLE
import traceback
import os

def log_startup(message):
    with open("startup.log", "a") as f:
        f.write(message + "\n")
    print(message)

def main():
    # Log startup message indicating HUD is starting
    log_startup("=== HUD Starting Up ===")
    # Initialize the camera stream for capturing video frames
    log_startup("Initializing camera...")
    cam = CameraStream()
    
    # Start all required background services (e.g., audio, sensors)
    log_startup("Starting services...")
    start_all_services()

    # Create and configure the OpenCV window for displaying the HUD
    log_startup("Creating OpenCV window...")
    cv2.namedWindow("HUD Camera Test", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("HUD Camera Test", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # Begin the main loop to continuously capture and process frames for HUD display
    log_startup("Entering main loop...")
    try:
        while True:
            # Capture a frame from the camera and rotate it for correct orientation
            frame = cam.read()
            frame = cv2.rotate(frame, cv2.ROTATE_180)
            if frame is not None:
                # Retrieve current system metrics (CPU usage, RAM, temperature, etc.)
                metrics = get_system_metrics()

                # Define starting position and spacing for left-side HUD text
                x, y, spacing = 30, 50, 35
                # Display CPU usage in neon pink
                draw_text(frame, f"CPU: {metrics.get('CPU', 0)}%", (x, y), NEON_PINK)
                # Display RAM usage in neon green
                draw_text(frame, f"RAM: {metrics.get('RAM', 0)}%", (x, y + spacing), NEON_GREEN)
                # Display Temperature in neon orange
                draw_text(frame, f"Temp: {metrics.get('Temp', 'N/A')}°C", (x, y + spacing * 2), NEON_ORANGE)
                # Display Network Sent data in neon blue
                draw_text(frame, f"Net ↑: {metrics.get('Net_Sent', 0):.1f} KB", (x, y + spacing * 3), NEON_BLUE)
                # Display Network Received data in neon purple
                draw_text(frame, f"Net ↓: {metrics.get('Net_Recv', 0):.1f} KB", (x, y + spacing * 4), NEON_PURPLE)

                # Display compass and GPS information below system metrics
                draw_text(frame, f"Heading: {gps_heading:.1f}°" if gps_heading else "Heading: N/A", (x, y + spacing * 5), NEON_GREEN)
                draw_text(frame, f"Lat: {latitude}", (x, y + spacing * 6), NEON_BLUE)
                draw_text(frame, f"Lon: {longitude}", (x, y + spacing * 7), NEON_BLUE)
                draw_text(frame, f"Speed: {speed:.2f} m/s", (x, y + spacing * 8), NEON_BLUE)

                # Render a visual compass overlay based on the current GPS heading
                draw_compass(frame, gps_heading if gps_heading else 0)

                # Overlay the audio visualizer on the frame
                draw_audio_visualizer(frame)

                # Draw HUD ONLINE text
                # draw_text(frame, "HUD ONLINE", (30, 50), (0, 255, 0))
                
                # Retrieve and display Wi-Fi network details on the right side of the HUD
                wifi_x, wifi_y = 950, 50
                wifi_spacing = 20
                for i, net in enumerate(get_display_wifi()):
                    draw_text(frame, f"{net['SSID']}", (wifi_x, wifi_y + i * wifi_spacing * 4), NEON_BLUE)
                    draw_text(frame, f"Signal: {net['Signal']}", (wifi_x, wifi_y + i * wifi_spacing * 4 + wifi_spacing), NEON_GREEN)
                    draw_text(frame, f"Channel: {net['Channel']}", (wifi_x, wifi_y + i * wifi_spacing * 4 + wifi_spacing * 2), NEON_BLUE)
                    draw_text(frame, f"Security: {net['Security']}", (wifi_x, wifi_y + i * wifi_spacing * 4 + wifi_spacing * 3), NEON_ORANGE)

                # Update the OpenCV window with the latest processed frame
                cv2.imshow("HUD Camera Test", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Quitting camera test.")
                break
    finally:
        # Cleanup: stop the camera stream, terminate services, and close display windows
        cam.stop()
        stop_all_services()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        with open("error.log", "w") as f:
            f.write("Unhandled exception occurred:\n")
            traceback.print_exc(file=f)
        print("An error occurred. See error.log for details.")
