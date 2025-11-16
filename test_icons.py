#!/usr/bin/env python3
"""
Test script for device icon rendering and color assignment.
Creates a test image showing all icon types with different colors.
"""

import cv2
import numpy as np
from theme import (
    assign_device_color,
    draw_router_icon,
    draw_drone_icon,
    draw_unknown_icon,
    draw_icon_with_border,
    DEVICE_COLOR_PALETTE
)

def main():
    # Create a test frame (dark background like HUD)
    frame = np.zeros((600, 1000, 3), dtype=np.uint8)
    frame[:] = (20, 20, 20)  # Dark gray background
    
    # Test 1: Color assignment consistency
    print("Testing color assignment consistency...")
    test_ssids = ["HomeRouter", "DJI-Mavic", "OfficeWiFi", "Phantom4", "UnknownDevice"]
    
    for ssid in test_ssids:
        color1 = assign_device_color(ssid)
        color2 = assign_device_color(ssid)
        assert color1 == color2, f"Color assignment not consistent for {ssid}"
        print(f"  {ssid}: {color1} ✓")
    
    print("\nColor assignment test PASSED ✓\n")
    
    # Test 2: Draw individual icons (24x24 for heading bar)
    print("Drawing 24x24 icons (heading bar size)...")
    y_pos = 100
    
    # Router icons with different colors
    cv2.putText(frame, "Routers (24x24):", (50, y_pos - 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    for i, ssid in enumerate(["Router1", "Router2", "Router3"]):
        x_pos = 150 + i * 100
        color = assign_device_color(ssid)
        draw_icon_with_border(frame, x_pos, y_pos, "router", color, size=24)
        cv2.putText(frame, ssid, (x_pos - 30, y_pos + 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    # Drone icons with different colors
    y_pos = 220
    cv2.putText(frame, "Drones (24x24):", (50, y_pos - 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    for i, ssid in enumerate(["DJI-Mavic", "Phantom4", "Autel-Evo"]):
        x_pos = 150 + i * 100
        color = assign_device_color(ssid)
        draw_icon_with_border(frame, x_pos, y_pos, "drone", color, size=24)
        cv2.putText(frame, ssid, (x_pos - 35, y_pos + 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    # Unknown icons with different colors
    y_pos = 340
    cv2.putText(frame, "Unknown (24x24):", (50, y_pos - 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    for i, ssid in enumerate(["Device1", "Device2", "Device3"]):
        x_pos = 150 + i * 100
        color = assign_device_color(ssid)
        draw_icon_with_border(frame, x_pos, y_pos, "unknown", color, size=24)
        cv2.putText(frame, ssid, (x_pos - 30, y_pos + 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    # Test 3: Draw smaller icons (20x20 for compass)
    print("Drawing 20x20 icons (compass size)...")
    y_pos = 460
    
    cv2.putText(frame, "Compass Size (20x20):", (50, y_pos - 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    device_types = ["router", "drone", "unknown"]
    ssids = ["CompactRouter", "CompactDrone", "CompactUnknown"]
    
    for i, (device_type, ssid) in enumerate(zip(device_types, ssids)):
        x_pos = 150 + i * 100
        color = assign_device_color(ssid)
        draw_icon_with_border(frame, x_pos, y_pos, device_type, color, size=20)
        cv2.putText(frame, f"{device_type}", (x_pos - 30, y_pos + 35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    # Test 4: Show color palette
    print("\nDisplaying color palette...")
    x_start = 550
    y_start = 100
    cv2.putText(frame, "Device Color Palette:", (x_start, y_start - 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    for i, color in enumerate(DEVICE_COLOR_PALETTE):
        x_pos = x_start + (i % 3) * 120
        y_pos = y_start + (i // 3) * 60
        
        # Draw color swatch
        cv2.rectangle(frame, (x_pos, y_pos), (x_pos + 40, y_pos + 40), color, -1)
        cv2.rectangle(frame, (x_pos, y_pos), (x_pos + 40, y_pos + 40), (255, 255, 255), 1)
        
        # Draw color index
        cv2.putText(frame, f"#{i+1}", (x_pos + 50, y_pos + 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    # Add title
    cv2.putText(frame, "RF Device Icon & Color System Test", (250, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
    
    # Save the test image
    output_file = "icon_test_output.png"
    cv2.imwrite(output_file, frame)
    print(f"\nTest image saved to: {output_file}")
    
    # Display the frame
    print("\nDisplaying test frame (press any key to close)...")
    cv2.imshow("Icon Test", frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    print("\n✓ All tests completed successfully!")

if __name__ == "__main__":
    main()
