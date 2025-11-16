# theme.py
# Defines HUD neon theme colors and layout settings

NEON_PURPLE = (128, 0, 128)  # RGB color for neon purple
NEON_PINK   = (255, 20, 147)  # RGB color for neon pink
NEON_GREEN  = (0, 255, 0)     # RGB color for neon green
NEON_ORANGE = (255, 165, 0)   # RGB color for neon orange
NEON_BLUE   = (0, 191, 255)   # RGB color for neon blue

FONT = 0  # OpenCV font type for text rendering
FONT_SCALE = 0.6  # Scale factor for font size
THICKNESS = 2  # Thickness of the text and shapes

# Display resolution center and visualizer radius
CENTER = (640, 360)  # Center point for a 1280x720 frame
RADIUS = 300         # Base radius for circular visualizer bars

# Device color palette for individual RF device identification
# Colors in BGR format for OpenCV
DEVICE_COLOR_PALETTE = [
    (255, 255, 0),      # Cyan
    (255, 100, 255),    # Magenta
    (100, 255, 0),      # Green
    (255, 255, 100),    # Yellow
    (100, 150, 255),    # Orange
    (255, 100, 200),    # Purple
    (200, 255, 50),     # Lime
    (100, 200, 255),    # Amber
    (255, 255, 150),    # Light Blue
    (150, 100, 255),    # Pink
    (150, 255, 100),    # Mint
    (100, 255, 200),    # Yellow-Green
]


def assign_device_color(ssid):
    """
    Assign a unique color to a device based on its SSID.
    Uses hash-based assignment to ensure the same device always gets the same color.
    
    Args:
        ssid: The SSID of the device
        
    Returns:
        Tuple of (B, G, R) color values for OpenCV
    """
    color_index = hash(ssid) % len(DEVICE_COLOR_PALETTE)
    return DEVICE_COLOR_PALETTE[color_index]


# ============================================================================
# TWO-LAYER VISUAL SYSTEM FOR RF DEVICE IDENTIFICATION
# ============================================================================
# This system uses two visual layers to identify RF devices:
#
# 1. DEVICE TYPE ICONS (Shape/Symbol)
#    - Consistent icon per device type (router, drone, unknown)
#    - Drawn in white/light gray for neutral appearance
#    - Allows quick identification of device category
#
# 2. INDIVIDUAL DEVICE COLORS (Border/Highlight)
#    - Unique color per device from DEVICE_COLOR_PALETTE
#    - Applied as border, glow, or connecting line
#    - Allows tracking of specific devices across all HUD elements
#
# Example:
#   - Router A: WiFi icon (white) + cyan border
#   - Router B: WiFi icon (white) + magenta border
#   - Drone A: Quadcopter icon (white) + green border
#   - Drone B: Quadcopter icon (white) + yellow border
#
# This design ensures:
#   - Device type is immediately recognizable by icon shape
#   - Individual devices can be tracked by their unique color
#   - Same device has same color across heading bar, compass, and list
# ============================================================================

import cv2
import numpy as np


def draw_router_icon(frame, x, y, size=24, color=(200, 200, 200)):
    """
    Draw a WiFi router icon using OpenCV primitives.
    Icon shows WiFi waves symbol (📶 style).
    
    Args:
        frame: The frame to draw on
        x: X coordinate of icon center
        y: Y coordinate of icon center
        size: Size of the icon in pixels (default 24)
        color: BGR color tuple (default light gray)
    """
    # Base of router (small rectangle at bottom)
    base_height = size // 6
    base_width = size // 2
    base_x1 = x - base_width // 2
    base_y1 = y + size // 3
    base_x2 = x + base_width // 2
    base_y2 = base_y1 + base_height
    cv2.rectangle(frame, (base_x1, base_y1), (base_x2, base_y2), color, -1)
    
    # WiFi waves (3 arcs of increasing size)
    wave_center = (x, y - size // 6)
    
    # Small arc (innermost)
    radius1 = size // 6
    cv2.ellipse(frame, wave_center, (radius1, radius1), 0, 180, 360, color, 2)
    
    # Medium arc
    radius2 = size // 4
    cv2.ellipse(frame, wave_center, (radius2, radius2), 0, 180, 360, color, 2)
    
    # Large arc (outermost)
    radius3 = size // 3
    cv2.ellipse(frame, wave_center, (radius3, radius3), 0, 180, 360, color, 2)
    
    # Center dot
    cv2.circle(frame, wave_center, 2, color, -1)


def draw_drone_icon(frame, x, y, size=24, color=(200, 200, 200)):
    """
    Draw a quadcopter drone icon using OpenCV primitives.
    Icon shows simplified quadcopter silhouette with 4 propellers.
    
    Args:
        frame: The frame to draw on
        x: X coordinate of icon center
        y: Y coordinate of icon center
        size: Size of the icon in pixels (default 24)
        color: BGR color tuple (default light gray)
    """
    # Center body (small circle)
    body_radius = size // 8
    cv2.circle(frame, (x, y), body_radius, color, -1)
    
    # Arms extending to 4 corners
    arm_length = size // 3
    arm_thickness = 2
    
    # Top-left arm
    cv2.line(frame, (x, y), (x - arm_length, y - arm_length), color, arm_thickness)
    # Top-right arm
    cv2.line(frame, (x, y), (x + arm_length, y - arm_length), color, arm_thickness)
    # Bottom-left arm
    cv2.line(frame, (x, y), (x - arm_length, y + arm_length), color, arm_thickness)
    # Bottom-right arm
    cv2.line(frame, (x, y), (x + arm_length, y + arm_length), color, arm_thickness)
    
    # Propellers at end of each arm (small circles)
    prop_radius = size // 10
    cv2.circle(frame, (x - arm_length, y - arm_length), prop_radius, color, -1)
    cv2.circle(frame, (x + arm_length, y - arm_length), prop_radius, color, -1)
    cv2.circle(frame, (x - arm_length, y + arm_length), prop_radius, color, -1)
    cv2.circle(frame, (x + arm_length, y + arm_length), prop_radius, color, -1)


def draw_unknown_icon(frame, x, y, size=24, color=(200, 200, 200)):
    """
    Draw an unknown device icon using OpenCV primitives.
    Icon shows a question mark symbol.
    
    Args:
        frame: The frame to draw on
        x: X coordinate of icon center
        y: Y coordinate of icon center
        size: Size of the icon in pixels (default 24)
        color: BGR color tuple (default light gray)
    """
    # Question mark using text
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = size / 30.0  # Scale based on icon size
    thickness = max(1, size // 12)
    
    # Get text size to center it
    text = "?"
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    # Draw question mark centered
    text_x = x - text_width // 2
    text_y = y + text_height // 2
    cv2.putText(frame, text, (text_x, text_y), font, font_scale, color, thickness)


def draw_icon_with_border(frame, x, y, device_type, device_color, size=24):
    """
    Draw a device type icon with a colored border/highlight.
    This is the main function that combines the two-layer visual system:
    - Layer 1: Device type icon (white/gray)
    - Layer 2: Colored border (unique per device)
    
    Args:
        frame: The frame to draw on
        x: X coordinate of icon center
        y: Y coordinate of icon center
        device_type: Type of device ("router", "drone", "unknown")
        device_color: BGR color tuple for the border/highlight
        size: Size of the icon in pixels (default 24)
    """
    # Draw colored background glow/highlight
    glow_radius = size // 2 + 4
    cv2.circle(frame, (x, y), glow_radius, device_color, 2)
    
    # Draw semi-transparent filled circle for background
    overlay = frame.copy()
    cv2.circle(overlay, (x, y), glow_radius - 1, device_color, -1)
    cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
    
    # Draw the device type icon in white/light gray
    icon_color = (200, 200, 200)  # Light gray
    
    if device_type == "router":
        draw_router_icon(frame, x, y, size, icon_color)
    elif device_type == "drone":
        draw_drone_icon(frame, x, y, size, icon_color)
    else:  # unknown
        draw_unknown_icon(frame, x, y, size, icon_color)