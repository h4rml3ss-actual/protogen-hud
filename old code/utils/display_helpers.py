# Helper functions for combining and displaying frames.
# utils/display_helpers.py
import cv2
import numpy as np

def create_blank_frame(width=800, height=600, color=(0, 0, 0)):
    """
    Create a blank frame with a given color (default: black).
    """
    return np.zeros((height, width, 3), dtype="uint8")

def overlay_frames(base_frame, overlay_frame, alpha=0.7):
    """
    Overlay one frame on top of another with transparency.
    - base_frame: The bottom frame.
    - overlay_frame: The top frame to overlay.
    - alpha: Transparency of the overlay (0.0 to 1.0).
    """
    return cv2.addWeighted(base_frame, 1 - alpha, overlay_frame, alpha, 0)

def draw_neon_text(frame, text, position, font_scale=1, color=(255, 0, 255), thickness=2):
    """
    Draw neon-styled text on a frame.
    - frame: The frame to draw on.
    - text: The string to draw.
    - position: (x, y) coordinates for the text.
    - font_scale: Size of the text.
    - color: Neon color (default: purple).
    - thickness: Thickness of the text.
    """
    x, y = position
    shadow_offset = 2

    # Shadow effect
    cv2.putText(frame, text, (x + shadow_offset, y + shadow_offset), 
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness + 2)

    # Main neon text
    cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def combine_multiple_frames(frames, layout=(1, 1)):
    """
    Combine multiple frames into a grid layout for display.
    - frames: List of frames to combine.
    - layout: Tuple (rows, cols) for the grid layout.
    """
    rows, cols = layout
    blank_frame = create_blank_frame()

    # Ensure all frames are the same size
    h, w = frames[0].shape[:2]
    resized_frames = [cv2.resize(frame, (w, h)) for frame in frames]

    # Create a grid of blank frames
    combined_frame = create_blank_frame(width=w * cols, height=h * rows)

    # Place each frame into the grid
    for idx, frame in enumerate(resized_frames):
        row = idx // cols
        col = idx % cols
        y1, y2 = row * h, (row + 1) * h
        x1, x2 = col * w, (col + 1) * w
        combined_frame[y1:y2, x1:x2] = frame

    return combined_frame
