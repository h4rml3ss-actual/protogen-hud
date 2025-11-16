# Wi-Fi Adapter Calibration - Quick Start

## 🚀 First Time Setup (3 minutes)

1. **Start the HUD:**
   ```bash
   python3 main.py
   ```

2. **Follow the prompts:**
   - Disconnect BOTH adapters → Press Enter
   - Connect RIGHT adapter → Press Enter
   - Connect LEFT adapter → Press Enter
   - Enter separation in cm (default: 15) → Press Enter

3. **Done!** Calibration saved to `.wifi_calibration.json`

## 🔄 Subsequent Runs

**Option 1: Skip calibration (recommended)**
```bash
python3 main.py --skip-calibration
```

**Option 2: Let it timeout**
```bash
python3 main.py
# Wait 30 seconds or press Ctrl+C
# Uses previous calibration automatically
```

## ⚡ Quick Commands

| Command | Description |
|---------|-------------|
| `python3 main.py` | Run with calibration prompt |
| `python3 main.py --skip-calibration` | Skip calibration, use previous |
| `python3 main.py --help` | Show help |

## 🔧 Troubleshooting

**"No new interface detected"**
- Check adapter power switch is ON
- Try unplugging and replugging USB
- Run `lsusb` to verify adapter is recognized

**"No previous calibration found"**
- Run calibration once: `python3 main.py`
- Or manually create `.wifi_calibration.json`

**Need to recalibrate?**
- Delete `.wifi_calibration.json`
- Run `python3 main.py` again

## 📋 Hardware Requirements

- ✅ Two USB Wi-Fi adapters
- ✅ Power switches (or USB hub with per-port power)
- ✅ Adapters mounted on LEFT and RIGHT sides
- ✅ Know the distance between adapters (typically 15-20cm)

## 💡 Pro Tips

- Use hardware power switches for easy calibration
- Measure adapter separation accurately for best results
- Keep adapters in same physical positions
- Don't use onboard wireless (wlan0) for direction finding

---

**Need more help?** See `WIFI_CALIBRATION_GUIDE.md` for detailed documentation.
