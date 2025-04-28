import cv2
from threading import Thread

class CameraStream:
    """
    CameraStream class handles video capture from a camera source in a separate thread to improve performance.
    """
    def __init__(self, src=0, width=1280, height=720):
        """
        Initialize the camera stream with the given source and resolution.
        
        Args:
            src (int or str): Camera source index or video file path.
            width (int): Desired width of the video frames.
            height (int): Desired height of the video frames.
        """
        # Open the video capture stream
        self.stream = cv2.VideoCapture(src)
        if not self.stream.isOpened():
            # Raise an error if the camera stream cannot be opened
            raise RuntimeError("Failed to open camera stream.")
        
        # Set the video codec to MJPG for better performance on USB cameras
        self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        
        # Set the buffer size to minimize latency if the property is supported by the driver
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Set the desired frame width and height
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        # Read the first frame from the stream to initialize
        self.grabbed, self.frame = self.stream.read()
        # Flag to indicate if the thread should stop running
        self.stopped = False

        # Start the thread to update frames from the stream in the background
        self.thread = Thread(target=self.update, args=(), daemon=True)
        self.thread.start()

    def update(self):
        """
        Continuously capture frames from the camera stream in a separate thread.
        This method runs in the background and updates the current frame.
        """
        while not self.stopped:
            # If frame capture failed, stop the stream
            if not self.grabbed:
                self.stop()
            else:
                # Read the next frame from the stream
                self.grabbed, self.frame = self.stream.read()

    def read(self):
        """
        Return the most recent frame captured from the camera stream.
        
        Returns:
            frame (ndarray): The latest video frame.
        """
        return self.frame

    def stop(self):
        """
        Stop the camera stream and release the video capture resource.
        """
        self.stopped = True
        self.stream.release()
