"""
hud_renderer.py
---------------
Unified renderer module for the Protogen HUD.
Consolidates all drawing logic into a single render_hud() function that takes
a frame and state snapshot, then renders all HUD elements.
"""

import cv2
import math
import numpy as np
import threading
from collections import deque
from draw_utils import draw_text, draw_bar
from theme import (
    NEON_PINK, NEON_GREEN, NEON_ORANGE, NEON_BLUE, NEON_PURPLE,
    CENTER, RADIUS, FONT, FONT_SCALE, THICKNESS, assign_device_color
)

# Thread-safe queues for RF overlay events
_signal_events = deque()
_scan_updates = deque()
_message_events = deque()
_rf_lock = threading.Lock()

# Wi-Fi network rotation state
_wifi_rotation_index = 0
_wifi_rotation_lock = threading.Lock()


def _draw_router_icon(frame, center, size=24, color=(200, 200, 200)):
    """
    Draw a router icon (WiFi waves symbol).
    
    Args:
        frame: OpenCV frame to draw on
        center: Tuple (x, y) for icon center
        size: Icon size in pixels
        color: Icon color in BGR format
    """
    x, y = center
    half = size // 2
    
    # Draw router base (small rectangle)
    cv2.rectangle(frame, (x - half//2, y + half//3), (x + half//2, y + half//2), color, -1)
    
    # Draw WiFi waves (3 arcs)
    for i in range(1, 4):
        radius = half // 3 * i
        cv2.ellipse(frame, (x, y), (radius, radius), 0, 180, 360, color, 1)


def _draw_drone_icon(frame, center, size=24, color=(200, 200, 200)):
    """
    Draw a drone icon (quadcopter silhouette).
    
    Args:
        frame: OpenCV frame to draw on
        center: Tuple (x, y) for icon center
        size: Icon size in pixels
        color: Icon color in BGR format
    """
    x, y = center
    half = size // 2
    quarter = size // 4
    
    # Draw center body (small circle)
    cv2.circle(frame, (x, y), quarter // 2, color, -1)
    
    # Draw four arms and propellers
    arm_positions = [
        (x - half, y - half),  # Top-left
        (x + half, y - half),  # Top-right
        (x - half, y + half),  # Bottom-left
        (x + half, y + half)   # Bottom-right
    ]
    
    for arm_x, arm_y in arm_positions:
        # Draw arm line
        cv2.line(frame, (x, y), (arm_x, arm_y), color, 1)
        # Draw propeller (small circle)
        cv2.circle(frame, (arm_x, arm_y), quarter // 2, color, 1)


def _draw_unknown_icon(frame, center, size=24, color=(200, 200, 200)):
    """
    Draw an unknown device icon (question mark or RF waves).
    
    Args:
        frame: OpenCV frame to draw on
        center: Tuple (x, y) for icon center
        size: Icon size in pixels
        color: Icon color in BGR format
    """
    x, y = center
    half = size // 2
    
    # Draw RF wave pattern (concentric circles)
    for i in range(1, 4):
        radius = half // 3 * i
        cv2.circle(frame, (x, y), radius, color, 1)
    
    # Draw center dot
    cv2.circle(frame, (x, y), 2, color, -1)


def _draw_device_icon(frame, center, device_type, size=24, icon_color=(200, 200, 200), border_color=None):
    """
    Draw a device type icon with optional colored border.
    
    Args:
        frame: OpenCV frame to draw on
        center: Tuple (x, y) for icon center
        device_type: Type of device ("router", "drone", "unknown")
        size: Icon size in pixels
        icon_color: Icon color in BGR format (white/light gray)
        border_color: Optional border color in BGR format (device's unique color)
    """
    # Draw colored border/highlight if provided
    if border_color:
        # Draw a colored circle behind the icon
        cv2.circle(frame, center, size // 2 + 3, border_color, 2)
    
    # Draw the appropriate icon
    if device_type == "router":
        _draw_router_icon(frame, center, size, icon_color)
    elif device_type == "drone":
        _draw_drone_icon(frame, center, size, icon_color)
    else:
        _draw_unknown_icon(frame, center, size, icon_color)


def _normalize_angle(angle):
    """Normalize angle to 0-360 range."""
    while angle < 0:
        angle += 360
    while angle >= 360:
        angle -= 360
    return angle


def _draw_heading_bar(frame, heading, rf_devices, wifi_directions):
    """
    Draw heading readout bar at the top of the frame.
    
    Args:
        frame: OpenCV frame to draw on
        heading: Current heading in degrees (0-360), or None
        rf_devices: List of RF device dictionaries with device_type, distance_m, color, ssid
        wifi_directions: Dictionary of SSID -> {direction_deg, confidence}
    """
    if heading is None:
        heading = 0  # Default to north if no heading available
    
    frame_height, frame_width = frame.shape[:2]
    
    # Bar dimensions
    bar_height = 60
    bar_width = int(frame_width * 0.8)
    bar_x = (frame_width - bar_width) // 2
    bar_y = 10
    
    # Draw semi-transparent background
    overlay = frame.copy()
    cv2.rectangle(overlay, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    
    # Draw neon cyan border
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), NEON_BLUE, 2)
    
    # Calculate visible degree range (heading ±60°)
    degree_range = 120  # Total visible range
    min_deg = heading - 60
    max_deg = heading + 60
    
    # Draw degree scale
    scale_y = bar_y + bar_height - 15
    pixels_per_degree = bar_width / degree_range
    
    # Draw tick marks and labels
    for deg_offset in range(-60, 61, 5):
        current_deg = _normalize_angle(heading + deg_offset)
        x_pos = bar_x + int((deg_offset + 60) * pixels_per_degree)
        
        # Major ticks every 10°, minor ticks every 5°
        if deg_offset % 10 == 0:
            tick_height = 10
            # Draw degree label
            label = f"{int(current_deg)}°"
            text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.3, 1)[0]
            cv2.putText(frame, label, (x_pos - text_size[0] // 2, scale_y - 12), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, NEON_BLUE, 1)
        else:
            tick_height = 5
        
        cv2.line(frame, (x_pos, scale_y), (x_pos, scale_y - tick_height), NEON_BLUE, 1)
    
    # Draw cardinal direction markers
    cardinals = [("N", 0), ("E", 90), ("S", 180), ("W", 270)]
    for label, cardinal_deg in cardinals:
        # Calculate position relative to current heading
        relative_deg = cardinal_deg - heading
        # Normalize to -180 to 180 range
        while relative_deg > 180:
            relative_deg -= 360
        while relative_deg < -180:
            relative_deg += 360
        
        # Only draw if within visible range
        if -60 <= relative_deg <= 60:
            x_pos = bar_x + int((relative_deg + 60) * pixels_per_degree)
            cv2.putText(frame, label, (x_pos - 5, bar_y + 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, NEON_PINK, 2)
    
    # Draw current heading indicator (vertical line and digital readout)
    center_x = bar_x + bar_width // 2
    cv2.line(frame, (center_x, bar_y + 5), (center_x, bar_y + bar_height - 5), NEON_GREEN, 3)
    
    # Digital heading readout
    heading_text = f"{int(heading):03d}°"
    text_size = cv2.getTextSize(heading_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
    text_x = center_x - text_size[0] // 2
    text_y = bar_y + 20
    cv2.putText(frame, heading_text, (text_x, text_y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, NEON_GREEN, 2)
    
    # Position RF device icons at their relative bearing
    if rf_devices and wifi_directions:
        # Collect devices with direction information
        devices_with_direction = []
        for device in rf_devices:
            ssid = device.get('SSID') or device.get('ssid')
            if ssid and ssid in wifi_directions:
                direction_data = wifi_directions[ssid]
                direction_deg = direction_data.get('direction_deg')
                confidence = direction_data.get('confidence', 0)
                
                if direction_deg is not None and confidence > 0.3:
                    # Calculate relative bearing
                    relative_deg = direction_deg - heading
                    while relative_deg > 180:
                        relative_deg -= 360
                    while relative_deg < -180:
                        relative_deg += 360
                    
                    # Only include if within visible range
                    if -60 <= relative_deg <= 60:
                        devices_with_direction.append({
                            'device': device,
                            'relative_deg': relative_deg,
                            'direction_deg': direction_deg
                        })
        
        # Sort by relative degree for stacking logic
        devices_with_direction.sort(key=lambda d: d['relative_deg'])
        
        # Implement icon stacking for devices within 5° of each other
        stacks = []
        current_stack = []
        
        for item in devices_with_direction:
            if not current_stack:
                current_stack.append(item)
            else:
                # Check if within 5° of the last device in current stack
                if abs(item['relative_deg'] - current_stack[-1]['relative_deg']) <= 5:
                    current_stack.append(item)
                else:
                    stacks.append(current_stack)
                    current_stack = [item]
        
        if current_stack:
            stacks.append(current_stack)
        
        # Draw each stack
        icon_size = 24
        icon_y_base = bar_y - 15  # Position above the bar
        stack_spacing = 30  # Vertical spacing between stacked icons
        
        for stack in stacks:
            # Calculate average position for the stack
            avg_relative_deg = sum(item['relative_deg'] for item in stack) / len(stack)
            x_pos = bar_x + int((avg_relative_deg + 60) * pixels_per_degree)
            
            # Draw each device in the stack
            for i, item in enumerate(stack):
                device = item['device']
                icon_y = icon_y_base - (i * stack_spacing)
                
                # Get device properties
                device_type = device.get('device_type', 'unknown')
                device_color = device.get('color', NEON_BLUE)
                distance_m = device.get('distance_m', 0)
                
                # Draw device icon with colored border
                _draw_device_icon(frame, (x_pos, icon_y), device_type, icon_size, 
                                (200, 200, 200), device_color)
                
                # Draw connecting line from icon to scale position (if stacked)
                if len(stack) > 1:
                    scale_x = bar_x + int((item['relative_deg'] + 60) * pixels_per_degree)
                    cv2.line(frame, (x_pos, icon_y + icon_size // 2), 
                            (scale_x, scale_y), device_color, 1)
                
                # Display distance estimate below icon
                if distance_m > 0:
                    if distance_m < 1000:
                        distance_text = f"~{int(distance_m)}m"
                    else:
                        distance_text = f"~{distance_m/1000:.1f}km"
                    
                    text_size = cv2.getTextSize(distance_text, cv2.FONT_HERSHEY_SIMPLEX, 0.3, 1)[0]
                    text_x = x_pos - text_size[0] // 2
                    text_y = icon_y + icon_size // 2 + 12
                    
                    # Draw text with outline for visibility
                    cv2.putText(frame, distance_text, (text_x, text_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 2)
                    cv2.putText(frame, distance_text, (text_x, text_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, device_color, 1)


def render_hud(frame, state_snapshot):
    """
    Main rendering function that draws all HUD elements onto the frame.
    
    Args:
        frame: OpenCV frame (numpy array) to draw on
        state_snapshot: Dictionary containing all HUD state data from SharedState
        
    Returns:
        Modified frame with all HUD elements rendered
    """
    # Get heading from IMU first, fall back to GPS
    imu_data = state_snapshot.get('imu', {})
    gps_data = state_snapshot.get('gps', {})
    heading = imu_data.get('heading')
    if heading is None:
        heading = gps_data.get('heading')
    
    # Render heading readout bar (top center)
    rf_devices = state_snapshot.get('wifi_networks', [])
    wifi_directions = state_snapshot.get('wifi_directions', {})
    _draw_heading_bar(frame, heading, rf_devices, wifi_directions)
    
    # Render system metrics (left side)
    _render_system_metrics(frame, state_snapshot.get('system_metrics', {}))
    
    # Render GPS info and compass (left side, below metrics)
    _render_gps_info(frame, state_snapshot)
    
    # Render Wi-Fi networks (right side)
    _render_wifi_networks(frame, state_snapshot)
    
    # Render audio visualizer (center)
    _render_audio_visualizer(frame, state_snapshot.get('audio_buffer'))
    
    # Render RF overlays (bottom left)
    _render_rf_overlays(frame)
    
    return frame


def _render_system_metrics(frame, metrics):
    """
    Renders system metrics on the left side of the HUD.
    
    Args:
        frame: OpenCV frame to draw on
        metrics: Dictionary with CPU, RAM, Temp, Net_Sent, Net_Recv
    """
    x, y, spacing = 30, 50, 35
    
    # CPU usage
    cpu = metrics.get('cpu_percent', 'N/A')
    cpu_text = f"CPU: {cpu}%" if isinstance(cpu, (int, float)) else f"CPU: {cpu}"
    draw_text(frame, cpu_text, (x, y), NEON_PINK)
    
    # RAM usage
    ram = metrics.get('ram_percent', 'N/A')
    ram_text = f"RAM: {ram}%" if isinstance(ram, (int, float)) else f"RAM: {ram}"
    draw_text(frame, ram_text, (x, y + spacing), NEON_GREEN)
    
    # Temperature
    temp = metrics.get('temp_celsius', 'N/A')
    temp_text = f"Temp: {temp}°C" if temp != 'N/A' else "Temp: N/A"
    draw_text(frame, temp_text, (x, y + spacing * 2), NEON_ORANGE)
    
    # Network sent
    net_sent = metrics.get('net_sent_kb', 0)
    draw_text(frame, f"Net ↑: {net_sent:.1f} KB", (x, y + spacing * 3), NEON_BLUE)
    
    # Network received
    net_recv = metrics.get('net_recv_kb', 0)
    draw_text(frame, f"Net ↓: {net_recv:.1f} KB", (x, y + spacing * 4), NEON_PURPLE)


def _render_gps_info(frame, state_snapshot):
    """
    Renders GPS information and compass on the left side below system metrics.
    
    Args:
        frame: OpenCV frame to draw on
        state_snapshot: Complete state snapshot containing GPS and IMU data
    """
    x, y, spacing = 30, 50, 35
    
    # Get heading from IMU first, fall back to GPS
    imu_data = state_snapshot.get('imu', {})
    gps_data = state_snapshot.get('gps', {})
    
    heading = imu_data.get('heading')
    if heading is None:
        heading = gps_data.get('heading')
    
    # Display heading
    if heading is not None:
        draw_text(frame, f"Heading: {heading:.1f}°", (x, y + spacing * 5), NEON_GREEN)
    else:
        draw_text(frame, "Heading: N/A", (x, y + spacing * 5), NEON_GREEN)
    
    # Display latitude
    lat = gps_data.get('latitude')
    if lat is not None:
        draw_text(frame, f"Lat: {lat:.6f}", (x, y + spacing * 6), NEON_BLUE)
    else:
        draw_text(frame, "Lat: N/A", (x, y + spacing * 6), NEON_BLUE)
    
    # Display longitude
    lon = gps_data.get('longitude')
    if lon is not None:
        draw_text(frame, f"Lon: {lon:.6f}", (x, y + spacing * 7), NEON_BLUE)
    else:
        draw_text(frame, "Lon: N/A", (x, y + spacing * 7), NEON_BLUE)
    
    # Display speed
    speed = gps_data.get('speed')
    if speed is not None:
        draw_text(frame, f"Speed: {speed:.2f} m/s", (x, y + spacing * 8), NEON_BLUE)
    else:
        draw_text(frame, "Speed: N/A", (x, y + spacing * 8), NEON_BLUE)
    
    # Draw compass with enhanced indicators
    compass_heading = heading if heading is not None else 0
    rf_devices = state_snapshot.get('wifi_networks', [])
    wifi_directions = state_snapshot.get('wifi_directions', {})
    _draw_compass(frame, compass_heading, wifi_directions, rf_devices)


def _draw_compass(frame, heading, wifi_directions, rf_devices=None, center=(100, 600), radius=40):
    """
    Draws a compass with heading indicator and enhanced Wi-Fi direction indicators.
    
    Args:
        frame: OpenCV frame to draw on
        heading: Current heading in degrees
        wifi_directions: Dictionary of SSID -> {direction_deg, confidence}
        rf_devices: List of RF device dictionaries with device_type, distance_m, color, ssid
        center: Tuple (x, y) for compass center
        radius: Radius of the compass circle
    """
    # Draw compass circle
    cv2.circle(frame, center, radius, NEON_BLUE, 2)
    
    # Direction markers and angles
    directions = [
        ("N", 270), ("NE", 315), ("E", 0), ("SE", 45),
        ("S", 90), ("SW", 135), ("W", 180), ("NW", 225)
    ]
    
    for label, angle_deg in directions:
        angle_rad = math.radians(angle_deg)
        x = int(center[0] + (radius + 10) * math.cos(angle_rad))
        y = int(center[1] + (radius + 10) * math.sin(angle_rad))
        cv2.putText(frame, label, (x - 10, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, NEON_PINK, 1)
    
    # Draw heading needle
    angle_rad = math.radians(-heading + 90)  # Offset so 0 degrees points up
    x2 = int(center[0] + radius * math.cos(angle_rad))
    y2 = int(center[1] - radius * math.sin(angle_rad))
    cv2.line(frame, center, (x2, y2), NEON_GREEN, 2)
    
    # Draw enhanced Wi-Fi direction indicators with device types and stacking
    if rf_devices and wifi_directions:
        # Collect devices with direction information
        devices_with_direction = []
        for device in rf_devices:
            ssid = device.get('SSID') or device.get('ssid')
            if ssid and ssid in wifi_directions:
                direction_data = wifi_directions[ssid]
                direction_deg = direction_data.get('direction_deg')
                confidence = direction_data.get('confidence', 0)
                
                if direction_deg is not None and confidence > 0.3:
                    # Get device properties
                    device_type = device.get('device_type', 'unknown')
                    device_color = device.get('color', NEON_BLUE)
                    distance_m = device.get('distance_m', 0)
                    signal_dbm = device.get('signal_dbm', 0)
                    
                    devices_with_direction.append({
                        'ssid': ssid,
                        'direction_deg': direction_deg,
                        'confidence': confidence,
                        'device_type': device_type,
                        'device_color': device_color,
                        'distance_m': distance_m,
                        'signal_dbm': signal_dbm
                    })
        
        # Sort by direction for stacking logic
        devices_with_direction.sort(key=lambda d: d['direction_deg'])
        
        # Implement label stacking for devices within 15° on compass
        stacks = []
        current_stack = []
        
        for item in devices_with_direction:
            if not current_stack:
                current_stack.append(item)
            else:
                # Check if within 15° of the last device in current stack
                if abs(item['direction_deg'] - current_stack[-1]['direction_deg']) <= 15:
                    current_stack.append(item)
                else:
                    stacks.append(current_stack)
                    current_stack = [item]
        
        if current_stack:
            stacks.append(current_stack)
        
        # Draw each stack
        icon_size = 20  # Smaller icons for compass
        label_spacing = 25  # Vertical spacing between stacked labels
        
        for stack in stacks:
            # Sort stack by signal strength (prioritize closer/stronger signals at top)
            stack.sort(key=lambda d: d['signal_dbm'], reverse=True)
            
            # Calculate average direction for the stack
            avg_direction = sum(item['direction_deg'] for item in stack) / len(stack)
            
            # Convert direction to compass coordinates
            angle_rad = math.radians(-avg_direction + 90)
            
            # Draw icon on compass ring for each device
            for i, item in enumerate(stack):
                # Position on compass ring
                item_angle_rad = math.radians(-item['direction_deg'] + 90)
                indicator_radius = radius - 5
                x_ring = int(center[0] + indicator_radius * math.cos(item_angle_rad))
                y_ring = int(center[1] - indicator_radius * math.sin(item_angle_rad))
                
                # Draw device icon on compass ring
                _draw_device_icon(frame, (x_ring, y_ring), item['device_type'], 
                                icon_size, (200, 200, 200), item['device_color'])
            
            # Draw stacked labels outside the compass
            label_radius = radius + 50
            label_x_base = int(center[0] + label_radius * math.cos(angle_rad))
            label_y_base = int(center[1] - label_radius * math.sin(angle_rad))
            
            for i, item in enumerate(stack):
                # Calculate label position (stacked vertically)
                label_y = label_y_base + (i * label_spacing)
                
                # Format distance
                distance_m = item['distance_m']
                if distance_m > 0:
                    if distance_m < 1000:
                        distance_text = f"~{int(distance_m)}m"
                    else:
                        distance_text = f"~{distance_m/1000:.1f}km"
                else:
                    distance_text = ""
                
                # Create label text with SSID and distance
                label_text = f"{item['ssid']}"
                if distance_text:
                    label_text += f" {distance_text}"
                
                # Measure text size for background
                text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                text_width, text_height = text_size
                
                # Adjust label position based on which side of compass
                if label_x_base > center[0]:
                    # Right side - align left
                    text_x = label_x_base + 5
                else:
                    # Left side - align right
                    text_x = label_x_base - text_width - 5
                
                # Draw semi-transparent background for readability
                bg_padding = 3
                bg_x1 = text_x - bg_padding
                bg_y1 = label_y - text_height - bg_padding
                bg_x2 = text_x + text_width + bg_padding
                bg_y2 = label_y + bg_padding
                
                overlay = frame.copy()
                cv2.rectangle(overlay, (bg_x1, bg_y1), (bg_x2, bg_y2), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
                
                # Draw leader line from label to compass ring position (in device's unique color)
                if len(stack) > 1:
                    item_angle_rad = math.radians(-item['direction_deg'] + 90)
                    x_ring = int(center[0] + (radius - 5) * math.cos(item_angle_rad))
                    y_ring = int(center[1] - (radius - 5) * math.sin(item_angle_rad))
                    cv2.line(frame, (text_x, label_y - text_height // 2), 
                            (x_ring, y_ring), item['device_color'], 1)
                
                # Draw label text with outline
                cv2.putText(frame, label_text, (text_x, label_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 2)
                cv2.putText(frame, label_text, (text_x, label_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.35, item['device_color'], 1)


def _render_wifi_networks(frame, state_snapshot):
    """
    Renders enhanced Wi-Fi network list on the right side with device type icons,
    colors, distance estimates, and rotation logic.
    
    Args:
        frame: OpenCV frame to draw on
        state_snapshot: Complete state snapshot containing Wi-Fi networks
    """
    global _wifi_rotation_index
    
    wifi_networks = state_snapshot.get('wifi_networks', [])
    
    if not wifi_networks:
        # Display "No Wi-Fi data" message
        draw_text(frame, "Wi-Fi: N/A", (950, 50), NEON_BLUE)
        return
    
    # Rotation logic: show up to 8 networks at a time
    max_display = 8
    
    with _wifi_rotation_lock:
        # Rotate through networks if there are more than max_display
        if len(wifi_networks) > max_display:
            start_idx = _wifi_rotation_index % len(wifi_networks)
            display_networks = []
            for i in range(max_display):
                idx = (start_idx + i) % len(wifi_networks)
                display_networks.append(wifi_networks[idx])
        else:
            display_networks = wifi_networks[:max_display]
    
    # Render networks with enhanced display
    frame_height, frame_width = frame.shape[:2]
    list_x = frame_width - 350  # Position from right edge
    list_y = 100
    entry_height = 70  # Height per device entry
    icon_size = 24
    
    for i, device in enumerate(display_networks):
        # Get device properties (handle both uppercase and lowercase keys for compatibility)
        ssid = device.get('SSID') or device.get('ssid', 'Unknown')
        signal = device.get('Signal') or device.get('signal', 'N/A')
        signal_dbm = device.get('signal_dbm', 0)
        channel = device.get('Channel') or device.get('channel', 'N/A')
        device_type = device.get('device_type', 'unknown')
        distance_m = device.get('distance_m', 0)
        device_color = device.get('color', NEON_BLUE)
        
        # Calculate entry position
        entry_y = list_y + (i * entry_height)
        
        # Draw colored accent bar on left edge (device's unique color)
        accent_bar_width = 4
        cv2.rectangle(frame, 
                     (list_x - 10, entry_y - 5), 
                     (list_x - 10 + accent_bar_width, entry_y + entry_height - 10),
                     device_color, -1)
        
        # Draw device type icon with colored border
        icon_x = list_x + 5
        icon_y = entry_y + 15
        _draw_device_icon(frame, (icon_x, icon_y), device_type, icon_size, 
                        (200, 200, 200), device_color)
        
        # Format distance estimate
        distance_text = ""
        if distance_m > 0:
            if distance_m < 1000:
                distance_text = f" ~{int(distance_m)}m"
            else:
                distance_text = f" ~{distance_m/1000:.1f}km"
        
        # Draw SSID with distance
        ssid_x = icon_x + icon_size + 10
        ssid_y = entry_y + 10
        ssid_display = ssid[:20] if len(ssid) > 20 else ssid  # Truncate long SSIDs
        ssid_with_distance = f"{ssid_display}{distance_text}"
        
        # Draw SSID text with outline for visibility
        cv2.putText(frame, ssid_with_distance, (ssid_x, ssid_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
        cv2.putText(frame, ssid_with_distance, (ssid_x, ssid_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, device_color, 1)
        
        # Draw channel number below SSID in smaller text
        channel_y = entry_y + 28
        channel_text = f"Ch: {channel}"
        cv2.putText(frame, channel_text, (ssid_x, channel_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 2)
        cv2.putText(frame, channel_text, (ssid_x, channel_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.35, NEON_BLUE, 1)
        
        # Draw signal strength bar and dBm value
        signal_y = entry_y + 45
        bar_width = 100
        bar_height = 8
        
        # Calculate signal strength percentage (assuming -100 dBm to -30 dBm range)
        if signal_dbm != 0:
            signal_percent = max(0, min(100, ((signal_dbm + 100) / 70) * 100))
        else:
            signal_percent = 0
        
        # Draw signal bar background
        cv2.rectangle(frame, (ssid_x, signal_y), 
                     (ssid_x + bar_width, signal_y + bar_height), 
                     (50, 50, 50), -1)
        
        # Draw signal bar fill (color based on strength)
        fill_width = int(bar_width * (signal_percent / 100))
        if signal_percent > 66:
            bar_color = NEON_GREEN
        elif signal_percent > 33:
            bar_color = NEON_ORANGE
        else:
            bar_color = NEON_PINK
        
        cv2.rectangle(frame, (ssid_x, signal_y), 
                     (ssid_x + fill_width, signal_y + bar_height), 
                     bar_color, -1)
        
        # Draw signal bar outline
        cv2.rectangle(frame, (ssid_x, signal_y), 
                     (ssid_x + bar_width, signal_y + bar_height), 
                     (255, 255, 255), 1)
        
        # Draw dBm value next to bar
        dbm_text = signal if isinstance(signal, str) else f"{signal_dbm} dBm"
        dbm_x = ssid_x + bar_width + 10
        dbm_y = signal_y + bar_height
        cv2.putText(frame, dbm_text, (dbm_x, dbm_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 2)
        cv2.putText(frame, dbm_text, (dbm_x, dbm_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.35, NEON_GREEN, 1)


def rotate_wifi_display():
    """
    Advances the Wi-Fi network rotation index.
    Should be called periodically (e.g., every few seconds) to rotate displayed networks.
    """
    global _wifi_rotation_index
    with _wifi_rotation_lock:
        _wifi_rotation_index += 1


def _render_audio_visualizer(frame, audio_buffer):
    """
    Renders circular FFT-based audio visualizer at the center of the frame.
    
    Args:
        frame: OpenCV frame to draw on
        audio_buffer: Numpy array of audio samples, or None
    """
    if audio_buffer is None or len(audio_buffer) == 0:
        return
    
    # Number of frequency bars to display
    NUM_BARS = 60
    
    # Compute FFT
    try:
        fft = np.abs(np.fft.rfft(audio_buffer))[:NUM_BARS]
        # Normalize
        if np.max(fft) > 0:
            fft /= np.max(fft)
    except Exception:
        return  # Skip rendering if FFT fails
    
    # Draw radial bars
    angle_step = 360 / NUM_BARS
    for i, amplitude in enumerate(fft):
        length = int(amplitude * 100)  # Scale bar length
        angle = math.radians(i * angle_step)
        
        # Starting point on circle circumference
        x1 = int(CENTER[0] + RADIUS * np.cos(angle))
        y1 = int(CENTER[1] + RADIUS * np.sin(angle))
        
        # Ending point extended outward
        x2 = int(CENTER[0] + (RADIUS + length) * np.cos(angle))
        y2 = int(CENTER[1] + (RADIUS + length) * np.sin(angle))
        
        cv2.line(frame, (x1, y1), (x2, y2), NEON_PINK, 2)


def _render_rf_overlays(frame):
    """
    Renders RF event overlays (signal events, scan updates, messages) at bottom left.
    
    Args:
        frame: OpenCV frame to draw on
    """
    x0, y0 = 50, 500
    spacing = 30
    
    with _rf_lock:
        # Render signal events
        while _signal_events:
            label, direction, strength = _signal_events.popleft()
            text = f"[RF] {label} {direction} {strength}dBm"
            draw_text(frame, text, (x0, y0), NEON_GREEN)
            y0 += spacing
        
        # Render scan updates
        while _scan_updates:
            freqs, peaks = _scan_updates.popleft()
            text = "[Scan] " + ", ".join(
                f"{f/1e6:.1f}MHz={'PK' if p else '--'}" 
                for f, p in zip(freqs, peaks)
            )
            draw_text(frame, text, (x0, y0), (255, 255, 0))
            y0 += spacing
        
        # Render messages
        while _message_events:
            sender, text_msg, rssi = _message_events.popleft()
            text = f"[Msg] {sender}: {text_msg} ({rssi}dBm)"
            draw_text(frame, text, (x0, y0), (255, 0, 255))
            y0 += spacing


# Public API for queueing RF events (maintains compatibility with existing code)

def display_signal_event(label: str, direction: str, strength: int):
    """
    Queue a signal event for rendering on the next frame.
    
    Args:
        label: Signal label/identifier
        direction: Direction string (e.g., "N", "SE")
        strength: Signal strength in dBm
    """
    with _rf_lock:
        _signal_events.append((label, direction, strength))


def display_scan_update(frequencies, peaks):
    """
    Queue a scan update for rendering on the next frame.
    
    Args:
        frequencies: List of frequency values
        peaks: List of boolean peak indicators
    """
    with _rf_lock:
        _scan_updates.append((frequencies, peaks))


def display_message_event(sender: str, text: str, rssi: int):
    """
    Queue a message event for rendering on the next frame.
    
    Args:
        sender: Message sender identifier
        text: Message text content
        rssi: Received signal strength indicator in dBm
    """
    with _rf_lock:
        _message_events.append((sender, text, rssi))


def render_overlays(frame):
    """
    Legacy function for rendering RF overlays.
    Maintained for backward compatibility with existing code.
    
    Args:
        frame: OpenCV frame to draw on
    """
    _render_rf_overlays(frame)
