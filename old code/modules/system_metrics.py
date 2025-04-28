import psutil
import cv2
import numpy as np
from time import time, sleep

# Initialize global variables for network stats
last_net_io = psutil.net_io_counters()
last_time = time()

def get_system_metrics():
    """Fetch enhanced system metrics."""
    global last_net_io, last_time

    # Basic system stats
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    try:
        temp = psutil.sensors_temperatures()['cpu_thermal'][0].current
    except KeyError:
        temp = "N/A"

    # Network stats
    current_time = time()
    current_net_io = psutil.net_io_counters()
    elapsed_time = current_time - last_time

    if elapsed_time > 0:
        net_sent_speed = (current_net_io.bytes_sent - last_net_io.bytes_sent) / elapsed_time / 1024  # KB/s
        net_recv_speed = (current_net_io.bytes_recv - last_net_io.bytes_recv) / elapsed_time / 1024  # KB/s
    else:
        net_sent_speed = net_recv_speed = 0

    last_net_io = current_net_io
    last_time = current_time

    # Disk I/O stats
    disk_io = psutil.disk_io_counters()
    disk_read_speed = disk_io.read_bytes / 1024  # KB
    disk_write_speed = disk_io.write_bytes / 1024  # KB

    return {
        "CPU": cpu,
        "RAM": ram,
        "Temp": temp,
        "Net_Sent": net_sent_speed,
        "Net_Recv": net_recv_speed,
        "Disk_Read": disk_read_speed,
        "Disk_Write": disk_write_speed,
    }

def draw_system_metrics(frame, metrics):
    """Draw enhanced system metrics on the frame."""
    y = 50  # Initial y-coordinate for the text
    spacing = 40  # Spacing between lines

    # Display basic system stats
    cv2.putText(frame, f"CPU: {metrics['CPU']}%", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
    y += spacing
    cv2.putText(frame, f"RAM: {metrics['RAM']}%", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    y += spacing
    cv2.putText(frame, f"Temp: {metrics['Temp']} C", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 191, 255), 2)
    y += spacing

    # Display network stats
    cv2.putText(frame, f"Net Sent: {metrics['Net_Sent']:.2f} KB/s", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 165, 0), 2)
    y += spacing
    cv2.putText(frame, f"Net Recv: {metrics['Net_Recv']:.2f} KB/s", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
    y += spacing

    # Display disk I/O stats
    cv2.putText(frame, f"Disk Read: {metrics['Disk_Read']:.2f} KB", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    y += spacing
    cv2.putText(frame, f"Disk Write: {metrics['Disk_Write']:.2f} KB", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (128, 0, 128), 2)

def display_system_metrics():
    """Continuously display enhanced system metrics over the camera feed."""
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
            camera_frame = cv2.resize(camera_frame, (800, 400))

            # Create a transparent overlay frame
            overlay_frame = np.zeros((400, 800, 3), dtype="uint8")

            # Get system metrics
            metrics = get_system_metrics()

            # Draw system metrics on the transparent overlay
            draw_system_metrics(overlay_frame, metrics)

            # Blend the overlay with the camera feed
            combined_frame = cv2.addWeighted(camera_frame, 0.7, overlay_frame, 0.3, 0)

            # Show the final HUD frame
            cv2.imshow("System Metrics HUD", combined_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    display_system_metrics()
