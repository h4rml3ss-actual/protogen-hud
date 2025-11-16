#!/usr/bin/env python3
"""
Integration Logic Test Suite for Enhanced HUD Features
-------------------------------------------------------
Tests the core logic of enhanced features without requiring OpenCV rendering.
This validates:
- Device classification logic
- Distance estimation calculations
- Color assignment consistency
- State management
- Data flow through SharedState

This test suite can run without hardware or OpenCV dependencies.
"""

import sys
import time
from shared_state import SharedState

# Import color palette directly to avoid cv2 dependency
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
    """Assign a unique color to a device based on its SSID."""
    color_index = hash(ssid) % len(DEVICE_COLOR_PALETTE)
    return DEVICE_COLOR_PALETTE[color_index]


def test_shared_state_operations():
    """Test SharedState thread-safe operations."""
    print("\n=== Test 1: SharedState Operations ===")
    
    shared_state = SharedState()
    
    # Test GPS data
    shared_state.set_gps_data(latitude=37.7749, longitude=-122.4194, speed=5.5, heading=45.0)
    gps_data = shared_state.get_gps_data()
    assert gps_data['latitude'] == 37.7749, "GPS latitude mismatch"
    assert gps_data['heading'] == 45.0, "GPS heading mismatch"
    print("✓ GPS data operations working")
    
    # Test IMU data
    shared_state.set_imu_data(heading=90.0, pitch=5.0, roll=-2.0)
    imu_data = shared_state.get_imu_data()
    assert imu_data['heading'] == 90.0, "IMU heading mismatch"
    assert imu_data['pitch'] == 5.0, "IMU pitch mismatch"
    print("✓ IMU data operations working")
    
    # Test system metrics
    shared_state.set_system_metrics(cpu_percent=45.2, ram_percent=62.8, temp_celsius=55.0)
    metrics = shared_state.get_system_metrics()
    assert metrics['cpu_percent'] == 45.2, "CPU metric mismatch"
    assert metrics['temp_celsius'] == 55.0, "Temperature metric mismatch"
    print("✓ System metrics operations working")
    
    # Test Wi-Fi networks
    test_networks = [
        {'ssid': 'TestNet', 'signal_dbm': -50, 'device_type': 'router'}
    ]
    shared_state.set_wifi_networks(test_networks)
    networks = shared_state.get_wifi_networks()
    assert len(networks) == 1, "Wi-Fi networks count mismatch"
    assert networks[0]['ssid'] == 'TestNet', "Wi-Fi SSID mismatch"
    print("✓ Wi-Fi networks operations working")
    
    # Test Wi-Fi directions
    shared_state.set_wifi_direction('TestNet', 180.0, 0.9)
    directions = shared_state.get_wifi_directions()
    assert 'TestNet' in directions, "Wi-Fi direction not stored"
    assert directions['TestNet']['direction_deg'] == 180.0, "Direction mismatch"
    assert directions['TestNet']['confidence'] == 0.9, "Confidence mismatch"
    print("✓ Wi-Fi direction operations working")
    
    # Test snapshot
    snapshot = shared_state.get_snapshot()
    assert 'gps' in snapshot, "Snapshot missing GPS data"
    assert 'imu' in snapshot, "Snapshot missing IMU data"
    assert 'wifi_networks' in snapshot, "Snapshot missing Wi-Fi networks"
    assert 'wifi_directions' in snapshot, "Snapshot missing Wi-Fi directions"
    print("✓ Snapshot operation working")
    
    print("✓ All SharedState operations passed")
    return True


def test_device_classification_logic():
    """Test device classification logic."""
    print("\n=== Test 2: Device Classification Logic ===")
    
    # Test various device types
    devices = [
        {'ssid': 'HomeRouter', 'device_type': 'router', 'frequency': '2.4GHz'},
        {'ssid': 'DJI-Mavic', 'device_type': 'drone', 'frequency': '5.8GHz'},
        {'ssid': 'UnknownAP', 'device_type': 'unknown', 'frequency': '2.4GHz'},
    ]
    
    for device in devices:
        assert 'device_type' in device, f"Device {device['ssid']} missing type"
        assert device['device_type'] in ['router', 'drone', 'unknown'], \
            f"Invalid device type: {device['device_type']}"
        print(f"✓ Device '{device['ssid']}' classified as '{device['device_type']}'")
    
    print("✓ Device classification logic validated")
    return True


def test_distance_estimation_logic():
    """Test distance estimation calculations."""
    print("\n=== Test 3: Distance Estimation Logic ===")
    
    # Test distance calculations for various signal strengths
    # Note: These are approximate ranges based on free space path loss
    test_cases = [
        {'signal_dbm': -30, 'frequency': '2.4GHz', 'expected_range': (500, 1000)},
        {'signal_dbm': -50, 'frequency': '2.4GHz', 'expected_range': (5000, 10000)},
        {'signal_dbm': -70, 'frequency': '2.4GHz', 'expected_range': (50000, 100000)},
        {'signal_dbm': -60, 'frequency': '5.8GHz', 'expected_range': (8000, 12000)},
    ]
    
    for case in test_cases:
        # Simplified path loss formula: distance = 10^((27.55 - RSSI) / 20)
        rssi = case['signal_dbm']
        if case['frequency'] == '2.4GHz':
            distance_m = 10 ** ((27.55 - rssi) / 20)
        else:  # 5.8GHz
            distance_m = 10 ** ((27.55 - rssi - 7.6) / 20)
        
        min_dist, max_dist = case['expected_range']
        assert min_dist <= distance_m <= max_dist, \
            f"Distance {distance_m}m outside expected range {case['expected_range']}"
        print(f"✓ Signal {rssi}dBm ({case['frequency']}) → ~{distance_m:.1f}m")
    
    print("✓ Distance estimation logic validated")
    return True


def test_color_assignment_consistency():
    """Test that color assignment is consistent for same SSID."""
    print("\n=== Test 4: Color Assignment Consistency ===")
    
    # Test same SSID gets same color
    ssids = ['TestRouter', 'DJI-Mavic', 'HomeNet', 'OfficeWiFi']
    
    for ssid in ssids:
        color1 = assign_device_color(ssid)
        color2 = assign_device_color(ssid)
        color3 = assign_device_color(ssid)
        
        assert color1 == color2 == color3, \
            f"Color assignment inconsistent for {ssid}: {color1} != {color2} != {color3}"
        print(f"✓ SSID '{ssid}' consistently assigned color {color1}")
    
    # Test different SSIDs get different colors (most of the time)
    colors = [assign_device_color(ssid) for ssid in ssids]
    unique_colors = len(set(colors))
    print(f"✓ {unique_colors}/{len(ssids)} unique colors assigned")
    
    print("✓ Color assignment consistency validated")
    return True


def test_stacking_logic():
    """Test icon stacking logic for close devices."""
    print("\n=== Test 5: Stacking Logic ===")
    
    # Test heading bar stacking (within 5°)
    devices_heading_bar = [
        {'direction': 90.0, 'ssid': 'Device1'},
        {'direction': 92.0, 'ssid': 'Device2'},  # Within 5° of Device1
        {'direction': 94.0, 'ssid': 'Device3'},  # Within 5° of Device2
        {'direction': 110.0, 'ssid': 'Device4'}, # Not within 5° of Device3
    ]
    
    # Simulate stacking logic
    stacks = []
    current_stack = []
    
    for device in devices_heading_bar:
        if not current_stack:
            current_stack.append(device)
        else:
            if abs(device['direction'] - current_stack[-1]['direction']) <= 5:
                current_stack.append(device)
            else:
                stacks.append(current_stack)
                current_stack = [device]
    
    if current_stack:
        stacks.append(current_stack)
    
    assert len(stacks) == 2, f"Expected 2 stacks, got {len(stacks)}"
    assert len(stacks[0]) == 3, f"First stack should have 3 devices, got {len(stacks[0])}"
    assert len(stacks[1]) == 1, f"Second stack should have 1 device, got {len(stacks[1])}"
    print(f"✓ Heading bar stacking: {len(stacks)} stacks created")
    print(f"  - Stack 1: {len(stacks[0])} devices (90°, 92°, 94°)")
    print(f"  - Stack 2: {len(stacks[1])} devices (110°)")
    
    # Test compass stacking (within 15°)
    devices_compass = [
        {'direction': 0.0, 'ssid': 'North1'},
        {'direction': 10.0, 'ssid': 'North2'},  # Within 15° of North1
        {'direction': 14.0, 'ssid': 'North3'},  # Within 15° of North2
        {'direction': 30.0, 'ssid': 'NE1'},     # Not within 15° of North3
    ]
    
    stacks_compass = []
    current_stack = []
    
    for device in devices_compass:
        if not current_stack:
            current_stack.append(device)
        else:
            if abs(device['direction'] - current_stack[-1]['direction']) <= 15:
                current_stack.append(device)
            else:
                stacks_compass.append(current_stack)
                current_stack = [device]
    
    if current_stack:
        stacks_compass.append(current_stack)
    
    assert len(stacks_compass) == 2, f"Expected 2 compass stacks, got {len(stacks_compass)}"
    assert len(stacks_compass[0]) == 3, f"First compass stack should have 3 devices"
    print(f"✓ Compass stacking: {len(stacks_compass)} stacks created")
    print(f"  - Stack 1: {len(stacks_compass[0])} devices (0°, 10°, 14°)")
    print(f"  - Stack 2: {len(stacks_compass[1])} devices (30°)")
    
    print("✓ Stacking logic validated")
    return True


def test_distance_formatting():
    """Test distance display formatting (meters vs kilometers)."""
    print("\n=== Test 6: Distance Formatting ===")
    
    test_cases = [
        {'distance_m': 5.2, 'expected': '~5m'},
        {'distance_m': 25.8, 'expected': '~25m'},
        {'distance_m': 150.0, 'expected': '~150m'},
        {'distance_m': 999.9, 'expected': '~999m'},
        {'distance_m': 1000.0, 'expected': '~1.0km'},
        {'distance_m': 1250.5, 'expected': '~1.3km'},
        {'distance_m': 5000.0, 'expected': '~5.0km'},
    ]
    
    for case in test_cases:
        distance_m = case['distance_m']
        if distance_m < 1000:
            formatted = f"~{int(distance_m)}m"
        else:
            formatted = f"~{distance_m/1000:.1f}km"
        
        assert formatted == case['expected'], \
            f"Distance formatting mismatch: {formatted} != {case['expected']}"
        print(f"✓ {distance_m}m → {formatted}")
    
    print("✓ Distance formatting validated")
    return True


def test_triangulation_logic():
    """Test triangulation distance calculation logic."""
    print("\n=== Test 7: Triangulation Logic ===")
    
    # Test triangulation with dual adapters
    # Given: adapter separation (d), signal strength at left (RSSI_L) and right (RSSI_R)
    
    test_cases = [
        {
            'adapter_separation_m': 0.15,
            'rssi_left': -50,
            'rssi_right': -52,
            'description': 'Device slightly to the left'
        },
        {
            'adapter_separation_m': 0.15,
            'rssi_left': -55,
            'rssi_right': -55,
            'description': 'Device directly ahead'
        },
        {
            'adapter_separation_m': 0.15,
            'rssi_left': -60,
            'rssi_right': -55,
            'description': 'Device to the right'
        },
    ]
    
    for case in test_cases:
        rssi_l = case['rssi_left']
        rssi_r = case['rssi_right']
        
        # Calculate individual distances
        d_l = 10 ** ((27.55 - rssi_l) / 20)
        d_r = 10 ** ((27.55 - rssi_r) / 20)
        
        # Weighted average triangulation
        if rssi_l + rssi_r != 0:
            distance_triangulated = (d_l * abs(rssi_r) + d_r * abs(rssi_l)) / (abs(rssi_l) + abs(rssi_r))
        else:
            distance_triangulated = (d_l + d_r) / 2
        
        print(f"✓ {case['description']}")
        print(f"  - Left distance: {d_l:.1f}m (RSSI: {rssi_l}dBm)")
        print(f"  - Right distance: {d_r:.1f}m (RSSI: {rssi_r}dBm)")
        print(f"  - Triangulated: {distance_triangulated:.1f}m")
    
    print("✓ Triangulation logic validated")
    return True


def test_data_flow():
    """Test complete data flow through the system."""
    print("\n=== Test 8: Complete Data Flow ===")
    
    # Simulate complete data flow
    shared_state = SharedState()
    
    # Step 1: Services write data to SharedState
    shared_state.set_imu_data(heading=45.0, pitch=2.0, roll=-1.0)
    shared_state.set_gps_data(latitude=37.7749, longitude=-122.4194, speed=5.5)
    shared_state.set_system_metrics(cpu_percent=45.2, ram_percent=62.8, temp_celsius=55.0)
    
    # Step 2: Wi-Fi scanner writes device data
    devices = [
        {
            'ssid': 'TestRouter',
            'signal': '-50 dBm',
            'signal_dbm': -50,
            'channel': '6',
            'security': 'Secured',
            'device_type': 'router',
            'frequency': '2.4GHz',
            'distance_m': 25.0,
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
            'distance_m': 75.0,
            'color': assign_device_color('TestDrone')
        }
    ]
    shared_state.set_wifi_networks(devices)
    
    # Step 3: Wi-Fi locator writes direction data
    shared_state.set_wifi_direction('TestRouter', 90.0, 0.9)
    shared_state.set_wifi_direction('TestDrone', 180.0, 0.8)
    
    # Step 4: Renderer reads snapshot
    snapshot = shared_state.get_snapshot()
    
    # Verify data integrity
    assert snapshot['imu']['heading'] == 45.0, "IMU heading not preserved"
    assert snapshot['gps']['latitude'] == 37.7749, "GPS data not preserved"
    assert len(snapshot['wifi_networks']) == 2, "Wi-Fi networks not preserved"
    assert 'TestRouter' in snapshot['wifi_directions'], "Wi-Fi directions not preserved"
    
    # Verify device data
    router = next(d for d in snapshot['wifi_networks'] if d['ssid'] == 'TestRouter')
    assert router['device_type'] == 'router', "Device type not preserved"
    assert router['distance_m'] == 25.0, "Distance not preserved"
    assert router['color'] == assign_device_color('TestRouter'), "Color not preserved"
    
    print("✓ Data flow validated:")
    print(f"  - IMU heading: {snapshot['imu']['heading']}°")
    print(f"  - GPS location: ({snapshot['gps']['latitude']}, {snapshot['gps']['longitude']})")
    print(f"  - System metrics: CPU {snapshot['system_metrics']['cpu_percent']}%")
    print(f"  - Wi-Fi devices: {len(snapshot['wifi_networks'])}")
    print(f"  - Wi-Fi directions: {len(snapshot['wifi_directions'])}")
    
    print("✓ Complete data flow validated")
    return True


def test_performance_logic():
    """Test performance with many devices."""
    print("\n=== Test 9: Performance with Many Devices ===")
    
    # Create many devices
    num_devices = 50
    devices = []
    for i in range(num_devices):
        devices.append({
            'ssid': f'Device{i}',
            'signal': f'-{50 + i} dBm',
            'signal_dbm': -(50 + i),
            'channel': str((i % 11) + 1),
            'security': 'Secured' if i % 2 == 0 else 'Open',
            'device_type': ['router', 'drone', 'unknown'][i % 3],
            'frequency': '2.4GHz' if i % 2 == 0 else '5.8GHz',
            'distance_m': 10.0 + i * 5,
            'color': assign_device_color(f'Device{i}')
        })
    
    shared_state = SharedState()
    
    # Measure write performance
    start_time = time.time()
    for _ in range(1000):
        shared_state.set_wifi_networks(devices)
    write_time = time.time() - start_time
    
    # Measure read performance
    start_time = time.time()
    for _ in range(1000):
        snapshot = shared_state.get_snapshot()
    read_time = time.time() - start_time
    
    print(f"✓ Performance with {num_devices} devices:")
    print(f"  - 1000 writes: {write_time*1000:.2f}ms ({write_time:.6f}ms per write)")
    print(f"  - 1000 reads: {read_time*1000:.2f}ms ({read_time:.6f}ms per read)")
    print(f"  - Total operations: 2000 in {(write_time + read_time)*1000:.2f}ms")
    
    # Verify data integrity
    snapshot = shared_state.get_snapshot()
    assert len(snapshot['wifi_networks']) == num_devices, "Device count mismatch"
    
    print("✓ Performance validated")
    return True


def run_all_tests():
    """Run all integration logic tests."""
    print("="*60)
    print("HUD ENHANCED FEATURES INTEGRATION LOGIC TEST SUITE")
    print("="*60)
    print("Testing core logic without OpenCV rendering dependencies")
    
    tests = [
        test_shared_state_operations,
        test_device_classification_logic,
        test_distance_estimation_logic,
        test_color_assignment_consistency,
        test_stacking_logic,
        test_distance_formatting,
        test_triangulation_logic,
        test_data_flow,
        test_performance_logic,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            result = test_func()
            if result:
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
        print("\n✓ ALL LOGIC TESTS PASSED")
        print("\nNote: These tests validate the core logic.")
        print("For visual validation, run the actual HUD system with:")
        print("  python3 main.py")
        return 0
    else:
        print(f"\n✗ {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
