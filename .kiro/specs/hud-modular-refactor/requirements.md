# Requirements Document

## Introduction

This document specifies the requirements for refactoring the Protogen HUD software from its current partially-modular state into a fully modular, thread-safe, and scalable architecture. The refactor will enable plug-and-play hardware modules (IMU, GPS, Wi-Fi direction finding), improve maintainability, and decouple rendering from data collection while maintaining the existing feature set and visual aesthetic.

**Target Platform:** LattePanda Alpha (x86-64 architecture) running Linux. The architecture is designed to be hardware-agnostic where possible, with platform-specific code isolated to individual service modules.

## Glossary

- **HUD System**: The complete Protogen heads-up display software running on Raspberry Pi 5
- **Shared State Manager**: A thread-safe centralized data store for all HUD variables
- **Service Thread**: A background thread responsible for collecting data from a specific hardware or software source
- **Renderer**: The component responsible for drawing all visual elements onto video frames
- **Camera Stream**: The threaded video capture component providing frames to the main loop
- **IMU**: Inertial Measurement Unit (BNO085) providing heading, pitch, and roll data
- **Wi-Fi Locator**: A component that estimates signal direction using dual Wi-Fi adapters and heading data
- **GPSD**: GPS daemon service providing location and heading data from USB GPS hardware
- **Platform-Specific Code**: Code that depends on specific hardware interfaces or system calls that may vary between ARM and x86 platforms
- **Audio Visualizer**: Component that processes microphone input and displays waveform visualization on the HUD
- **Heading Readout Bar**: A horizontal strip display at the top of the HUD showing directional information and RF signal indicators
- **RF Device**: Any radio frequency emitting device on 2.4GHz or 5.8GHz bands, including Wi-Fi routers, drones, and other wireless devices
- **Device Classification**: The process of identifying RF device types based on signal characteristics and behavior patterns

## Requirements

### Requirement 1: Shared State Management

**User Story:** As a developer, I want all HUD data stored in a thread-safe centralized location, so that multiple service threads can update data without race conditions or data corruption.

#### Acceptance Criteria

1. THE HUD System SHALL provide a Shared State Manager class that stores all HUD variables
2. WHEN any Service Thread writes data, THE Shared State Manager SHALL use threading locks to prevent concurrent access conflicts
3. THE Shared State Manager SHALL store GPS data including latitude, longitude, speed, and heading
4. THE Shared State Manager SHALL store IMU data including heading, pitch, and roll
5. THE Shared State Manager SHALL store system metrics including CPU usage, RAM usage, temperature, and network statistics
6. THE Shared State Manager SHALL store Wi-Fi scan results including SSID, signal strength, channel, and security information
7. THE Shared State Manager SHALL store Wi-Fi direction estimation data
8. THE Shared State Manager SHALL provide thread-safe read methods for accessing stored data
9. THE Shared State Manager SHALL provide thread-safe write methods for updating stored data

### Requirement 2: System Metrics Service

**User Story:** As a user, I want to see real-time system performance metrics on my HUD, so that I can monitor the health and resource usage of my device.

#### Acceptance Criteria

1. THE HUD System SHALL provide a System Metrics Service that runs as a background Service Thread
2. THE System Metrics Service SHALL collect CPU usage percentage
3. THE System Metrics Service SHALL collect RAM usage percentage
4. THE System Metrics Service SHALL collect CPU temperature in degrees Celsius using platform-appropriate methods
5. THE System Metrics Service SHALL collect network bytes sent and received
6. IF platform-specific temperature reading fails, THEN THE System Metrics Service SHALL display a not-available indicator
7. WHEN the System Metrics Service collects new data, THE System Metrics Service SHALL write the data to the Shared State Manager
8. THE System Metrics Service SHALL update metrics at intervals no less than one second

### Requirement 3: GPS Tracking Service

**User Story:** As a user, I want to see my current location, heading, and speed on the HUD, so that I have situational awareness while moving.

#### Acceptance Criteria

1. THE HUD System SHALL provide a GPS Tracking Service that runs as a background Service Thread
2. THE GPS Tracking Service SHALL connect to GPSD to retrieve GPS data
3. THE GPS Tracking Service SHALL collect latitude coordinates
4. THE GPS Tracking Service SHALL collect longitude coordinates
5. THE GPS Tracking Service SHALL collect speed in meters per second
6. THE GPS Tracking Service SHALL collect heading in degrees
7. WHEN the GPS Tracking Service receives new GPS data, THE GPS Tracking Service SHALL write the data to the Shared State Manager
8. IF IMU data is available in the Shared State Manager, THEN THE GPS Tracking Service SHALL NOT override the heading value

### Requirement 4: IMU Tracking Service

**User Story:** As a user, I want accurate heading information from an IMU sensor, so that my compass display is responsive and accurate even when stationary.

#### Acceptance Criteria

1. THE HUD System SHALL provide an IMU Tracking Service that runs as a background Service Thread
2. THE IMU Tracking Service SHALL connect to the BNO085 sensor via I2C
3. THE IMU Tracking Service SHALL collect heading data in degrees
4. THE IMU Tracking Service SHALL collect pitch data in degrees
5. THE IMU Tracking Service SHALL collect roll data in degrees
6. WHEN the IMU Tracking Service receives valid sensor data, THE IMU Tracking Service SHALL write the data to the Shared State Manager
7. THE IMU Tracking Service SHALL take priority over GPS heading data

### Requirement 5: Wi-Fi Scanning Service

**User Story:** As a user, I want to see nearby Wi-Fi networks and their properties on my HUD, so that I can identify available networks and their signal strength.

#### Acceptance Criteria

1. THE HUD System SHALL provide a Wi-Fi Scanning Service that runs as a background Service Thread
2. THE Wi-Fi Scanning Service SHALL execute system commands to scan for Wi-Fi networks
3. THE Wi-Fi Scanning Service SHALL parse SSID from scan results
4. THE Wi-Fi Scanning Service SHALL parse signal strength in dBm from scan results
5. THE Wi-Fi Scanning Service SHALL parse channel number from scan results
6. THE Wi-Fi Scanning Service SHALL parse security status from scan results
7. WHEN the Wi-Fi Scanning Service completes a scan, THE Wi-Fi Scanning Service SHALL write the results to the Shared State Manager
8. THE Wi-Fi Scanning Service SHALL perform scans at intervals no less than ten seconds

### Requirement 6: Wi-Fi Direction Finding Service

**User Story:** As a user, I want to see the estimated direction of Wi-Fi signals on my HUD, so that I can locate the physical position of access points.

#### Acceptance Criteria

1. THE HUD System SHALL provide a Wi-Fi Locator Service that runs as a background Service Thread
2. THE Wi-Fi Locator Service SHALL compare signal strength between multiple Wi-Fi adapters
3. THE Wi-Fi Locator Service SHALL retrieve current heading from the Shared State Manager
4. THE Wi-Fi Locator Service SHALL calculate estimated signal direction based on signal strength differential and heading
5. WHEN the Wi-Fi Locator Service calculates a direction estimate, THE Wi-Fi Locator Service SHALL write the direction data to the Shared State Manager

### Requirement 7: Modular Rendering System

**User Story:** As a developer, I want all rendering logic separated from data collection, so that I can modify visual elements without affecting data gathering services.

#### Acceptance Criteria

1. THE HUD System SHALL provide a Renderer component that handles all OpenCV drawing operations
2. THE Renderer SHALL receive frame data and state data as function parameters
3. THE Renderer SHALL NOT access global variables for HUD data
4. THE Renderer SHALL draw system metrics using data from the Shared State Manager
5. THE Renderer SHALL draw GPS information using data from the Shared State Manager
6. THE Renderer SHALL draw compass visualization using heading data from the Shared State Manager
7. THE Renderer SHALL draw Wi-Fi network list using data from the Shared State Manager
8. THE Renderer SHALL draw audio visualizer using audio data
9. THE Renderer SHALL draw RF event overlays using queued event data
10. THE Renderer SHALL apply the neon color theme to all visual elements

### Requirement 8: Main Orchestration

**User Story:** As a developer, I want a clean main entry point that coordinates all services, so that the system startup and shutdown process is clear and maintainable.

#### Acceptance Criteria

1. THE HUD System SHALL provide a main orchestration module as the entry point
2. THE main orchestration module SHALL initialize the Shared State Manager
3. THE main orchestration module SHALL start the Camera Stream
4. THE main orchestration module SHALL start all Service Threads
5. THE main orchestration module SHALL create the OpenCV display window
6. WHEN the main loop executes, THE main orchestration module SHALL read the latest frame from the Camera Stream
7. WHEN the main loop executes, THE main orchestration module SHALL read current state from the Shared State Manager
8. WHEN the main loop executes, THE main orchestration module SHALL pass frame and state data to the Renderer
9. WHEN the main loop executes, THE main orchestration module SHALL display the rendered frame
10. WHEN shutdown is requested, THE main orchestration module SHALL stop all Service Threads gracefully
11. WHEN shutdown is requested, THE main orchestration module SHALL stop the Camera Stream
12. WHEN shutdown is requested, THE main orchestration module SHALL close all OpenCV windows

### Requirement 9: Service Lifecycle Management

**User Story:** As a developer, I want consistent service startup and shutdown patterns, so that all background threads can be managed reliably.

#### Acceptance Criteria

1. THE HUD System SHALL provide a service management module for coordinating Service Thread lifecycle
2. THE service management module SHALL start all configured Service Threads during initialization
3. THE service management module SHALL provide stop signals to all Service Threads during shutdown
4. WHEN a Service Thread is started, THE Service Thread SHALL run as a daemon thread
5. WHEN a Service Thread receives a stop signal, THE Service Thread SHALL terminate gracefully within five seconds

### Requirement 10: Configuration and Modularity

**User Story:** As a user, I want to enable or disable hardware modules based on my setup, so that the HUD works correctly whether or not I have IMU, GPS, or dual Wi-Fi adapters installed.

#### Acceptance Criteria

1. THE HUD System SHALL support optional hardware modules
2. THE HUD System SHALL allow the IMU Tracking Service to be disabled if IMU hardware is not present
3. THE HUD System SHALL allow the GPS Tracking Service to be disabled if GPS hardware is not present
4. THE HUD System SHALL allow the Wi-Fi Locator Service to be disabled if dual Wi-Fi adapters are not present
5. WHEN a Service Thread for optional hardware is disabled, THE HUD System SHALL continue operating with remaining services
6. THE Renderer SHALL display placeholder text for data from disabled services

### Requirement 11: RF Device Detection and Classification

**User Story:** As a user, I want to detect and identify different types of RF devices on 2.4GHz and 5.8GHz bands, so that I can distinguish between routers, drones, and other wireless devices on my HUD.

#### Acceptance Criteria

1. THE HUD System SHALL detect RF devices operating on 2.4GHz frequency bands
2. THE HUD System SHALL detect RF devices operating on 5.8GHz frequency bands
3. THE Wi-Fi Scanning Service SHALL classify detected devices into categories including routers, drones, and unknown devices
4. THE Wi-Fi Scanning Service SHALL use signal characteristics to determine device type classification
5. WHEN the Wi-Fi Scanning Service detects a device, THE Wi-Fi Scanning Service SHALL store the device type classification in the Shared State Manager
6. THE Shared State Manager SHALL store device type information for each detected RF device
7. THE HUD System SHALL assign distinct visual identifiers for each device type category
8. THE HUD System SHALL assign unique colors to each individual detected RF device
9. THE HUD System SHALL maintain consistent color assignment for each device across all display elements

### Requirement 12: Heading Readout Bar Display

**User Story:** As a user, I want a horizontal heading readout bar at the top of my HUD showing my current direction and RF signal locations, so that I have an intuitive sci-fi style directional awareness display.

#### Acceptance Criteria

1. THE Renderer SHALL draw a Heading Readout Bar as a horizontal strip at the top of the display
2. THE Heading Readout Bar SHALL display a range of compass degrees centered on the current heading
3. THE Heading Readout Bar SHALL display the current heading value in degrees
4. THE Heading Readout Bar SHALL display cardinal direction indicators for North, South, East, and West
5. THE Heading Readout Bar SHALL display icons representing detected RF devices at their relative directional positions
6. WHEN multiple RF devices are detected in close proximity, THE Heading Readout Bar SHALL stack device icons vertically to prevent overlap
7. THE Heading Readout Bar SHALL use device type icons that are consistent for each device type
8. THE Heading Readout Bar SHALL use unique colors for each individual RF device
9. THE Heading Readout Bar SHALL update in real-time as heading changes

### Requirement 13: Enhanced Compass Indicators

**User Story:** As a user, I want clear and distinct indicators on the compass for each detected RF device, so that I can easily identify individual signals even when they are close together.

#### Acceptance Criteria

1. THE Renderer SHALL draw distinct visual indicators on the compass for each detected RF device
2. THE Renderer SHALL use device type icons that are consistent for each device type on the compass display
3. WHEN multiple RF devices are detected in close directional proximity, THE Renderer SHALL stack indicator labels vertically
4. THE Renderer SHALL use unique colors for each individual RF device on compass indicators
5. THE compass indicators SHALL display device identification information including SSID or device identifier
6. THE compass indicators SHALL remain readable when multiple devices are displayed simultaneously

### Requirement 14: Enhanced RF Device List Display

**User Story:** As a user, I want the RF device list to show all detected devices with their types and properties, so that I have complete awareness of the RF environment around me.

#### Acceptance Criteria

1. THE Renderer SHALL display a list of all detected RF devices in the upper right area of the HUD
2. THE RF device list SHALL display device type icons for each detected device
3. THE RF device list SHALL display SSID or device identifier for each detected device
4. THE RF device list SHALL display signal strength for each detected device
5. THE RF device list SHALL display channel information for each detected device
6. THE RF device list SHALL use device type icons to distinguish between routers, drones, and unknown devices
7. THE RF device list SHALL use unique colors for each individual RF device
8. WHEN the list contains more devices than can fit on screen, THE RF device list SHALL rotate through devices at regular intervals

### Requirement 15: RF Device Distance Estimation

**User Story:** As a user, I want to see estimated distances to detected RF devices, so that I can gauge how far away routers, drones, and other devices are from my position.

#### Acceptance Criteria

1. THE Wi-Fi Scanning Service SHALL calculate estimated distance for each detected RF device based on signal strength
2. THE Wi-Fi Scanning Service SHALL use the path loss formula to convert signal strength to distance estimate
3. THE Wi-Fi Scanning Service SHALL account for frequency band differences in distance calculations
4. WHERE dual Wi-Fi adapters are available, THE Wi-Fi Locator Service SHALL use triangulation to improve distance accuracy
5. THE Wi-Fi Locator Service SHALL calculate distance using signal strength differential and known adapter separation
6. THE Wi-Fi Locator Service SHALL combine path loss distance with triangulation distance for improved estimates
7. THE Shared State Manager SHALL store distance estimates in meters
8. THE Renderer SHALL display distance estimates on the RF device list
9. THE Renderer SHALL display distance estimates on compass indicators
10. THE Renderer SHALL display distance estimates on the heading readout bar
11. THE distance estimates SHALL be displayed with appropriate units (meters for close range, kilometers for far range)
12. THE HUD System SHALL indicate that distance estimates are approximate

### Requirement 16: Wi-Fi Adapter Configuration and Calibration

**User Story:** As a user, I want an easy way to identify which USB Wi-Fi adapter is on the left vs right side during startup, so that direction finding works correctly even if USB enumeration changes between reboots.

#### Acceptance Criteria

1. THE HUD System SHALL perform adapter calibration during application startup
2. WHEN calibration starts, THE HUD System SHALL prompt the user to connect only the right adapter
3. THE HUD System SHALL detect which interface appears when the right adapter is connected
4. THE HUD System SHALL prompt the user to connect the left adapter
5. THE HUD System SHALL detect which interface appears when the left adapter is connected
6. THE HUD System SHALL save the detected interface mappings for the current session
7. THE HUD System SHALL display the detected interface names to the user for confirmation
8. THE HUD System SHALL allow the user to skip calibration and use previous configuration
9. THE HUD System SHALL support hardware power switches for easy adapter connection control
