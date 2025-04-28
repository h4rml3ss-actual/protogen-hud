# Protogen HUD - Phase 1 Design Document

## Overview

This document outlines the design specifications and hardware/software considerations for Phase 1 of the Protogen HUD project. The system is intended to run on a dedicated Raspberry Pi 5 and provide a real-time augmented display overlay via a wearable HDMI device.

## System Considerations

- **Security:** All code must follow security best practices and avoid introducing known vulnerabilities.
- **Resource Usage:** Optimize CPU, GPU, and RAM usage for best performance.
- **System Environment:** Application should ideally operate without a full desktop environment (headless), if feasible.
- **Layout Strategy:** Widgets will be positioned along the left, top, and right sides of the screen in a stacked grid.

## Hardware Specifications

- **Compute:** Raspberry Pi 5 (8GB RAM) with M.2 Hat and SSD
- **Audio:** WM8960 Sound Card (Audio Hat)
- **Display:** VuFine Wearable Display (1280x720 HDMI)
- **Microphone:** USB-C Conference Microphone
- **Camera:** Arducam USB IR Camera (1080p, automatic IR switching, MJPG output)
- **GPS:** Stratux vk-162 USB GPS Dongle

## Feature Set

### ✅ Camera Feed
- Fullscreen display of the USB camera feed.
- Target framerate: 30 FPS at 1280x720 (MJPG).
- Prioritize smooth rendering using hardware acceleration where available.

### ✅ System Metrics Widget
- Data points: CPU usage, CPU temp, RAM usage, GPU usage, GPU temp, network in/out, disk I/O activity.
- Updates periodically (not real-time).
- Positioned on the left.

### ✅ Wi-Fi Scanner Widget
- Lists visible Wi-Fi networks, including hidden SSIDs.
- Displays: SSID, signal strength, channel, security status (secured/unsecured).
- Rotates through entries; updates infrequently for performance.
- Positioned on the right.

### ✅ Audio Visualizer Widget
- Circular audio level display with waveform in the center.
- Updates more than once per second.
- Balanced for performance (not real-time).
- Positioned at the top center.

### ✅ Compass and GPS Widget
- Displays: compass heading, GPS coordinates (lat/lon), and speed.
- Updates every few seconds.
- Positioned on the left side under system metrics.

### 🔄 Gesture Controls (Planned)
- Uses hand gesture recognition to trigger actions:
  - Take picture
  - Record video
  - Adjust volume (up/down)
- Must account for user wearing gloves with altered hand shape.

## Notes

- Final system should operate fully offline, with local processing only.
- All UI elements must reflect the HUD's neon visual aesthetic (purple, green, orange, pink, blue).
- Performance optimizations will be guided by profiling during development.

@end Phase 1
