# Unified Heads-Up Display (HUD) for Protogen Helmet

## Overview
The `hud.py` script is a core module of the Protogen Helmet system that provides a unified heads-up display (HUD) overlay. This script integrates real-time system metrics, audio visualizations, GPS data, and Wi-Fi signal strength into a single display powered by OpenCV and other Python libraries. The module is optimized for the Raspberry Pi 5 and is designed to support low-latency performance.

## Features

### 1. **Camera Stream Integration**
- Displays live video feed from the connected camera.
- Optimized for 1280x720 resolution.

### 2. **Audio Visualizer**
- Displays real-time FFT-based audio visualizations.
- Configurable number of bars and animation radius.

### 3. **System Metrics Overlay**
- Monitors and displays:
  - CPU usage
  - RAM usage
  - CPU temperature
  - Network bandwidth (sent/received)

### 4. **Wi-Fi Signal Scanner**
- Displays information about nearby Wi-Fi networks, including:
  - SSID
  - Signal strength
  - Channel
  - Security type

### 5. **GPS Data Integration**
- Shows GPS-based heading, latitude, longitude, and speed.
- Integrates with `gpsd` for live updates.

### 6. **Compass Overlay**
- Displays a real-time compass that updates based on GPS or simulated heading.

## Prerequisites

### Hardware
- Raspberry Pi 5 (recommended for performance).
- HDMI-compatible display (e.g., Epson Moverio glasses).
- Camera module for Raspberry Pi.
- Microphone and audio output device.
- USB GPS module

### Software
- Raspberry Pi OS (latest version).
- Python 3.9 or higher.
- Libraries:
  - OpenCV (`cv2`)
  - NumPy
  - SoundDevice (`sounddevice`)
  - GPS (`gps`)
  - Psutil

## Installation
1. **Install Required Python Packages**:
   ```bash
   pip install opencv-python numpy sounddevice gps psutil
   ```

2. **Configure GPS**:
   - Install and configure `gpsd`:
     ```bash
     sudo apt-get install gpsd gpsd-clients
     sudo systemctl enable gpsd
     sudo systemctl start gpsd
     ```

3. **Camera Configuration**:
   - Ensure the camera module is enabled in the Raspberry Pi settings:
     ```bash
     sudo raspi-config
     ```
   - Select **Interface Options > Camera** and enable it.
   - (NOTE: Unneeded if using USB camera)

4. **Set Environment Variables**:
   - Add the following to your shell configuration file (e.g., `.bashrc`):
     ```bash
     export QT_QPA_PLATFORM=xcb
     export OPENCV_OPENCL_RUNTIME=true
     ```

## Usage

### Starting the HUD
Run the script directly:
```bash
python3 hud.py
```

### Stopping the HUD
Press `Ctrl+C` or 'q' to terminate the application gracefully.

## Code Structure

### Modules
- **CameraStream**: Manages the live camera feed.
- **Audio Visualizer**: Processes audio input and renders visualizations.
- **System Metrics Updater**: Monitors and updates system statistics.
- **GPS Worker**: Retrieves and updates GPS data.
- **Drawing Functions**:
  - System Metrics
  - Wi-Fi Signals
  - Compass

### Main Functions
- `start_hud()`: Initializes and runs the HUD.
- `cleanup()`: Handles graceful shutdown of all resources.

## Customization
- **Visualizer Parameters**:
  - `NUM_BARS`: Number of FFT bars to display.
  - `RADIUS`: Radius of the circular visualizer.

- **Camera Resolution**:
  - Modify the `cv2.CAP_PROP_FRAME_WIDTH` and `cv2.CAP_PROP_FRAME_HEIGHT` values in the `CameraStream` class.

- **Wi-Fi Scan Frequency**:
  - Adjust the sleep interval in the `update_metrics` function.

## Known Issues
- High CPU usage during Wi-Fi scanning.
  - Recommendation: Reduce scanning frequency or disable if not critical.

- GPS errors if `gpsd` is not properly configured.

## Contributing
Feel free to contribute enhancements or report issues. Fork this repository and submit a pull request for review.

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments
- Special thanks to the open-source community for libraries and tools used in this project.

---

