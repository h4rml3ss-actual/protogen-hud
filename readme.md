# Protogen HUD

## Overview

A real-time augmented reality heads-up display system designed for wearable devices. The HUD provides live camera feed with overlay widgets for system monitoring, GPS tracking, IMU orientation, Wi-Fi scanning with RF device detection, and audio visualization. Built with a modular, thread-safe architecture for plug-and-play hardware support.

## System Architecture

The HUD uses a modular service-based architecture with centralized state management:

- **SharedState**: Thread-safe centralized data store for all sensor and service data
- **ServiceManager**: Coordinates lifecycle of all background service threads
- **Service Modules**: Independent daemon threads that collect data and write to SharedState
- **Renderer**: Reads from SharedState snapshot and renders all HUD overlays
- **Main Loop**: Orchestrates camera capture, state snapshot, rendering, and display

This architecture provides clean separation of concerns, thread safety, and graceful degradation when hardware is unavailable.

## Hardware Specifications

### Required Components
- **Compute:** Raspberry Pi 5 (8GB RAM) with M.2 Hat and SSD, or LattePanda Alpha (x86-64)
- **Display:** VuFine Wearable Display (1280x720 HDMI) or similar HDMI display
- **Camera:** Arducam USB IR Camera (1080p, automatic IR switching, MJPG output) or compatible USB camera

### Optional Components
- **GPS:** USB GPS receiver (e.g., Stratux vk-162, GlobalSat BU-353-S4) - for location and heading
- **IMU:** Adafruit BNO085 9-DOF IMU (I2C) - for precise heading, pitch, roll
- **Wi-Fi Adapters:** 1-2 USB Wi-Fi adapters for network scanning and direction finding
- **Audio:** USB microphone or WM8960 Sound Card (Audio Hat) - for audio visualization
- **Microphone:** USB-C Conference Microphone or compatible audio input device

## Features

### Core Features

#### ✅ Camera Feed
- Fullscreen display of USB camera feed with HUD overlays
- Target: 30 FPS at 1280x720 (MJPG)
- Hardware-accelerated rendering where available

#### ✅ System Metrics Widget (Left Side)
- Real-time monitoring: CPU usage, CPU temperature, RAM usage
- Network activity: bytes sent/received
- Platform-agnostic temperature reading with fallback
- Updates every second

#### ✅ GPS Tracking Widget (Left Side, Below Metrics)
- Displays: latitude, longitude, speed, heading
- Requires USB GPS device connected to gpsd daemon
- Updates every few seconds
- Optional - gracefully disabled if hardware unavailable

#### ✅ IMU Orientation Tracking
- Precise heading, pitch, and roll from BNO085 9-DOF sensor
- Connected via I2C (typically /dev/i2c-1)
- IMU heading takes priority over GPS heading when both enabled
- ~50Hz update rate
- Optional - gracefully disabled if hardware unavailable

#### ✅ Compass Display
- Visual compass ring with cardinal directions
- Shows current heading from IMU or GPS
- Displays RF device direction indicators with color-coded icons
- Positioned on left side with GPS widget

### Advanced RF Features

#### ✅ Wi-Fi Scanner with RF Device Detection (Right Side)
- Scans for nearby Wi-Fi networks using iwlist
- Displays: SSID, signal strength (dBm), channel, security status
- **Device Classification**: Automatically identifies device types
  - Routers (standard Wi-Fi APs)
  - Drones (DJI, Parrot, Autel, etc. based on SSID patterns and frequency)
  - Unknown devices
- **Distance Estimation**: Calculates approximate distance using path loss formula
  - Accounts for 2.4GHz vs 5.8GHz frequency differences
  - Adjusts for device type (router vs drone transmit power)
  - Displays distance in meters (<1000m) or kilometers (≥1000m)
- **Color Coding**: Each device assigned unique persistent color for tracking
- Rotates through network list for readability
- Updates every 15 seconds

#### ✅ Wi-Fi Direction Finding (Dual Adapter)
- Estimates direction to RF devices using signal strength comparison
- Requires two USB Wi-Fi adapters positioned on left and right sides
- **Triangulation**: Refines distance estimates using dual-adapter measurements
- Combines with IMU/GPS heading for absolute direction
- Confidence metric based on signal differential
- Updates every 5 seconds
- Optional - requires dual adapters and heading source

#### ✅ Heading Readout Bar (Top Center)
- Horizontal degree scale showing ±60° from current heading
- Cardinal direction markers (N, E, S, W)
- Digital heading readout
- **RF Device Icons**: Shows detected devices at their relative bearing
  - Device type icons (router, drone, unknown) in white/light gray
  - Color-coded borders using device's unique color
  - Distance estimate below each icon
  - Automatic stacking for devices within 5° of each other
  - Leader lines connect stacked icons to scale positions

#### ✅ Enhanced Compass Indicators
- Device type icons on compass ring
- Color-coded borders for each device
- Distance estimates next to labels
- Automatic label stacking for devices within 15° on compass
- Leader lines from stacked labels to compass positions
- Prioritizes closer/stronger signals at top of stack

#### ✅ Enhanced RF Device List (Right Side)
- Device type icons with color-coded accent bars
- Distance estimates next to SSID
- Channel number display
- Signal strength bar and dBm value
- Consistent color coding across heading bar, compass, and list
- Rotation through all detected devices

### Audio Features

#### ✅ Audio Visualizer Widget (Top Center)
- Circular audio level display with FFT waveform
- Real-time audio input from microphone
- Audio passthrough functionality
- Balanced performance (not blocking)
- Optional - gracefully disabled if audio device unavailable

### Calibration Features

#### ✅ Wi-Fi Adapter Calibration
- Interactive startup calibration for dual Wi-Fi adapters
- Guides user through connecting left and right adapters
- Automatic interface detection using hardware power switches
- Configurable adapter separation for triangulation accuracy
- Saves calibration to file for reuse
- `--skip-calibration` flag to use previous configuration
- 30-second timeout with automatic fallback to saved calibration

## Configuration

The HUD system supports modular hardware configuration through `config.py`. All hardware modules are optional and can be enabled/disabled based on your setup.

### Quick Start

1. Edit `config.py` to enable/disable services based on your hardware
2. Configure Wi-Fi interface names (use USB adapters, not onboard wireless)
3. Run `python main.py` to start the HUD
4. If using Wi-Fi locator, follow the interactive calibration workflow

### Configuration Options

Edit `config.py` to configure the HUD:

```python
HUD_CONFIG = {
    # Core Services
    "enable_system_metrics": True,    # CPU, RAM, temp, network monitoring
    
    # Optional Hardware Services
    "enable_gps": False,              # GPS tracking (requires USB GPS + gpsd)
    "enable_imu": False,              # IMU orientation (requires BNO085 via I2C)
    "enable_wifi_scanner": True,      # Wi-Fi scanning (requires USB adapter)
    "enable_wifi_locator": False,     # Direction finding (requires 2 USB adapters)
    "enable_audio": True,             # Audio visualizer (requires microphone)
    
    # Wi-Fi Interface Configuration
    # IMPORTANT: Use USB Wi-Fi adapters (wlan1, wlan2, wlx*), NOT onboard (wlan0)
    "wifi_scan_interface": "wlan1",       # Primary scanning interface
    "wifi_left_interface": "wlan1",       # Left adapter for direction finding
    "wifi_right_interface": "wlan2",      # Right adapter for direction finding
    "adapter_separation_m": 0.15,         # Physical distance between adapters (meters)
}
```

### Service Requirements

| Service | Hardware Required | Notes |
|---------|------------------|-------|
| **System Metrics** | None (built-in) | Always recommended |
| **GPS** | USB GPS receiver | Requires gpsd daemon running |
| **IMU** | BNO085 9-DOF IMU | Connected via I2C, overrides GPS heading |
| **Wi-Fi Scanner** | 1 USB Wi-Fi adapter | Use wlan1/wlan2, not onboard wlan0 |
| **Wi-Fi Locator** | 2 USB Wi-Fi adapters | Requires GPS or IMU for heading reference |
| **Audio** | Microphone/audio input | Any compatible audio device |

### Wi-Fi Interface Configuration

**Important**: Use USB Wi-Fi adapters for scanning and direction finding, NOT the onboard wireless interface.

To identify your Wi-Fi interfaces:
```bash
# List all network interfaces
ip link show

# Show wireless interfaces
iwconfig

# Verify USB Wi-Fi adapters are connected
lsusb

# Show detailed interface information
iw dev
```

Common interface names:
- `wlan0`, `wlp1s0`, `wlp*` - Onboard wireless (DO NOT USE for HUD)
- `wlan1`, `wlan2` - USB Wi-Fi adapters (RECOMMENDED)
- `wlx[mac_address]` - USB Wi-Fi adapters with MAC-based naming

### Calibration

When enabling Wi-Fi locator for the first time:

1. Run `python main.py` (without `--skip-calibration`)
2. Follow the interactive calibration workflow:
   - Disconnect both USB adapters
   - Connect RIGHT adapter when prompted
   - Connect LEFT adapter when prompted
   - Enter physical separation distance (typically 15-20cm for fursuit heads)
3. Calibration is saved to `.wifi_calibration.json` for future use

To skip calibration and use previous configuration:
```bash
python main.py --skip-calibration
```

### Graceful Degradation

The HUD is designed to work with any combination of available hardware:

- **Service disabled in config**: Service thread is not started
- **Hardware unavailable**: Service logs error and exits gracefully
- **Missing data**: Renderer displays "N/A" for unavailable data
- **System continues**: HUD operates with remaining functional services

This allows you to start with minimal hardware (just camera) and add sensors incrementally.

## Architecture Details

### Module Overview

```
main.py                 # Entry point, orchestration, calibration workflow
config.py               # Configuration system with validation
shared_state.py         # Thread-safe centralized data store
service_manager.py      # Service lifecycle coordinator
hud_renderer.py         # Unified rendering module for all HUD overlays
camera.py               # Camera stream handler
theme.py                # Neon color palette and visual styling
draw_utils.py           # Drawing utilities and helper functions

# Service Modules (Independent daemon threads)
system_metrics.py       # CPU, RAM, temperature, network monitoring
gps_tracker.py          # GPS data collection via gpsd
imu_tracker.py          # IMU orientation tracking via BNO085
wifi_scanner.py         # Wi-Fi scanning with device classification
wifi_locator.py         # Direction finding and triangulation
audio_service.py        # Audio capture and visualization
```

### Data Flow

1. **Service threads** collect data from hardware sensors
2. **Services write** to SharedState using thread-safe setters
3. **Main loop** calls `shared_state.get_snapshot()` to read all data atomically
4. **Renderer** receives snapshot and draws all HUD overlays
5. **Display** shows final composited frame

### Thread Safety

All data access is protected by threading locks in SharedState:
- Services write data independently without blocking each other
- Renderer reads complete snapshot in single lock acquisition
- No race conditions or data corruption
- Efficient lock usage minimizes contention

### RF Device Detection

The Wi-Fi scanner implements intelligent device classification:

**Classification Logic**:
- Analyzes SSID patterns for known drone manufacturers (DJI, Phantom, Mavic, Parrot, Autel)
- Considers frequency band (5.8GHz more likely drone)
- Evaluates channel selection patterns
- Defaults to "router" for standard Wi-Fi on common channels
- Falls back to "unknown" for unrecognized patterns

**Distance Estimation**:
- Uses path loss formula: `distance_m = 10^((27.55 - RSSI - freq_offset) / 20)`
- Frequency offset: 0 dB for 2.4GHz, 7.6 dB for 5.8GHz
- Transmit power assumptions: 20 dBm (routers), 27 dBm (drones)
- Triangulation refinement with dual adapters using weighted average

**Color Assignment**:
- Hash-based color assignment ensures consistency across sessions
- Same SSID always gets same color
- 12+ distinct colors in palette for visual distinction
- Two-layer visual system: type icons (white/gray) + individual colors (borders/accents)

## Installation

### System Dependencies

```bash
# Raspberry Pi / Debian-based systems
sudo apt-get update
sudo apt-get install python3 python3-pip
sudo apt-get install wireless-tools  # For iwlist
sudo apt-get install gpsd gpsd-clients  # For GPS (optional)
sudo apt-get install i2c-tools  # For IMU (optional)

# Enable I2C for IMU (Raspberry Pi)
sudo raspi-config  # Interface Options -> I2C -> Enable
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- opencv-python - Camera capture and rendering
- numpy - Numerical operations and FFT
- psutil - System metrics
- gpsd-py3 - GPS interface (optional)
- adafruit-circuitpython-bno08x - IMU interface (optional)
- sounddevice - Audio capture (optional)

### GPS Setup (Optional)

```bash
# Start gpsd daemon
sudo systemctl start gpsd
sudo systemctl enable gpsd

# Configure gpsd for your GPS device
sudo nano /etc/default/gpsd
# Set DEVICES="/dev/ttyUSB0" or your GPS device path
```

## Usage

### Basic Usage

```bash
# Run with default configuration
python main.py

# Skip Wi-Fi adapter calibration (use previous config)
python main.py --skip-calibration
```

### Controls

- **Q key**: Quit the HUD application
- **Fullscreen**: Automatically enabled on startup

### Troubleshooting

**Camera not detected**:
- Check USB connection: `lsusb`
- Verify camera device: `ls /dev/video*`
- Test with: `ffplay /dev/video0`

**Wi-Fi scanning fails**:
- Check interface exists: `ip link show`
- Verify wireless tools: `iwlist --version`
- Run with sudo if permission denied: `sudo python main.py`

**GPS not working**:
- Check gpsd status: `sudo systemctl status gpsd`
- Test GPS: `cgps -s` or `gpsmon`
- Verify device: `ls /dev/ttyUSB*` or `/dev/ttyACM*`

**IMU not detected**:
- Check I2C enabled: `ls /dev/i2c*`
- Scan I2C bus: `sudo i2cdetect -y 1`
- Verify BNO085 at address 0x4A or 0x4B

**Wi-Fi adapter calibration issues**:
- Ensure adapters have hardware power switches
- Try unplugging and replugging USB adapters
- Check USB enumeration: `dmesg | grep -i usb`
- Verify adapters recognized: `lsusb` and `iw dev`

## Performance

- **Target framerate**: 30 FPS at 1280x720
- **CPU usage**: ~30-50% on Raspberry Pi 5 (varies with enabled services)
- **RAM usage**: ~200-400 MB
- **Service update rates**:
  - System metrics: 1 second
  - GPS: 2-3 seconds
  - IMU: ~50 Hz (20ms)
  - Wi-Fi scanner: 15 seconds
  - Wi-Fi locator: 5 seconds
  - Audio: Real-time streaming

## Visual Design

All UI elements use a neon cyberpunk aesthetic with the following color palette:
- **Cyan/Teal**: Primary UI elements, borders, heading bar
- **Purple/Magenta**: Accent colors, highlights
- **Green**: Positive indicators, signal strength
- **Orange**: Warnings, medium priority
- **Pink**: High priority, alerts
- **Blue**: Information, secondary elements

Device-specific colors are assigned from a 12+ color palette for tracking individual RF devices across all display elements.

## Development

### Project Structure

The codebase follows a modular architecture with clear separation of concerns:
- **Configuration layer**: `config.py` with validation
- **State management**: `shared_state.py` with thread-safe operations
- **Service layer**: Independent service modules with daemon threads
- **Orchestration**: `service_manager.py` for lifecycle management
- **Rendering layer**: `hud_renderer.py` with all drawing logic
- **Application layer**: `main.py` for startup and main loop

### Adding New Services

1. Create service module (e.g., `new_service.py`)
2. Implement `start_new_service(shared_state, stop_event)` function
3. Add data fields to `SharedState` class
4. Add enable flag to `HUD_CONFIG` in `config.py`
5. Register service in `ServiceManager.start_all()`
6. Add rendering logic to `hud_renderer.py`

### Testing

See `TEST_QUICK_START.md` and `TESTING_SUMMARY.md` for comprehensive testing documentation.

## License

This project is provided as-is for educational and personal use.

## Acknowledgments

Built for the furry/protogen community with love for wearable tech and augmented reality displays.
