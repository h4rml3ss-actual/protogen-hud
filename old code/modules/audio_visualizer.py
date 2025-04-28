import os
import sounddevice as sd
import numpy as np
import cv2

# Force OpenCV to use X11 instead of Wayland
os.environ["QT_QPA_PLATFORM"] = "xcb"

# Parameters
SAMPLERATE = 44100
FRAMES_PER_BUFFER = 1024
NUM_BARS = 60
RADIUS = 200
CENTER = (400, 400)

# Global variable for audio data
audio_data = np.zeros(FRAMES_PER_BUFFER, dtype=np.float32)

def audio_callback(indata, frames, time, status):
    """Capture audio input."""
    global audio_data
    if status:
        print(f"Audio Status: {status}")
    audio_data = np.frombuffer(indata, dtype=np.float32)

def start_audio_visualizer():
    """Visualize real-time audio as a circular spectrum over the camera feed."""
    global audio_data

    # Start the audio stream
    stream = sd.InputStream(samplerate=SAMPLERATE, channels=1, callback=audio_callback)
    stream.start()

    # Open the camera feed
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Error: Camera not found.")
        return

    try:
        while True:
            # Read the camera frame
            ret, camera_frame = camera.read()
            if not ret:
                print("Error: Could not read camera frame.")
                break

            # Resize camera feed to match visualizer size
            camera_frame = cv2.resize(camera_frame, (800, 800))

            # Create a transparent frame for the visualizer
            visualizer_frame = np.zeros((800, 800, 3), dtype="uint8")

            # Perform FFT on audio data
            fft = np.abs(np.fft.rfft(audio_data))[:NUM_BARS]
            fft = fft / np.max(fft) if np.max(fft) != 0 else fft  # Normalize

            # Draw the circular spectrum
            angle_step = 360 / NUM_BARS
            for i, amplitude in enumerate(fft):
                length = int(amplitude * 400)  # Scale amplitude for bar length
                angle = np.radians(i * angle_step)
                x1 = int(CENTER[0] + RADIUS * np.cos(angle))
                y1 = int(CENTER[1] + RADIUS * np.sin(angle))
                x2 = int(CENTER[0] + (RADIUS + length) * np.cos(angle))
                y2 = int(CENTER[1] + (RADIUS + length) * np.sin(angle))

                # Neon gradient
                color = (255 - i * 4, 0, 255)
                cv2.line(visualizer_frame, (x1, y1), (x2, y2), color, 2)

            # Blend the visualizer with the camera feed
            combined_frame = cv2.addWeighted(camera_frame, 0.7, visualizer_frame, 0.3, 0)

            # Show the blended frame
            cv2.imshow("Audio Visualizer HUD", combined_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        stream.stop()
        camera.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    start_audio_visualizer()
