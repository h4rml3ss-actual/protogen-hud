# Wi-Fi Adapter Calibration Guide

## Overview

The Wi-Fi adapter calibration feature helps you identify which USB Wi-Fi adapter is on the LEFT vs RIGHT side of your device. This is essential for accurate Wi-Fi direction finding and triangulation.

## Hardware Requirements

- Two USB Wi-Fi adapters with inline power switches (or USB hub with per-port power control)
- Adapters physically mounted on left and right sides of device
- Power switches accessible during startup

## Usage

### First Time Setup (Interactive Calibration)

1. Start the HUD application normally:
   ```bash
   python3 main.py
   ```

2. If Wi-Fi locator is enabled in config, you'll see the calibration prompt:
   ```
   === Wi-Fi Adapter Calibration ===
   ```

3. Follow the on-screen instructions:
   - Disconnect BOTH adapters (switches OFF)
   - Press Enter
   - Connect the RIGHT adapter (switch ON)
   - Press Enter
   - Connect the LEFT adapter (switch ON)
   - Press Enter
   - Enter adapter separation in cm (default: 15)

4. Calibration is saved to `.wifi_calibration.json` for future use

### Skip Calibration (Use Previous Configuration)

If you've already calibrated once, you can skip the calibration process:

```bash
python3 main.py --skip-calibration
```

This will load the previous calibration from `.wifi_calibration.json`.

### Automatic Timeout

If you don't respond to the calibration prompt within 30 seconds, the system will:
1. Try to load previous calibration
2. If no previous calibration exists, disable Wi-Fi locator service
3. Continue with other services

### Calibration Cancellation

Press `Ctrl+C` during the calibration prompt to:
1. Skip calibration
2. Try to load previous calibration
3. If no previous calibration exists, disable Wi-Fi locator service

## Calibration File

The calibration is stored in `.wifi_calibration.json` in the application directory:

```json
{
  "wifi_left_interface": "wlan1",
  "wifi_right_interface": "wlan2",
  "wifi_scan_interface": "wlan1",
  "adapter_separation_m": 0.15
}
```

You can manually edit this file if needed, but interactive calibration is recommended.

## Troubleshooting

### "No new interface detected"

**Possible causes:**
- Adapter is not powered on
- USB connection is loose
- Adapter is not recognized by the system

**Solutions:**
1. Check that the adapter power switch is ON
2. Try unplugging and replugging the USB adapter
3. Verify adapter is recognized: `lsusb`
4. Check wireless interfaces: `iw dev`

### "Using onboard wireless interface"

**Problem:** The calibration detected your onboard wireless (wlan0, wlp1s0) instead of USB adapters.

**Solution:**
1. Make sure onboard wireless is NOT connected during calibration
2. Use only USB Wi-Fi adapters for direction finding
3. Reserve onboard wireless for system connectivity

### Calibration file not loading

**Problem:** `--skip-calibration` doesn't work or says "No previous calibration found"

**Solution:**
1. Check that `.wifi_calibration.json` exists in the application directory
2. Verify the file is valid JSON
3. Run calibration again to create a fresh file

## Tips

- **Adapter Separation:** Measure the distance between adapter antennas accurately for best triangulation results
- **Typical Values:** 15-20cm for fursuit heads, adjust based on your setup
- **Power Switches:** Hardware power switches make calibration much easier than unplugging USB cables
- **Consistent Mounting:** Keep adapters in the same physical positions for consistent results

## Advanced: Manual Configuration

If you prefer not to use calibration, you can manually configure adapters in `config.py`:

```python
HUD_CONFIG = {
    "enable_wifi_locator": True,
    "wifi_left_interface": "wlan1",
    "wifi_right_interface": "wlan2",
    "wifi_scan_interface": "wlan1",
    "adapter_separation_m": 0.15,
}
```

However, USB enumeration can change between reboots, so calibration is recommended.
