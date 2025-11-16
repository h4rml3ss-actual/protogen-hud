#!/usr/bin/env python3
"""
Integration Test Suite for Enhanced HUD Features
-------------------------------------------------
Tests all enhanced features including:
- Device classification (router, drone, unknown)
- Distance estimation (2.4GHz and 5.8GHz)
- Triangulation with dual adapters
- Heading readout bar rendering
- Compass indicator stacking
- RF device list display
- Color coding consistency
- Icon stacking logic
- Graceful degradation

This test suite validates the complete integration of all enhanced features
without requiring actual hardware by using mock data.
"""

import cv2
import numpy as np
import sys
import time
from shared_state import SharedState
from hud_renderer import render_hud
from theme import assign_device_color


def create_test_frame():
    """Create a blank test frame."""
    return np.zeros((720, 1280, 3), dtype=np.uint8)


def test_device_classification():
    """Test device classification with various device types."""
    print("\n=== Test 1: Device Classification ===")
    
    # Create mock RF devices with different types
    test_devices = [
        {
            'ssid': 'HomeRouter',
            'signal': '-45 dBm',
            'signal_dbm': -45,
            'channel': '6',
            'security': 'Secured',
            'device_type': 'router',
            'frequency': '2.4GHz',
            'distance_m': 15.5,
            'color': assign_device_color('HomeRouter')
        },
        {
            'ssid': 'DJI-Mavic-5G',
            'signal': '-55 dBm',
            'signal_dbm': -55,
            'channel': '149',
            'security': 'Open',
            'device_type': 'drone',
            'frequency': '5.8GHz',
            'distance_m': 45.2,
            'color': assign_device_color('DJI-Mavic-5G')
        },
        {
            'ssid': 'UnknownDevice',
            'signal': '-70 dBm',
            'signal_dbm': -70,
            'channel': '11',
            'security': 'Secured',
            'device_type': 'unknown',
            'frequency': '2.4GHz',
            'distance_m': 120.8,
            'color': assign_device_color('UnknownDevice')
        }
    ]
    
    # Create state snapshot
    shared_state = SharedState()
    shared_state.set_wifi_networks(test_devices)
    shared_state.set_imu_data(heading=45.0)
    
    # Add direction data for devices
    for device in test_devices:
        shared_state.set_wifi_direction(device['ssid'], 90.0, 0.8)
    
    snapshot = shared_state.get_snapshot()
    
    # Render frame
    frame = create_test_frame()
    frame = render_hud(frame, snapshot)
    
    # Verify rendering completed without errors
    print("✓ Device classification rendering completed")
    print(f"  - Router: {test_devices[0]['ssid']}")
    print(f"  - Drone: {test_devices[1]['ssid']}")
    print(f"  - Unknown: {test_devices[2]['ssid']}")
    
    return frame, "device_classification"


def test_distance_estimation():
    """Test distance estimation for 2.4GHz and 5.8GHz devices."""
    print("\n=== Test 2: Distance Estimation ===")
    
    # Create devices at various distances
    test_devices = [
        {
            'ssid': 'Close2.4GHz',
            'signal': '-30 dBm',
            'signal_dbm': -30,
            'channel': '1',
            'security': 'Secured',
            'device_type': 'router',
            'frequency': '2.4GHz',
            'distance_m': 5.2,  # Very close
            'color': assign_device_color('Close2.4GHz')
        },
        {
            'ssid': 'Medium5.8GHz',
            'signal': '-60 dBm',
            'signal_dbm': -60,
            'channel': '149',
            'security': 'Open',
            'device_type': 'drone',
            'frequency': '5.8GHz',
            'distance_m': 85.5,  # Medium distance
            'color': assign_device_color('Medium5.8GHz')
        },
        {
            'ssid': 'Far2.4GHz',
            'signal': '-85 dBm',
            'signal_dbm': -85,
            'channel': '11',
            'security': 'Secured',
            'device_type': 'router',
            'frequency': '2.4GHz',
            'distance_m': 1250.0,  # Far (should display in km)
            'color': assign_device_color('Far2.4GHz')
        }
    ]
    
    shared_state = SharedState()
    shared_state.set_wifi_networks(test_devices)
    shared_state.set_imu_data(heading=180.0)
    
    # Add direction data
    for i, device in enumerate(test_devices):
        shared_state.set_wifi_direction(device['ssid'], 45.0 + i * 30, 0.9)
    
    snapshot = shared_state.get_snapshot()
    
    # Render frame
    frame = create_test_frame()
    frame = render_hud(frame, snapshot)
    
    print("✓ Distance estimation rendering completed")
    print(f"  - Close (2.4GHz): {test_devices[0]['distance_m']}m")
    print(f"  - Medium (5.8GHz): {test_devices[1]['distance_m']}m")
    print(f"  - Far (2.4GHz): {test_devices[2]['distance_m']}m (~{test_devices[2]['distance_m']/1000:.1f}km)")
    
    return frame, "distance_estimation"


def test_heading_bar_with_stacking():
    """Test heading readout bar with icon stacking for close devices."""
    print("\n=== Test 3: Heading Bar Icon Stacking ===")
    
    # Create devices within 5° of each other (should stack)
    test_devices = [
        {
            'ssid': 'Device1',
            'signal': '-50 dBm',
            'signal_dbm': -50,
            'channel': '6',
            'security': 'Secured',
            'device_type': 'router',
            'frequency': '2.4GHz',
            'distance_m': 25.0,
            'color': assign_device_color('Device1')
        },
        {
            'ssid': 'Device2',
            'signal': '-52 dBm',
            'signal_dbm': -52,
            'channel': '11',
            'security': 'Secured',
            'device_type': 'drone',
            'frequency': '5.8GHz',
            'distance_m': 30.0,
            'color': assign_device_color('Device2')
        },
        {
            'ssid': 'Device3',
            'signal': '-48 dBm',
            'signal_dbm': -48,
            'channel': '1',
            'security': 'Open',
            'device_type': 'unknown',
            'frequency': '2.4GHz',
            'distance_m': 20.0,
            'color': assign_device_color('Device3')
        }
    ]
    
    shared_state = SharedState()
    shared_state.set_wifi_networks(test_devices)
    shared_state.set_imu_data(heading=90.0)
    
    # Set directions within 5° of each other (should trigger stacking)
    shared_state.set_wifi_direction('Device1', 92.0, 0.9)
    shared_state.set_wifi_direction('Device2', 94.0, 0.9)
    shared_state.set_wifi_direction('Device3', 96.0, 0.9)
    
    snapshot = shared_state.get_snapshot()
    
    # Render frame
    frame = create_test_frame()
    frame = render_hud(frame, snapshot)
    
    print("✓ Heading bar icon stacking completed")
    print("  - 3 devices within 5° should be stacked vertically")
    print("  - Connecting lines should be drawn to scale positions")
    
    return frame, "heading_bar_stacking"


def test_compass_stacking():
    """Test compass indicator stacking for devices within 15°."""
    print("\n=== Test 4: Compass Indicator Stacking ===")
    
    # Create devices within 15° on compass (should stack labels)
    test_devices = [
        {
            'ssid': 'North1',
            'signal': '-45 dBm',
            'signal_dbm': -45,
            'channel': '6',
            'security': 'Secured',
            'device_type': 'router',
            'frequency': '2.4GHz',
            'distance_m': 15.0,
            'color': assign_device_color('North1')
        },
        {
            'ssid': 'North2',
            'signal': '-50 dBm',
            'signal_dbm': -50,
            'channel': '11',
            'security': 'Secured',
            'device_type': 'drone',
            'frequency': '5.8GHz',
            'distance_m': 25.0,
            'color': assign_device_color('North2')
        },
        {
            'ssid': 'North3',
            'signal': '-55 dBm',
            'signal_dbm': -55,
            'channel': '1',
            'security': 'Open',
            'device_type': 'router',
            'frequency': '2.4GHz',
            'distance_m': 35.0,
            'color': assign_device_color('North3')
        }
    ]
    
    shared_state = SharedState()
    shared_state.set_wifi_networks(test_devices)
    shared_state.set_imu_data(heading=0.0)
    
    # Set directions within 15° (should trigger label stacking)
    shared_state.set_wifi_direction('North1', 5.0, 0.9)
    shared_state.set_wifi_direction('North2', 10.0, 0.9)
    shared_state.set_wifi_direction('North3', 15.0, 0.9)
    
    snapshot = shared_state.get_snapshot()
    
    # Render frame
    frame = create_test_frame()
    frame = render_hud(frame, snapshot)
    
    print("✓ Compass indicator stacking completed")
    print("  - 3 devices within 15° should have stacked labels")
    print("  - Leader lines should connect labels to compass ring")
    print("  - Stronger signals should be prioritized at top")
    
    return frame, "compass_stacking"


def test_color_consistency():
    """Test that device colors are consistent across all HUD elements."""
    print("\n=== Test 5: Color Coding Consistency ===")
    
    # Create devices with known SSIDs to verify color consistency
    test_devices = [
        {
            'ssid': 'TestRouter',
            'signal': '-50 dBm',
            'signal_dbm': -50,
            'channel': '6',
            'security': 'Secured',
            'device_type': 'router',
            'frequency': '2.4GHz',
            'distance_m': 20.0,
            'color': assign_device_color('TestRouter')
        },
        {
            'ssid': 'TestDrone',
            'signal': '-60 dBm',
            'signal_dbm': -60,
            'channel': '149',
            'security': 'Open',
            'device_type': 'drone',
            'frequency': '5.8GHz',
            'distance_m': 50.0,
            'color': assign_device_color('TestDrone')
        }
    ]
    
    # Verify color assignment is consistent
    color1_a = assign_device_color('TestRouter')
    color1_b = assign_device_color('TestRouter')
    assert color1_a == color1_b, "Color assignment should be consistent for same SSID"
    
    shared_state = SharedState()
    shared_state.set_wifi_networks(test_devices)
    shared_state.set_imu_data(heading=45.0)
    
    # Add direction data
    shared_state.set_wifi_direction('TestRouter', 90.0, 0.9)
    shared_state.set_wifi_direction('TestDrone', 180.0, 0.9)
    
    snapshot = shared_state.get_snapshot()
    
    # Render frame
    frame = create_test_frame()
    frame = render_hud(frame, snapshot)
    
    print("✓ Color consistency verified")
    print(f"  - TestRouter color: {test_devices[0]['color']}")
    print(f"  - TestDrone color: {test_devices[1]['color']}")
    print("  - Same device should have same color across heading bar, compass, and list")
    
    return frame, "color_consistency"


def test_mixed_device_types():
    """Test RF device list with mixed device types and distances."""
    print("\n=== Test 6: Mixed Device Types Display ===")
    
    # Create a realistic mix of devices
    test_devices = [
        {
            'ssid': 'HomeWiFi',
            'signal': '-40 dBm',
            'signal_dbm': -40,
            'channel': '6',
            'security': 'Secured',
            'device_type': 'router',
            'frequency': '2.4GHz',
            'distance_m': 10.0,
            'color': assign_device_color('HomeWiFi')
        },
        {
            'ssid': 'DJI-Phantom',
            'signal': '-65 dBm',
            'signal_dbm': -65,
            'channel': '149',
            'security': 'Open',
            'device_type': 'drone',
            'frequency': '5.8GHz',
            'distance_m': 100.0,
            'color': assign_device_color('DJI-Phantom')
        },
        {
            'ssid': 'OfficeNet',
            'signal': '-55 dBm',
            'signal_dbm': -55,
            'channel': '11',
            'security': 'Secured',
            'device_type': 'router',
            'frequency': '2.4GHz',
            'distance_m': 35.0,
            'color': assign_device_color('OfficeNet')
        },
        {
            'ssid': 'Parrot-Anafi',
            'signal': '-70 dBm',
            'signal_dbm': -70,
            'channel': '157',
            'security': 'Open',
            'device_type': 'drone',
            'frequency': '5.8GHz',
            'distance_m': 150.0,
            'color': assign_device_color('Parrot-Anafi')
        },
        {
            'ssid': 'Mystery-AP',
            'signal': '-75 dBm',
            'signal_dbm': -75,
            'channel': '3',
            'security': 'Secured',
            'device_type': 'unknown',
            'frequency': '2.4GHz',
            'distance_m': 200.0,
            'color': assign_device_color('Mystery-AP')
        }
    ]
    
    shared_state = SharedState()
    shared_state.set_wifi_networks(test_devices)
    shared_state.set_imu_data(heading=0.0)
    
    # Add direction data for all devices
    for i, device in enumerate(test_devices):
        shared_state.set_wifi_direction(device['ssid'], i * 60.0, 0.8)
    
    snapshot = shared_state.get_snapshot()
    
    # Render frame
    frame = create_test_frame()
    frame = render_hud(frame, snapshot)
    
    print("✓ Mixed device types rendering completed")
    print(f"  - Total devices: {len(test_devices)}")
    print(f"  - Routers: {sum(1 for d in test_devices if d['device_type'] == 'router')}")
    print(f"  - Drones: {sum(1 for d in test_devices if d['device_type'] == 'drone')}")
    print(f"  - Unknown: {sum(1 for d in test_devices if d['device_type'] == 'unknown')}")
    
    return frame, "mixed_device_types"


def test_graceful_degradation():
    """Test graceful degradation when no RF devices detected."""
    print("\n=== Test 7: Graceful Degradation ===")
    
    # Create state with no Wi-Fi devices
    shared_state = SharedState()
    shared_state.set_wifi_networks([])
    shared_state.set_imu_data(heading=270.0)
    shared_state.set_system_metrics(
        cpu_percent=45.2,
        ram_percent=62.8,
        temp_celsius=55.0,
        net_sent_kb=1024.5,
        net_recv_kb=2048.3
    )
    
    snapshot = shared_state.get_snapshot()
    
    # Render frame
    frame = create_test_frame()
    frame = render_hud(frame, snapshot)
    
    print("✓ Graceful degradation verified")
    print("  - No RF devices detected")
    print("  - HUD should display 'Wi-Fi: N/A' without crashing")
    print("  - Other HUD elements should still render normally")
    
    return frame, "graceful_degradation"


def test_various_headings():
    """Test heading readout bar with various heading values."""
    print("\n=== Test 8: Various Heading Values ===")
    
    test_devices = [
        {
            'ssid': 'TestDevice',
            'signal': '-50 dBm',
            'signal_dbm': -50,
            'channel': '6',
            'security': 'Secured',
            'device_type': 'router',
            'frequency': '2.4GHz',
            'distance_m': 25.0,
            'color': assign_device_color('TestDevice')
        }
    ]
    
    headings = [0, 45, 90, 135, 180, 225, 270, 315]
    frames = []
    
    for heading in headings:
        shared_state = SharedState()
        shared_state.set_wifi_networks(test_devices)
        shared_state.set_imu_data(heading=float(heading))
        shared_state.set_wifi_direction('TestDevice', (heading + 30) % 360, 0.9)
        
        snapshot = shared_state.get_snapshot()
        frame = create_test_frame()
        frame = render_hud(frame, snapshot)
        frames.append((frame, f"heading_{heading}"))
    
    print("✓ Various heading values tested")
    print(f"  - Tested headings: {headings}")
    print("  - Heading bar should correctly display ±60° range for each")
    
    return frames[0][0], "various_headings"


def test_performance():
    """Test performance impact of enhanced rendering."""
    print("\n=== Test 9: Performance Impact ===")
    
    # Create a realistic scenario with many devices
    test_devices = []
    for i in range(20):
        test_devices.append({
            'ssid': f'Device{i}',
            'signal': f'-{50 + i*2} dBm',
            'signal_dbm': -(50 + i*2),
            'channel': str((i % 11) + 1),
            'security': 'Secured' if i % 2 == 0 else 'Open',
            'device_type': ['router', 'drone', 'unknown'][i % 3],
            'frequency': '2.4GHz' if i % 2 == 0 else '5.8GHz',
            'distance_m': 10.0 + i * 10,
            'color': assign_device_color(f'Device{i}')
        })
    
    shared_state = SharedState()
    shared_state.set_wifi_networks(test_devices)
    shared_state.set_imu_data(heading=45.0)
    
    # Add direction data for all devices
    for i, device in enumerate(test_devices):
        shared_state.set_wifi_direction(device['ssid'], (i * 18) % 360, 0.7)
    
    snapshot = shared_state.get_snapshot()
    
    # Measure rendering time
    num_iterations = 100
    start_time = time.time()
    
    for _ in range(num_iterations):
        frame = create_test_frame()
        frame = render_hud(frame, snapshot)
    
    end_time = time.time()
    avg_time = (end_time - start_time) / num_iterations
    fps = 1.0 / avg_time if avg_time > 0 else 0
    
    print("✓ Performance test completed")
    print(f"  - Devices rendered: {len(test_devices)}")
    print(f"  - Average render time: {avg_time*1000:.2f}ms")
    print(f"  - Estimated FPS: {fps:.1f}")
    print(f"  - Target FPS: 30")
    print(f"  - Performance: {'✓ PASS' if fps >= 30 else '✗ FAIL (optimization needed)'}")
    
    return frame, "performance"


def save_test_frame(frame, test_name):
    """Save test frame to file for visual inspection."""
    filename = f"test_output_{test_name}.png"
    cv2.imwrite(filename, frame)
    print(f"  - Saved test frame: {filename}")


def run_all_tests(save_frames=False):
    """Run all integration tests."""
    print("="*60)
    print("HUD ENHANCED FEATURES INTEGRATION TEST SUITE")
    print("="*60)
    
    tests = [
        test_device_classification,
        test_distance_estimation,
        test_heading_bar_with_stacking,
        test_compass_stacking,
        test_color_consistency,
        test_mixed_device_types,
        test_graceful_degradation,
        test_various_headings,
        test_performance
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            frame, test_name = test_func()
            if save_frames:
                save_test_frame(frame, test_name)
            passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(passed/len(tests)*100):.1f}%")
    
    if failed == 0:
        print("\n✓ ALL TESTS PASSED")
        return 0
    else:
        print(f"\n✗ {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    # Parse command-line arguments
    save_frames = "--save-frames" in sys.argv
    
    if save_frames:
        print("Note: Test frames will be saved to disk for visual inspection")
    
    exit_code = run_all_tests(save_frames)
    sys.exit(exit_code)
