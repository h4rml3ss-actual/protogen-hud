import cv2
import numpy as np
import math

def draw_compass(heading, frame):
    """
    Draw a compass on the frame with a given heading (in degrees).
    - heading: The direction to point (0° = North, 90° = East, etc.).
    """
    center = (200, 200)
    radius = 100

    # Draw the compass circle
    cv2.circle(frame, center, radius, (128, 0, 128), 3)

    # Draw the compass needle
    angle = math.radians(-heading + 90)  # Adjust for compass orientation
    x = int(center[0] + radius * math.cos(angle))
    y = int(center[1] + radius * math.sin(angle))
    cv2.line(frame, center, (x, y), (255, 20, 147), 5)

    # Draw the heading as text
    cv2.putText(frame, f"Heading: {heading}°", (10, 390), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

def display_compass():
    """Continuously display the compass over the camera feed."""
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Error: Camera not found. Exiting.")
        return

    try:
        heading = 0  # Example heading value; replace with GPS/antenna input later

        while True:
            # Capture the camera frame
            ret, camera_frame = camera.read()
            if not ret:
                print("Error: Could not read camera frame. Exiting loop.")
                break

            # Resize camera feed to match display size
            camera_frame = cv2.resize(camera_frame, (400, 400))

            # Create a transparent overlay frame
            overlay_frame = np.zeros((400, 400, 3), dtype="uint8")

            # Draw the compass on the transparent overlay
            draw_compass(heading, overlay_frame)

            # Blend the overlay with the camera feed
            combined_frame = cv2.addWeighted(camera_frame, 0.7, overlay_frame, 0.3, 0)

            # Show the final HUD frame
            cv2.imshow("Compass HUD", combined_frame)

            # Increment heading for demonstration (simulate rotation)
            heading = (heading + 1) % 360  # Loop from 0° to 359°

            # Exit on 'q'
            key = cv2.waitKey(50)
            if key & 0xFF == ord('q'):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    display_compass()
