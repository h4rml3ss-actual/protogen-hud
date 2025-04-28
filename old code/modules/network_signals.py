import subprocess
import cv2
import numpy as np

def get_wifi_signals():
    """Scan for Wi-Fi networks and return their signal strengths."""
    result = subprocess.run(["iwlist", "wlan0", "scan"], capture_output=True, text=True)
    networks = []
    ssid = None
    signal_strength = None

    for line in result.stdout.split("\n"):
        line = line.strip()

        # Extract SSID
        if "ESSID" in line:
            ssid = line.split(":")[1].strip('"')

        # Extract signal strength (quality or dBm)
        if "Quality" in line or "Signal level" in line:
            if "Quality" in line:
                quality = line.split("Quality=")[1].split()[0]
                current, max_value = map(int, quality.split("/"))
                signal_strength = int((current / max_value) * 100)
            elif "Signal level" in line:
                signal_strength = int(line.split("Signal level=")[1].split()[0])

            if ssid and signal_strength is not None:
                networks.append((ssid, signal_strength))
                ssid = None
                signal_strength = None

    return networks

def draw_wifi_signals(frame, networks):
    """Draw Wi-Fi signal strengths as a horizontal bar graph."""
    max_width = 600  # Maximum width of a bar
    bar_height = 30  # Height of each bar
    start_y = 20     # Starting y-coordinate for the first bar

    for i, (ssid, signal) in enumerate(networks):
        strength = signal
        bar_width = int((strength / 100) * max_width)
        x1 = 200  # Starting x-coordinate for all bars
        y1 = start_y + i * (bar_height + 10)
        x2 = x1 + bar_width
        y2 = y1 + bar_height

        # Neon gradient
        color = (255 - int(255 * (strength / 100)), 0, 255)

        # Draw the bar
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)

        # Draw the SSID and signal strength
        cv2.putText(frame, f"{ssid} ({strength}%)", (10, y1 + bar_height - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

def display_wifi_signals():
    """Continuously display Wi-Fi signal strengths over the camera feed."""
    # Open the camera feed
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Error: Camera not found.")
        return

    try:
        while True:
            # Capture the camera frame
            ret, camera_frame = camera.read()
            if not ret:
                print("Error: Could not read camera frame.")
                break

            # Resize camera feed to match display size
            camera_frame = cv2.resize(camera_frame, (800, 500))

            # Create a transparent overlay frame
            overlay_frame = np.zeros((500, 800, 3), dtype="uint8")

            # Get Wi-Fi network signals
            networks = get_wifi_signals()
            if not networks:
                networks = [("No Network", 0)]  # Default placeholder

            # Draw network signals on the transparent overlay
            draw_wifi_signals(overlay_frame, networks[:10])  # Display up to 10 networks

            # Blend the overlay with the camera feed
            combined_frame = cv2.addWeighted(camera_frame, 0.7, overlay_frame, 0.3, 0)

            # Show the final HUD frame
            cv2.imshow("Wi-Fi Signals HUD", combined_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    display_wifi_signals()
