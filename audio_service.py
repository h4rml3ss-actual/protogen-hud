"""
audio_service.py
----------------
Audio capture service that runs in a background thread and writes audio data
to SharedState for visualization by the renderer.
"""

import numpy as np
import sounddevice as sd
import threading
import logging

# Constants for audio processing
SAMPLERATE = 48000
FRAMES_PER_BUFFER = 1024

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def start_audio_service(shared_state, stop_event, enable_passthrough=True, output_device=None):
    """
    Starts the audio capture service in a background daemon thread.
    
    This service captures audio from the default microphone and writes the
    audio buffer to SharedState for visualization. Optionally supports
    audio passthrough to an output device.
    
    Args:
        shared_state: SharedState instance for storing audio data
        stop_event: threading.Event to signal service shutdown
        enable_passthrough: If True, pass audio through to output device
        output_device: Device index or name for audio output (None = default)
    
    Returns:
        threading.Thread: The started daemon thread
    """
    def audio_service_thread():
        """Main audio service thread function."""
        input_stream = None
        output_stream = None
        audio_buffer = np.zeros(FRAMES_PER_BUFFER, dtype=np.float32)
        buffer_lock = threading.Lock()
        
        def audio_callback(indata, frames, time_info, status):
            """
            Callback function for sounddevice.InputStream.
            Copies audio data into buffer and writes to SharedState.
            """
            nonlocal audio_buffer, output_stream
            
            # Log any status issues
            if status:
                logger.warning(f"[Audio] Stream status: {status}")
            
            # Copy audio data to local buffer
            with buffer_lock:
                audio_buffer[:] = np.copy(indata[:, 0])
            
            # Write to SharedState
            shared_state.set_audio_buffer(audio_buffer)
            
            # Pass through to output if enabled
            if output_stream and enable_passthrough:
                try:
                    output_stream.write(indata)
                except sd.PortAudioError as e:
                    logger.error(f"[Audio] Output stream error: {e}")
        
        try:
            # Initialize input stream
            logger.info("[Audio] Initializing audio input stream...")
            input_stream = sd.InputStream(
                callback=audio_callback,
                channels=1,
                samplerate=SAMPLERATE,
                blocksize=FRAMES_PER_BUFFER,
                dtype='int16'
            )
            input_stream.start()
            logger.info("[Audio] Audio input stream started successfully")
            
            # Initialize output stream for passthrough if enabled
            if enable_passthrough:
                try:
                    logger.info(f"[Audio] Initializing audio passthrough to device: {output_device or 'default'}")
                    output_stream = sd.OutputStream(
                        samplerate=SAMPLERATE,
                        channels=1,
                        device=output_device,
                        dtype='int16'
                    )
                    output_stream.start()
                    logger.info("[Audio] Audio passthrough started successfully")
                except Exception as e:
                    logger.warning(f"[Audio] Failed to initialize passthrough: {e}")
                    logger.info("[Audio] Continuing without passthrough")
                    output_stream = None
            
            # Keep thread alive until stop_event is set
            while not stop_event.is_set():
                stop_event.wait(timeout=0.1)
            
            logger.info("[Audio] Stop signal received, shutting down...")
            
        except Exception as e:
            logger.error(f"[Audio] Audio service error: {e}", exc_info=True)
        
        finally:
            # Clean up streams
            if input_stream:
                try:
                    input_stream.stop()
                    input_stream.close()
                    logger.info("[Audio] Input stream closed")
                except Exception as e:
                    logger.error(f"[Audio] Error closing input stream: {e}")
            
            if output_stream:
                try:
                    output_stream.stop()
                    output_stream.close()
                    logger.info("[Audio] Output stream closed")
                except Exception as e:
                    logger.error(f"[Audio] Error closing output stream: {e}")
    
    # Create and start daemon thread
    thread = threading.Thread(target=audio_service_thread, daemon=True, name="AudioService")
    thread.start()
    logger.info("[Audio] Audio service thread started")
    
    return thread
