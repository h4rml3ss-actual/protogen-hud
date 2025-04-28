# Camera feed module.
# camera_feed.py
import cv2

def start_camera():
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Error: Camera not found.")
        return

    while True:
        ret, frame = camera.read()
        if not ret:
            print("Error: Could not read frame.")
            break

        # Add neon border
        border_thickness = 10
        cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), (255, 20, 147), border_thickness)

        # Add neon text
        cv2.putText(frame, "Live Camera Feed", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 191, 255), 3)

        # Display the camera feed
        cv2.imshow("Camera Feed", frame)

        # Exit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    camera.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    start_camera()
