# Integration Testing Quick Start Guide

## Overview

This guide provides quick instructions for running integration tests on the enhanced HUD features.

## Test Files

1. **test_integration_logic.py** - Core logic tests (no hardware required)
2. **test_integration.py** - Full visual tests (requires OpenCV and hardware)
3. **INTEGRATION_TEST_REPORT.md** - Detailed test report

## Quick Test Commands

### 1. Run Logic Tests (Recommended First)
```bash
python3 test_integration_logic.py
```

**What it tests:**
- SharedState thread-safe operations
- Device classification logic
- Distance estimation calculations
- Color assignment consistency
- Stacking logic (heading bar and compass)
- Distance formatting
- Triangulation calculations
- Complete data flow
- Performance with many devices

**Expected output:** `✓ ALL LOGIC TESTS PASSED`

---

### 2. Run Visual Tests (Requires OpenCV)
```bash
# Install dependencies first
pip3 install opencv-python numpy psutil

# Run tests
python3 test_integration.py

# Save test frames for inspection
python3 test_integration.py --save-frames
```

**What it tests:**
- Device classification rendering
- Distance estimation display
- Heading bar icon stacking
- Compass indicator stacking
- Color consistency across displays
- Mixed device types
- Graceful degradation
- Various heading values
- Performance impact

**Expected output:** Test frames saved as PNG files

---

### 3. Run Full HUD System
```bash
# With calibration
python3 main.py

# Skip calibration (use previous config)
python3 main.py --skip-calibration
```

**What to verify:**
- Wi-Fi adapter calibration works correctly
- Heading readout bar displays at top
- RF devices appear with correct icons
- Colors are consistent across all displays
- Distance estimates are reasonable
- Icon stacking works visually
- Compass indicators display correctly
- RF device list shows all information

---

## Test Checklist

### Logic Tests ✅
- [ ] Run `python3 test_integration_logic.py`
- [ ] Verify all 9 tests pass
- [ ] Check performance metrics (should be <0.002ms per operation)

### Visual Tests (if OpenCV available)
- [ ] Run `python3 test_integration.py`
- [ ] Check test output frames
- [ ] Verify rendering completes without errors

### Hardware Tests (requires actual hardware)
- [ ] Run Wi-Fi adapter calibration
- [ ] Verify left/right adapter detection
- [ ] Test with real Wi-Fi networks
- [ ] Verify distance estimates are reasonable
- [ ] Test with multiple devices (>8 for rotation)
- [ ] Verify icon stacking with close devices
- [ ] Check color consistency across displays
- [ ] Test graceful degradation (no devices)
- [ ] Verify performance (should maintain 30 FPS)

### Real-World Validation
- [ ] Test distance accuracy at known distances
- [ ] Test 2.4GHz device detection
- [ ] Test 5.8GHz device detection (drones)
- [ ] Test triangulation with dual adapters
- [ ] Verify direction finding accuracy
- [ ] Test with swapped left/right adapters

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'cv2'"
**Solution:** Install OpenCV
```bash
pip3 install opencv-python
```

### "No Wi-Fi adapters detected"
**Solution:** Check USB adapters are connected
```bash
# List wireless interfaces
iw dev

# List USB devices
lsusb

# Check interface status
ip link show
```

### "Calibration failed"
**Solution:** 
1. Ensure both adapters are disconnected initially
2. Connect adapters one at a time
3. Wait for USB enumeration (2 seconds)
4. Use hardware power switches if available

### "Distance estimates seem wrong"
**Solution:**
1. Check adapter separation is correct (default 15cm)
2. Verify transmit power assumptions are reasonable
3. Remember distances are approximate (~)
4. Environmental factors affect accuracy

### "Performance is slow"
**Solution:**
1. Check CPU usage (should be <50%)
2. Reduce number of devices if needed
3. Check for other processes using resources
4. Verify frame rate with FPS counter

---

## Expected Test Results

### Logic Tests
```
============================================================
HUD ENHANCED FEATURES INTEGRATION LOGIC TEST SUITE
============================================================
Testing core logic without OpenCV rendering dependencies

=== Test 1: SharedState Operations ===
✓ All SharedState operations passed

=== Test 2: Device Classification Logic ===
✓ Device classification logic validated

=== Test 3: Distance Estimation Logic ===
✓ Distance estimation logic validated

=== Test 4: Color Assignment Consistency ===
✓ Color assignment consistency validated

=== Test 5: Stacking Logic ===
✓ Stacking logic validated

=== Test 6: Distance Formatting ===
✓ Distance formatting validated

=== Test 7: Triangulation Logic ===
✓ Triangulation logic validated

=== Test 8: Complete Data Flow ===
✓ Complete data flow validated

=== Test 9: Performance with Many Devices ===
✓ Performance validated

============================================================
TEST SUMMARY
============================================================
Total tests: 9
Passed: 9
Failed: 0
Success rate: 100.0%

✓ ALL LOGIC TESTS PASSED
```

### Performance Benchmarks
- Write operations: <0.001ms per operation
- Read operations: <0.002ms per operation
- 50 devices: No performance degradation
- Estimated FPS: >400 (far exceeds 30 FPS target)

---

## Test Coverage Summary

| Feature | Logic Tests | Visual Tests | Hardware Tests |
|---------|-------------|--------------|----------------|
| Device Classification | ✅ | ✅ | ⏳ Required |
| Distance Estimation | ✅ | ✅ | ⏳ Required |
| Heading Readout Bar | ✅ | ✅ | ⏳ Required |
| Compass Indicators | ✅ | ✅ | ⏳ Required |
| RF Device List | ✅ | ✅ | ⏳ Required |
| Color Consistency | ✅ | ✅ | ⏳ Required |
| Icon Stacking | ✅ | ✅ | ⏳ Required |
| Triangulation | ✅ | ⏳ Optional | ⏳ Required |
| Graceful Degradation | ✅ | ✅ | ⏳ Required |
| Performance | ✅ | ✅ | ⏳ Required |

Legend:
- ✅ Completed and passing
- ⏳ Requires hardware/manual testing
- ❌ Failed or not implemented

---

## Next Steps

1. **Run logic tests** to verify core functionality
2. **Run visual tests** if OpenCV is available
3. **Run HUD system** with actual hardware
4. **Perform real-world validation** with known distances
5. **Document any issues** in GitHub issues or bug tracker
6. **Update test report** with hardware test results

---

## Support

For issues or questions:
1. Check INTEGRATION_TEST_REPORT.md for detailed results
2. Review requirements.md and design.md for specifications
3. Check error.log and startup.log for runtime issues
4. Consult WIFI_CALIBRATION_GUIDE.md for adapter setup

---

**Last Updated:** November 11, 2025  
**Test Suite Version:** 1.0  
**Status:** ✅ Logic tests passing, ready for hardware validation
