"""
audio_visualizer.py
-------------------
Handles audio input from microphone and renders a circular FFT-based visualizer
onto the HUD frame.
"""

import numpy as np
import sounddevice as sd
import math
import cv2
from threading import Lock
from theme import CENTER, RADIUS, NEON_PINK

# Constants for audio processing
SAMPLERATE = 48000
FRAMES_PER_BUFFER = 1024
NUM_BARS = 60

# Shared buffer for audio data and lock for thread safety
audio_buffer = np.zeros(FRAMES_PER_BUFFER, dtype=np.float32)
audio_lock = Lock()

# New output stream for audio passthrough
output_stream = None

def find_output_device(name_hint="wm8960"):
    """
    Finds the first output device containing the given name hint.
    """
    # Iterate over all available audio devices
    for i, device in enumerate(sd.query_devices()):
        # Check if device name contains the hint string (case-insensitive)
        # and if it supports output channels
        if name_hint.lower() in device["name"].lower() and device["max_output_channels"] > 0:
            return i  # Return the device index if found
    # Raise error if no matching device is found
    raise RuntimeError(f"No matching output device found for '{name_hint}'")

def audio_callback(indata, frames, time_info, status):
    """
    Callback function for sounddevice.InputStream.
    Copies mono audio data into the shared buffer.
    """
    global audio_buffer, output_stream
    # Acquire lock to safely update shared audio buffer
    with audio_lock:
        # Copy the first channel of the input audio data (mono) into buffer
        audio_buffer[:] = np.copy(indata[:, 0])
    
    # If output stream is initialized, write input audio to output (passthrough)
    if output_stream:
        try:
            output_stream.write(indata)
        except sd.PortAudioError as e:
            # Print error if output stream write fails
            print(f"[Audio] Output stream error: {e}")

def start_audio_stream():
    """
    Starts the audio input stream using sounddevice.
    Audio data is fed into audio_callback in real-time.
    """
    global output_stream
    # Create an input stream with specified parameters:
    # callback function, mono channel, sample rate, block size, and 16-bit int data type
    stream = sd.InputStream(callback=audio_callback, channels=1, samplerate=SAMPLERATE, blocksize=FRAMES_PER_BUFFER, dtype='int16')
    stream.start()  # Start the input audio stream
    
    # Find the output device index matching "wm8960"
    device_index = find_output_device("wm8960")

    # Create and start an output stream with matching parameters for audio passthrough
    output_stream = sd.OutputStream(samplerate=SAMPLERATE, channels=1, device=device_index, dtype='int16')
    output_stream.start()

def draw_audio_visualizer(frame):
    """
    Performs FFT on buffered audio samples and draws radial bars onto the frame
    to visualize amplitude by frequency band.
    """
    global audio_buffer
    # Acquire lock to safely copy audio samples from shared buffer
    with audio_lock:
        samples = np.copy(audio_buffer)

    # Compute the one-sided FFT magnitude of the samples
    fft = np.abs(np.fft.rfft(samples))[:NUM_BARS]
    # Normalize FFT values to max amplitude of 1 if max is greater than zero
    if np.max(fft) > 0:
        fft /= np.max(fft)

    # Calculate angular step between each bar in degrees
    angle_step = 360 / NUM_BARS
    # Iterate over each frequency bin and its amplitude
    for i, amplitude in enumerate(fft):
        # Scale the bar length proportionally to the amplitude
        length = int(amplitude * 100)  # Scale bar length
        # Convert angle to radians for trigonometric functions
        angle = math.radians(i * angle_step)
        # Calculate starting point on the circle circumference
        x1 = int(CENTER[0] + RADIUS * np.cos(angle))
        y1 = int(CENTER[1] + RADIUS * np.sin(angle))
        # Calculate ending point extended outward by the bar length
        x2 = int(CENTER[0] + (RADIUS + length) * np.cos(angle))
        y2 = int(CENTER[1] + (RADIUS + length) * np.sin(angle))
        # Draw a line from start to end point with neon pink color and thickness 2
        cv2.line(frame, (x1, y1), (x2, y2), NEON_PINK, 2)
