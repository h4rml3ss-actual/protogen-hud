

 # 🛠️ Phase 1 Build Order – Protogen HUD
 
 This document outlines the recommended order of implementation for building the HUD system, with justification for each step.
 
 ## ✅ 1. `camera.py` — Camera Feed First
 **Why:** This is the foundation — everything overlays on top of this.
 
 - Implement `CameraStream`
 - Use OpenCV to open the camera at 1280x720
 - Confirm it displays live fullscreen feed in `main.py`
 
 📦 *Testing Tip:* Write a minimal loop in `main.py` that displays the camera frame.
 
 ---
 
 ## ✅ 2. `draw_utils.py` + `theme.py` — Build Your Drawing Tools
 **Why:** All widgets will need these.
 
 - Implement `draw_text()` and `draw_bar()` in `draw_utils.py`
 - Define neon theme colors and font sizes in `theme.py`
 
 📦 *Testing Tip:* Use dummy text over the camera feed to test positioning and fonts.
 
 ---
 
 ## ✅ 3. `metrics.py` — System Stats
 **Why:** Easy to get going, good visual feedback, and no external hardware needed.
 
 - Use `psutil` to get CPU, RAM, temp, net I/O
 - Return a dictionary or dataclass
 
 📦 *Testing Tip:* Call `get_system_metrics()` from `main.py` and draw them in a loop.
 
 ---
 
 ## ✅ 4. `audio_visualizer.py` — Mic + Visuals
 **Why:** Builds off of `sounddevice`, starts giving a sense of interactivity.
 
 - Capture mic input
 - Compute FFT using NumPy
 - Draw circular bars using `draw_utils`
 
 📦 *Testing Tip:* Run it isolated and draw on a static frame before layering into the HUD.
 
 ---
 
 ## ✅ 5. `wifi_scanner.py` — Environmental Awareness
 **Why:** Visual + functional, helps test right-side widget layout.
 
 - Parse `iwlist wlan0 scan`
 - Return SSID, signal strength, channel, encryption
 - Handle malformed/empty outputs gracefully
 
 ---
 
 ## ✅ 6. `gps_tracker.py` — GPS + Compass
 **Why:** Slightly trickier but important for directional HUD feel.
 
 - Use GPSD Python bindings
 - Extract heading, lat/lon, and speed
 - Provide placeholder/demo data when GPS unavailable
 
 ---
 
 ## ✅ 7. `service_threads.py` — Wire It Together
 **Why:** Now that all modules work individually, run them concurrently.
 
 - Use Python threads to update:
   - Metrics
   - Audio stream
   - GPS data
   - Wi-Fi scan
 - Add graceful shutdown support using `threading.Event`
 
 ---
 
 ## ✅ 8. `main.py` — HUD Render Loop
 **Why:** Bring the pieces together!
 
 - Initialize all modules
 - In main loop:
   - Read camera frame
   - Call each draw function
   - Show final image with OpenCV
 
 ---
 
 ## 🧪 Final Test
 Run:
 
 ```bash
 python3 main.py
 ```
 
 ✅ You should see the live camera feed  
 ✅ Metrics on the left, Wi-Fi on right  
 ✅ Audio at top, GPS+Compass below metrics