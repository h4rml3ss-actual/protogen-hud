# Design Document

## Overview

This design document describes the architecture for refactoring the Protogen HUD software into a fully modular, thread-safe system. The refactor transforms the current partially-modular codebase into a clean architecture where data collection services are completely decoupled from rendering, all shared state is managed through a thread-safe central store, and hardware modules can be enabled or disabled based on availability.

The design follows a producer-consumer pattern where multiple service threads collect data from various sources (GPS, IMU, Wi-Fi, system metrics) and write to a shared state manager, while the main rendering loop reads from this shared state to draw the HUD overlay.

**Key Design Principles:**
- Thread-safe data access using locks
- Clear separation between data collection and rendering
- Self-contained, independently testable modules
- Graceful degradation when hardware is unavailable
- Minimal changes to existing working components where possible

## Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Main Loop                            │
│  - Initialize SharedState                                    │
│  - Start CameraStream                                        │
│  - Start all ServiceThreads                                  │
│  - Read frame from CameraStream                              │
│  - Read data from SharedState                                │
│  - Call Renderer with frame + data                           │
│  - Display frame                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │         SharedState Manager              │
        │  (Thread-safe central data store)        │
        │  - GPS data                              │
        │  - IMU data                              │
        │  - System metrics                        │
        │  - Wi-Fi scan results                    │
        │  - Wi-Fi direction estimates             │
        │  - Audio buffer                          │
        └─────────────────────────────────────────┘
                    ▲                    │
                    │                    │
        ┌───────────┴────────┐          │
        │   Write (locked)   │          │  Read (locked)
        └───────────┬────────┘          │
                    │                    ▼
    ┌───────────────┴───────────────────────────────┐
    │          Service Threads                       │
    │  ┌──────────────────────────────────────────┐ │
    │  │  SystemMetricsService                    │ │
    │  │  - Collect CPU, RAM, Temp, Network       │ │
    │  └──────────────────────────────────────────┘ │
    │  ┌──────────────────────────────────────────┐ │
    │  │  GPSTrackerService                       │ │
    │  │  - Connect to gpsd                       │ │
    │  │  - Read lat/lon/speed/heading            │ │
    │  └──────────────────────────────────────────┘ │
    │  ┌──────────────────────────────────────────┐ │
    │  │  IMUTrackerService                       │ │
    │  │  - Connect to BNO085 via I2C             │ │
    │  │  - Read heading/pitch/roll               │ │
    │  └──────────────────────────────────────────┘ │
    │  ┌──────────────────────────────────────────┐ │
    │  │  WiFiScannerService                      │ │
    │  │  - Execute iwlist scan                   │ │
    │  │  - Parse SSID/signal/channel/security    │ │
    │  └──────────────────────────────────────────┘ │
    │  ┌──────────────────────────────────────────┐ │
    │  │  WiFiLocatorService                      │ │
    │  │  - Compare signal strength (dual adapters)│ │
    │  │  - Calculate direction estimate          │ │
    │  └──────────────────────────────────────────┘ │
    │  ┌──────────────────────────────────────────┐ │
    │  │  AudioService                            │ │
    │  │  - Capture microphone input              │ │
    │  │  - Compute FFT for visualizer            │ │
    │  └──────────────────────────────────────────┘ │
    └────────────────────────────────────────────────┘
```

### Data Flow

1. **Initialization Phase:**
   - Main creates SharedState instance
   - Main starts CameraStream thread
   - Main starts all enabled ServiceThreads via ServiceManager
   - Each ServiceThread begins its collection loop

2. **Runtime Phase:**
   - ServiceThreads continuously collect data and write to SharedState (with locks)
   - Main loop reads latest frame from CameraStream
   - Main loop reads current state snapshot from SharedState (with locks)
   - Main loop passes frame and state to Renderer
   - Renderer draws all HUD elements onto frame
   - Main loop displays frame via OpenCV

3. **Shutdown Phase:**
   - Main signals ServiceManager to stop all threads
   - Each ServiceThread checks stop_event and terminates gracefully
   - CameraStream stops and releases camera
   - OpenCV windows close

## Components and Interfaces

### 1. SharedState (shared_state.py)

**Purpose:** Thread-safe centralized storage for all HUD data.

**Interface:**
```python
class SharedState:
    def __init__(self):
        # Initialize all data fields and lock
        
    # GPS data
    def set_gps_data(self, lat, lon, speed, heading):
        # Thread-safe write
        
    def get_gps_data(self):
        # Thread-safe read, returns dict
        
    # IMU data
    def set_imu_data(self, heading, pitch, roll):
        # Thread-safe write
        
    def get_imu_data(self):
        # Thread-safe read, returns dict
        
    # System metrics
    def set_system_metrics(self, cpu, ram, temp, net_sent, net_recv):
        # Thread-safe write
        
    def get_system_metrics(self):
        # Thread-safe read, returns dict
        
    # Wi-Fi scan results
    def set_wifi_networks(self, networks):
        # Thread-safe write, networks is list of dicts
        
    def get_wifi_networks(self):
        # Thread-safe read, returns list
        
    # Wi-Fi direction estimates
    def set_wifi_direction(self, ssid, direction_deg, confidence):
        # Thread-safe write
        
    def get_wifi_directions(self):
        # Thread-safe read, returns dict
        
    # Audio buffer
    def set_audio_buffer(self, buffer):
        # Thread-safe write
        
    def get_audio_buffer(self):
        # Thread-safe read, returns numpy array
        
    # Get complete snapshot
    def get_snapshot(self):
        # Returns all data in single locked read
```

**Design Notes:**
- Uses `threading.Lock()` for all read/write operations
- Provides both granular accessors and snapshot method
- Initializes all fields with safe defaults (None, empty lists, etc.)
- Lock is acquired for minimal time to avoid blocking

### 2. CameraStream (camera.py)

**Status:** Already implemented and working well.

**Interface:**
```python
class CameraStream:
    def __init__(self, src=0, width=1280, height=720)
    def read(self) -> np.ndarray
    def stop(self)
```

**Design Notes:**
- No changes needed to existing implementation
- Already uses background thread for frame capture
- Already configured for MJPG codec and minimal buffering

### 3. SystemMetricsService (system_metrics.py)

**Purpose:** Collect system performance metrics in background thread.

**Interface:**
```python
def start_system_metrics_service(shared_state, stop_event):
    # Starts daemon thread that:
    # 1. Collects CPU, RAM, temp, network stats
    # 2. Writes to shared_state.set_system_metrics()
    # 3. Sleeps for 1 second
    # 4. Checks stop_event and exits if set
```

**Design Notes:**
- Refactors existing `metrics.py` into service pattern
- Keeps existing `psutil` usage for cross-platform compatibility
- Temperature reading uses platform-specific fallback:
  - Try `/sys/class/thermal/thermal_zone0/temp` (Linux)
  - Try `psutil.sensors_temperatures()` if available
  - Return "N/A" if both fail
- Network stats are cumulative; renderer can calculate deltas if needed

### 4. GPSTrackerService (gps_tracker.py)

**Status:** Mostly implemented, needs refactoring to use SharedState.

**Interface:**
```python
def start_gps_tracker_service(shared_state, stop_event):
    # Starts daemon thread that:
    # 1. Connects to gpsd
    # 2. Polls for TPV reports
    # 3. Writes lat/lon/speed/heading to shared_state
    # 4. Checks stop_event and exits if set
```

**Design Notes:**
- Remove global variables (gps_heading, latitude, longitude, speed)
- Move `draw_compass()` function to renderer module
- Check if IMU heading exists in SharedState before writing GPS heading
- Handle gpsd connection failures gracefully (log error, retry with backoff)

### 5. IMUTrackerService (imu_tracker.py)

**Purpose:** Read heading, pitch, roll from BNO085 IMU sensor.

**Interface:**
```python
def start_imu_tracker_service(shared_state, stop_event):
    # Starts daemon thread that:
    # 1. Initializes I2C connection to BNO085
    # 2. Configures sensor for rotation vector output
    # 3. Polls for sensor data
    # 4. Converts quaternion to Euler angles
    # 5. Writes heading/pitch/roll to shared_state
    # 6. Checks stop_event and exits if set
```

**Design Notes:**
- Uses `adafruit-circuitpython-bno08x` library
- I2C address typically 0x4A or 0x4B
- Heading takes priority over GPS heading in SharedState
- If sensor initialization fails, log error and exit thread gracefully
- Update rate: ~50Hz (20ms poll interval)

### 6. WiFiScannerService (wifi_scanner.py)

**Status:** Mostly implemented, needs refactoring to use SharedState and add device classification.

**Interface:**
```python
def start_wifi_scanner_service(shared_state, stop_event, interface="wlan0"):
    # Starts daemon thread that:
    # 1. Executes iwlist scan on specified interface
    # 2. Parses SSID, signal, channel, security
    # 3. Classifies device type based on signal characteristics
    # 4. Writes device list to shared_state
    # 5. Sleeps for scan interval (15 seconds)
    # 6. Checks stop_event and exits if set
```

**Design Notes:**
- Remove global variables and rotation logic (move to renderer)
- Keep existing parsing logic for iwlist output
- Support scanning multiple interfaces (wlan0, wlan1) if configured
- Handle scan failures gracefully (permissions, interface down, etc.)
- **Device Classification Algorithm:**
  - Routers: Typically have stable signal, common SSIDs, standard channels (1, 6, 11 for 2.4GHz)
  - Drones: Often use 5.8GHz, may have SSIDs containing "DJI", "Phantom", "Mavic", or be on non-standard channels
  - Unknown: Any device that doesn't match router or drone patterns
  - Classification based on:
    - SSID patterns (regex matching for known drone manufacturers)
    - Frequency band (5.8GHz more likely to be drone)
    - Channel selection (non-standard channels may indicate specialized equipment)
    - Signal behavior (rapid movement/changes may indicate mobile device)
- **Distance Estimation:**
  - Uses Free Space Path Loss (FSPL) formula: `distance = 10^((TxPower - RSSI - 20*log10(frequency)) / 20)`
  - Assumptions:
    - Typical router transmit power: 20 dBm (100mW)
    - Typical drone transmit power: 27 dBm (500mW) for 5.8GHz video
    - 2.4GHz frequency: 2437 MHz (channel 6 center)
    - 5.8GHz frequency: 5805 MHz (typical FPV drone frequency)
  - Simplified formula for 2.4GHz: `distance_m = 10^((27.55 - RSSI) / 20)`
  - Simplified formula for 5.8GHz: `distance_m = 10^((27.55 - RSSI - 7.6) / 20)`
  - Distance estimates are approximate due to:
    - Unknown actual transmit power
    - Environmental factors (walls, interference, multipath)
    - Antenna gain variations
  - Display with "~" prefix to indicate approximation (e.g., "~15m")

### 7. WiFiLocatorService (wifi_locator.py)

**Purpose:** Estimate direction and improved distance to RF devices using dual adapters.

**Interface:**
```python
def start_wifi_locator_service(shared_state, stop_event, 
                                left_interface="wlan0", 
                                right_interface="wlan1",
                                adapter_separation_m=0.15):
    # Starts daemon thread that:
    # 1. Reads Wi-Fi scan results from shared_state
    # 2. Reads current heading from shared_state
    # 3. Compares signal strength between left/right adapters
    # 4. Calculates direction estimate for each SSID
    # 5. Calculates improved distance using triangulation
    # 6. Writes direction and distance estimates to shared_state
    # 7. Sleeps for update interval (5 seconds)
    # 8. Checks stop_event and exits if set
```

**Design Notes:**
- Requires dual Wi-Fi adapters positioned left/right on device
- **Direction Algorithm:**
  - If left signal > right signal: AP is to the left
  - If right signal > right signal: AP is to the right
  - Combine with current heading to get absolute direction
  - Confidence based on signal strength differential
- **Triangulation Distance Algorithm:**
  - Given: adapter separation distance (d), signal strength at left (RSSI_L) and right (RSSI_R)
  - Calculate individual distances: `d_L = 10^((27.55 - RSSI_L) / 20)`, `d_R = 10^((27.55 - RSSI_R) / 20)`
  - Use law of cosines to find distance to target:
    - `angle = arccos((d_L² + d_R² - d²) / (2 * d_L * d_R))`
    - `distance = sqrt(d_L² - (d * sin(angle))²)`
  - Simplified approach: Average the two distance estimates weighted by signal strength
  - `distance_triangulated = (d_L * RSSI_R + d_R * RSSI_L) / (RSSI_L + RSSI_R)`
- **Distance Refinement:**
  - If only one adapter: use basic path loss distance
  - If dual adapters: use triangulation distance (more accurate)
  - Confidence increases with signal strength differential
- Only estimates for devices visible on both adapters
- **Configuration:**
  - `adapter_separation_m`: Physical distance between adapter antennas (default 0.15m / 6 inches)
  - Typical fursuit head width: 15-20cm, so 15cm is reasonable default

### 8. AudioService (audio_service.py)

**Status:** Mostly implemented in audio_visualizer.py, needs refactoring.

**Interface:**
```python
def start_audio_service(shared_state, stop_event):
    # Starts audio stream that:
    # 1. Captures microphone input via sounddevice
    # 2. Writes audio buffer to shared_state
    # 3. Optionally passes through to output device
    # Audio callback runs continuously until stop_event
```

**Design Notes:**
- Refactor existing `audio_visualizer.py` to separate service from rendering
- Service only captures audio and writes buffer to SharedState
- Move FFT computation and drawing to renderer
- Keep existing passthrough functionality (mic → speaker)
- Remove hardcoded WM8960 device search (use default or config)

### 9. Renderer (hud_renderer.py)

**Purpose:** Draw all HUD elements onto video frame.

**Interface:**
```python
def render_hud(frame, state_snapshot):
    # Draws all HUD elements:
    # - Heading readout bar (top center) - NEW
    # - System metrics (left side)
    # - GPS info and compass (left side, below metrics)
    # - RF device list (right side) - ENHANCED
    # - Audio visualizer (top center, below heading bar)
    # - RF direction indicators (overlay on compass) - ENHANCED
    # - RF event overlays (bottom left)
    # Returns: modified frame
```

**Design Notes:**
- Receives complete state snapshot (no global access)
- Uses existing `draw_utils.py` helper functions
- Uses existing `theme.py` color constants
- Incorporates existing RF overlay rendering from main.py
- Handles missing data gracefully (display "N/A" or skip element)
- RF device rotation logic moves here from scanner service
- Compass drawing moves here from gps_tracker.py
- Audio FFT computation and visualization moves here from audio_visualizer.py

**New Rendering Components:**

#### Heading Readout Bar
- **Position:** Top of screen, horizontal strip spanning ~80% of width
- **Layout:**
  - Center: Current heading in large digits (e.g., "045°")
  - Background: Horizontal degree scale showing ±60° range from current heading
  - Cardinal markers: N, E, S, W at appropriate positions
  - RF device icons: Positioned at their relative bearing on the scale
- **Visual Design:**
  - Semi-transparent dark background with neon border
  - Degree tick marks every 10°
  - Current heading highlighted with vertical indicator line
  - Device icons float above the scale with connecting lines
- **Icon Stacking:** When multiple devices are within 5° of each other:
  - Stack icons vertically above the scale
  - Draw thin connecting lines from each icon to its position on scale
  - Maintain color coding for each device type

#### Enhanced Compass Indicators
- **Device Type Icons:**
  - Router: WiFi symbol (standard waves icon)
  - Drone: Quadcopter silhouette icon
  - Unknown: Question mark or generic RF wave icon
  - Icons drawn in white/light gray
- **Individual Device Colors:**
  - Each device gets unique color from palette
  - Color applied as border around icon and connecting line
  - Same color used across all HUD elements for consistency
- **Label Stacking:** When devices are within 15° on compass:
  - Stack labels vertically outward from compass
  - Draw leader lines from label to position on compass ring (in device's unique color)
  - Use semi-transparent backgrounds for label readability
  - Prioritize closer/stronger signals at top of stack

#### Enhanced RF Device List
- **Position:** Upper right, vertical list
- **Per-Device Display:**
  - Device type icon (left) - white/light gray icon
  - Colored border/highlight around icon (device's unique color)
  - SSID/identifier (center-left)
  - Distance estimate (center-right, e.g., "~15m")
  - Signal strength bar or dBm value (right)
  - Channel number (small text below SSID)
  - Colored accent bar on left edge (device's unique color)
- **Rotation:** If more than 8 devices, rotate through list every 3 seconds
- **Grouping:** Optionally group by device type with section headers
- **Distance Display:**
  - Use meters for distances < 1000m (e.g., "~15m", "~250m")
  - Use kilometers for distances >= 1000m (e.g., "~1.2km")
  - Prefix with "~" to indicate approximation

### 10. ServiceManager (service_manager.py)

**Purpose:** Coordinate lifecycle of all service threads.

**Interface:**
```python
class ServiceManager:
    def __init__(self, shared_state, config):
        # Initialize with shared state and config dict
        
    def start_all(self):
        # Start all enabled services
        # Returns list of (service_name, stop_event) tuples
        
    def stop_all(self):
        # Signal all services to stop
        # Wait up to 5 seconds for graceful shutdown
```

**Design Notes:**
- Config dict specifies which services to enable:
  ```python
  config = {
      "enable_gps": True,
      "enable_imu": True,
      "enable_wifi_scanner": True,
      "enable_wifi_locator": True,
      
      # Wi-Fi interface configuration
      # IMPORTANT: Use USB adapter interfaces, NOT onboard wireless
      # Onboard wireless typically: wlan0 or wlp1s0
      # USB adapters typically: wlan1, wlan2, wlx[mac_address]
      # Use 'ip link show' or 'iwconfig' to identify USB adapters
      "wifi_scan_interface": "wlan1",      # Primary USB adapter for scanning
      "wifi_left_interface": "wlan1",      # Left USB adapter for direction finding
      "wifi_right_interface": "wlan2",     # Right USB adapter for direction finding
      
      # Adapter separation for triangulation (in meters)
      "adapter_separation_m": 0.15,        # 15cm / 6 inches typical
      
      # etc.
  }
  ```
- Tracks all started threads and their stop events
- Provides clean shutdown mechanism
- Logs service start/stop events
- **Interface Identification:**
  - Onboard wireless should be reserved for system connectivity
  - USB adapters can be identified by:
    - Interface names like wlan1, wlan2 (if onboard is wlan0)
    - Interface names starting with wlx (USB adapters often use MAC-based naming)
    - Using `lsusb` to verify USB Wi-Fi adapters are connected
    - Using `iw dev` to see which interfaces are USB-based

### 11. Main Orchestrator (main.py)

**Purpose:** Entry point that coordinates all components.

**Interface:**
```python
def main():
    # 1. Load configuration
    # 2. Initialize SharedState
    # 3. Initialize CameraStream
    # 4. Initialize and start ServiceManager
    # 5. Create OpenCV window
    # 6. Main loop:
    #    - Read frame
    #    - Get state snapshot
    #    - Render HUD
    #    - Display frame
    #    - Check for quit
    # 7. Cleanup on exit
```

**Design Notes:**
- Minimal logic in main loop (just coordination)
- Configuration can be hardcoded dict initially, move to file later
- Graceful shutdown on 'q' key or exception
- Logs startup sequence to startup.log
- Logs errors to error.log

## Data Models

### GPS Data
```python
{
    "latitude": float or None,
    "longitude": float or None,
    "speed": float or None,  # m/s
    "heading": float or None  # degrees, 0-360
}
```

### IMU Data
```python
{
    "heading": float or None,  # degrees, 0-360
    "pitch": float or None,    # degrees
    "roll": float or None      # degrees
}
```

### System Metrics
```python
{
    "cpu_percent": float,
    "ram_percent": float,
    "temp_celsius": float or "N/A",
    "net_sent_kb": float,
    "net_recv_kb": float
}
```

### RF Device (Enhanced Wi-Fi Network)
```python
{
    "ssid": str,
    "signal": str,         # e.g. "-45 dBm"
    "signal_dbm": int,     # numeric signal strength for comparison
    "channel": str,        # e.g. "6"
    "security": str,       # "Open" or "Secured"
    "device_type": str,    # "router", "drone", "unknown"
    "frequency": str,      # "2.4GHz" or "5.8GHz"
    "distance_m": float,   # estimated distance in meters
    "color": tuple         # (B, G, R) unique color for this device
}
```

### Wi-Fi Direction Estimate
```python
{
    "ssid": str,
    "direction_deg": float,  # absolute direction, 0-360
    "confidence": float      # 0.0-1.0
}
```

## Error Handling

### Service Thread Failures
- Each service thread wraps its main loop in try/except
- Exceptions are logged with traceback
- Thread exits gracefully rather than crashing entire application
- SharedState retains last known good values

### Hardware Unavailability
- If GPS hardware not found: GPS service exits, renderer shows "GPS: N/A"
- If IMU hardware not found: IMU service exits, falls back to GPS heading
- If Wi-Fi interface not found: Scanner service exits, renderer shows "Wi-Fi: N/A"
- If audio device not found: Audio service exits, visualizer not drawn

### Platform-Specific Code
- Temperature reading tries multiple methods, falls back to "N/A"
- I2C bus detection tries common paths (/dev/i2c-0, /dev/i2c-1)
- Network interface names may vary (wlan0, wlp2s0, etc.) - make configurable

## Testing Strategy

### Unit Testing
- **SharedState:** Test thread-safe read/write operations, verify locking
- **Service Functions:** Test data parsing logic in isolation (mock hardware)
- **Renderer:** Test drawing functions with mock state data
- **ServiceManager:** Test start/stop coordination

### Integration Testing
- **Service → SharedState:** Verify each service correctly writes to SharedState
- **SharedState → Renderer:** Verify renderer correctly reads and displays data
- **Full System:** Run with all services enabled, verify no deadlocks or crashes

### Hardware Testing
- Test on LattePanda Alpha with actual hardware
- Test with missing hardware (IMU disconnected, GPS unplugged, etc.)
- Verify graceful degradation

### Performance Testing
- Monitor CPU usage with all services running
- Verify frame rate stays at target 30 FPS
- Check for memory leaks during extended runtime
- Profile lock contention in SharedState

## Visual Design Specifications

### Color Scheme Design

**Two-Layer Visual System:**
1. **Device Type Icons** - Consistent icon per type (router, drone, unknown)
2. **Individual Device Colors** - Unique color per device for tracking

### Device Type Icons
Each device type has a distinct icon shape that remains consistent:
- **Router:** WiFi waves symbol (📶 style)
- **Drone:** Quadcopter silhouette with 4 propellers
- **Unknown:** Question mark or generic RF wave pattern

### Individual Device Color Assignment
Each detected device gets a unique color from a palette:
```python
# Color palette for individual devices (HSV-based for variety)
DEVICE_COLOR_PALETTE = [
    (0, 255, 255),      # Cyan
    (255, 100, 255),    # Magenta
    (0, 255, 100),      # Green
    (100, 255, 255),    # Yellow
    (255, 150, 100),    # Orange
    (200, 100, 255),    # Purple
    (50, 255, 200),     # Lime
    (255, 200, 100),    # Amber
    (150, 255, 255),    # Light Blue
    (255, 100, 150),    # Pink
    (100, 255, 150),    # Mint
    (200, 255, 100),    # Yellow-Green
]

# Color assignment strategy
def assign_device_color(ssid, device_list):
    # Use hash of SSID to consistently assign same color to same device
    # Cycle through palette if more devices than colors
    color_index = hash(ssid) % len(DEVICE_COLOR_PALETTE)
    return DEVICE_COLOR_PALETTE[color_index]
```

### Visual Application
- **Icon:** Drawn in white or light gray (consistent across all devices of same type)
- **Color Border/Highlight:** Unique color per device applied as:
  - Border around icon
  - Background glow/highlight
  - Connecting line color
  - Label background tint

**Example:**
- Router A (SSID: "HomeNet"): Router icon with cyan border
- Router B (SSID: "OfficeWiFi"): Router icon with magenta border  
- Drone A (SSID: "DJI-Mavic"): Drone icon with green border
- Drone B (SSID: "DJI-Phantom"): Drone icon with yellow border

This allows you to:
1. Quickly identify device type by icon shape
2. Track individual devices by their unique color
3. See the same device across all HUD elements (heading bar, compass, list)

### Heading Readout Bar Specifications
- **Height:** 60 pixels
- **Width:** 80% of frame width, centered
- **Background:** Semi-transparent black (alpha 0.7)
- **Border:** 2px neon cyan
- **Degree Scale:**
  - Range: Current heading ±60° (120° total visible)
  - Major ticks every 10°, minor ticks every 5°
  - Tick height: 10px (major), 5px (minor)
- **Current Heading Indicator:**
  - Vertical line at center, full height of bar
  - Width: 3px, color: bright cyan
  - Digital readout: 48pt font, centered above line
- **Device Icons:**
  - Size: 24x24 pixels
  - Position: Floating 10px above scale
  - Stacking offset: 30px vertical spacing when stacked

### Compass Enhancement Specifications
- **Compass Radius:** 100 pixels (existing)
- **Device Indicator:**
  - Icon size: 20x20 pixels
  - Position: On compass ring at calculated bearing
  - Label: SSID text, 12pt font
  - Label background: Semi-transparent black
  - Leader line: 1px, device type color
- **Stacking:**
  - Vertical offset: 25px per stacked item
  - Maximum stack height: 4 items (then rotate)

## Wi-Fi Adapter Startup Calibration

### Purpose
Detect which USB Wi-Fi adapter is on the left vs right side during application startup by having the user connect them one at a time using hardware power switches.

### Design Rationale
- USB device enumeration (wlan1, wlan2) can change between reboots
- Using hardware power switches allows reliable detection each startup
- No need for persistent configuration that could become stale
- Simple user workflow: connect right, then connect left

### Hardware Setup
- Two USB Wi-Fi adapters with inline power switches (or USB hub with per-port power control)
- Adapters physically mounted on left and right sides of device
- Power switches accessible during startup

### Calibration Workflow
```python
# In main.py startup sequence
def calibrate_wifi_adapters():
    print("=== Wi-Fi Adapter Calibration ===")
    print("Make sure BOTH adapters are DISCONNECTED (switches OFF)")
    input("Press Enter when ready...")
    
    # Get baseline interfaces (onboard wireless only)
    baseline_interfaces = get_wifi_interfaces()
    
    print("\n1. Connect the RIGHT adapter (switch ON)")
    input("Press Enter when connected...")
    time.sleep(2)  # Wait for USB enumeration
    
    # Detect new interface
    current_interfaces = get_wifi_interfaces()
    right_interface = find_new_interface(baseline_interfaces, current_interfaces)
    print(f"   Detected RIGHT adapter: {right_interface}")
    
    print("\n2. Connect the LEFT adapter (switch ON)")
    input("Press Enter when connected...")
    time.sleep(2)
    
    # Detect new interface
    current_interfaces = get_wifi_interfaces()
    left_interface = find_new_interface(baseline_interfaces + [right_interface], current_interfaces)
    print(f"   Detected LEFT adapter: {left_interface}")
    
    print(f"\n=== Calibration Complete ===")
    print(f"RIGHT: {right_interface}")
    print(f"LEFT:  {left_interface}")
    
    # Prompt for adapter separation
    separation = input("Enter adapter separation in cm (default 15): ") or "15"
    adapter_separation_m = float(separation) / 100.0
    
    return {
        "wifi_left_interface": left_interface,
        "wifi_right_interface": right_interface,
        "wifi_scan_interface": left_interface,  # Use left for primary scanning
        "adapter_separation_m": adapter_separation_m
    }

def get_wifi_interfaces():
    # Use 'iw dev' to list wireless interfaces
    # Filter out onboard wireless (wlan0, wlp1s0)
    # Return list of USB adapter interface names
    
def find_new_interface(old_list, new_list):
    # Return the interface that appears in new_list but not old_list
```

### User Experience
1. Application starts
2. Prompt: "Make sure BOTH adapters are DISCONNECTED"
3. User turns off both power switches
4. User presses Enter
5. Prompt: "Connect the RIGHT adapter"
6. User turns on right power switch
7. User presses Enter
8. System detects right adapter interface (e.g., wlan1)
9. Prompt: "Connect the LEFT adapter"
10. User turns on left power switch
11. User presses Enter
12. System detects left adapter interface (e.g., wlan2)
13. Prompt: "Enter adapter separation in cm (default 15)"
14. User enters separation or presses Enter for default
15. Calibration complete, HUD starts normally

### Optional: Skip Calibration
- Add command-line flag: `--skip-calibration`
- Use last known configuration from previous run (stored in memory/temp file)
- Useful for quick restarts during development

## Migration Strategy

The refactor will be implemented incrementally to minimize risk:

1. **Phase 1:** Create SharedState and ServiceManager infrastructure
2. **Phase 2:** Refactor SystemMetricsService to use SharedState
3. **Phase 3:** Refactor GPSTrackerService to use SharedState
4. **Phase 4:** Create IMUTrackerService (new functionality)
5. **Phase 5:** Refactor WiFiScannerService to use SharedState
6. **Phase 6:** Create WiFiLocatorService (new functionality)
7. **Phase 7:** Refactor AudioService to use SharedState
8. **Phase 8:** Refactor Renderer to use state snapshot
9. **Phase 9:** Update main.py to use new architecture
10. **Phase 10:** Testing and refinement
11. **Phase 11:** Add RF device classification to WiFiScannerService
12. **Phase 12:** Implement heading readout bar in Renderer
13. **Phase 13:** Enhance compass indicators with stacking and device types
14. **Phase 14:** Update RF device list display with device type icons and colors
15. **Phase 15:** Create Wi-Fi adapter configuration utility

Each phase can be tested independently before proceeding to the next.
