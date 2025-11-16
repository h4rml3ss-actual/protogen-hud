# main.py
# Entrypoint: starts HUD and orchestrates modules

import cv2
import traceback
import subprocess
import time
import argparse
import json
import os
from camera import CameraStream
from shared_state import SharedState
from service_manager import ServiceManager
from hud_renderer import render_hud
from config import get_config, validate_config


def log_startup(message):
    """Log startup messages to both console and startup.log file."""
    with open("startup.log", "a") as f:
        f.write(message + "\n")
    print(message)


def get_wifi_interfaces():
    """
    Get list of wireless interfaces, filtering out onboard wireless.
    
    Uses 'iw dev' command to list all wireless interfaces and filters out
    common onboard wireless interface names (wlan0, wlp1s0, wlp*).
    
    Returns:
        list: List of wireless interface names (USB adapters only)
    """
    try:
        # Execute 'iw dev' command to list wireless interfaces
        result = subprocess.run(
            ['iw', 'dev'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            log_startup(f"Warning: 'iw dev' command failed: {result.stderr}")
            return []
        
        # Parse output to extract interface names
        interfaces = []
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line.startswith('Interface '):
                interface_name = line.split()[1]
                
                # Filter out onboard wireless interfaces
                # Keep only USB adapters (wlan1+, wlan2+, wlx*)
                if interface_name == 'wlan0':
                    continue
                if interface_name.startswith('wlp'):
                    continue
                
                interfaces.append(interface_name)
        
        return interfaces
        
    except subprocess.TimeoutExpired:
        log_startup("Warning: 'iw dev' command timed out")
        return []
    except FileNotFoundError:
        log_startup("Warning: 'iw' command not found. Install iw package.")
        return []
    except Exception as e:
        log_startup(f"Warning: Error getting Wi-Fi interfaces: {e}")
        return []


def find_new_interface(old_list, new_list):
    """
    Find the interface that appears in new_list but not in old_list.
    
    Args:
        old_list: List of interface names before adapter connection
        new_list: List of interface names after adapter connection
        
    Returns:
        str or None: The newly detected interface name, or None if no new interface found
    """
    for interface in new_list:
        if interface not in old_list:
            return interface
    return None


CALIBRATION_FILE = ".wifi_calibration.json"


def save_calibration(calibration_config):
    """
    Save calibration configuration to a temporary file.
    
    Args:
        calibration_config: Dict with adapter configuration
    """
    try:
        with open(CALIBRATION_FILE, 'w') as f:
            json.dump(calibration_config, f, indent=2)
        log_startup(f"Calibration saved to {CALIBRATION_FILE}")
    except Exception as e:
        log_startup(f"Warning: Could not save calibration: {e}")


def load_calibration():
    """
    Load calibration configuration from temporary file.
    
    Returns:
        dict or None: Calibration config if file exists, None otherwise
    """
    try:
        if os.path.exists(CALIBRATION_FILE):
            with open(CALIBRATION_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        log_startup(f"Warning: Could not load calibration: {e}")
    return None


def calibrate_wifi_adapters():
    """
    Interactive calibration workflow to identify left and right Wi-Fi adapters.
    
    Guides the user through connecting adapters one at a time using hardware
    power switches to reliably detect which USB interface corresponds to which
    physical adapter position.
    
    Returns:
        dict: Configuration dict with left_interface, right_interface, 
              scan_interface, and adapter_separation_m
    """
    print("\n" + "="*50)
    print("=== Wi-Fi Adapter Calibration ===")
    print("="*50)
    print("\nThis calibration will identify which USB Wi-Fi adapter")
    print("is on the LEFT vs RIGHT side of your device.")
    print("\nMake sure BOTH adapters are DISCONNECTED (switches OFF)")
    print("or unplugged before continuing.")
    input("\nPress Enter when ready...")
    
    # Get baseline interfaces (onboard wireless only)
    print("\nScanning for baseline interfaces...")
    baseline_interfaces = get_wifi_interfaces()
    if baseline_interfaces:
        print(f"Found existing interfaces: {', '.join(baseline_interfaces)}")
        print("WARNING: These should be disconnected for accurate calibration.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Calibration cancelled.")
            return None
    else:
        print("No USB Wi-Fi adapters detected (good - starting fresh)")
    
    # Detect RIGHT adapter
    print("\n" + "-"*50)
    print("Step 1: Connect the RIGHT adapter")
    print("-"*50)
    print("Connect the RIGHT adapter (switch ON or plug in USB)")
    input("Press Enter when connected...")
    
    print("Waiting for USB enumeration...")
    time.sleep(2)  # Wait for USB enumeration
    
    current_interfaces = get_wifi_interfaces()
    right_interface = find_new_interface(baseline_interfaces, current_interfaces)
    
    if right_interface:
        print(f"✓ Detected RIGHT adapter: {right_interface}")
    else:
        print("✗ ERROR: No new interface detected!")
        print(f"Current interfaces: {', '.join(current_interfaces) if current_interfaces else 'None'}")
        print("\nTroubleshooting:")
        print("- Make sure the adapter is powered on")
        print("- Try unplugging and replugging the USB adapter")
        print("- Check that the adapter is recognized by the system (lsusb)")
        return None
    
    # Detect LEFT adapter
    print("\n" + "-"*50)
    print("Step 2: Connect the LEFT adapter")
    print("-"*50)
    print("Connect the LEFT adapter (switch ON or plug in USB)")
    input("Press Enter when connected...")
    
    print("Waiting for USB enumeration...")
    time.sleep(2)  # Wait for USB enumeration
    
    current_interfaces = get_wifi_interfaces()
    left_interface = find_new_interface(baseline_interfaces + [right_interface], current_interfaces)
    
    if left_interface:
        print(f"✓ Detected LEFT adapter: {left_interface}")
    else:
        print("✗ ERROR: No new interface detected!")
        print(f"Current interfaces: {', '.join(current_interfaces) if current_interfaces else 'None'}")
        print("\nTroubleshooting:")
        print("- Make sure the adapter is powered on")
        print("- Try unplugging and replugging the USB adapter")
        print("- Check that the adapter is recognized by the system (lsusb)")
        return None
    
    # Prompt for adapter separation
    print("\n" + "-"*50)
    print("Step 3: Adapter Separation")
    print("-"*50)
    print("Enter the physical distance between the two adapters.")
    print("This is used for triangulation distance calculations.")
    print("Typical fursuit head width: 15-20cm")
    
    while True:
        separation_input = input("\nEnter adapter separation in cm (default 15): ").strip()
        if not separation_input:
            separation_cm = 15.0
            break
        
        try:
            separation_cm = float(separation_input)
            if separation_cm < 5.0 or separation_cm > 50.0:
                print(f"Warning: {separation_cm}cm is outside typical range (5-50cm)")
                response = input("Use this value anyway? (y/n): ")
                if response.lower() == 'y':
                    break
            else:
                break
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    adapter_separation_m = separation_cm / 100.0
    
    # Display calibration summary
    print("\n" + "="*50)
    print("=== Calibration Complete ===")
    print("="*50)
    print(f"RIGHT adapter: {right_interface}")
    print(f"LEFT adapter:  {left_interface}")
    print(f"Separation:    {separation_cm}cm ({adapter_separation_m}m)")
    print("="*50 + "\n")
    
    # Return configuration dict
    calibration_config = {
        "wifi_left_interface": left_interface,
        "wifi_right_interface": right_interface,
        "wifi_scan_interface": left_interface,  # Use left for primary scanning
        "adapter_separation_m": adapter_separation_m
    }
    
    # Save calibration for future use
    save_calibration(calibration_config)
    
    return calibration_config


def main():
    """Main orchestration function for the HUD system."""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Protogen HUD System')
    parser.add_argument(
        '--skip-calibration',
        action='store_true',
        help='Skip Wi-Fi adapter calibration and use previous configuration'
    )
    args = parser.parse_args()
    
    # Log startup message indicating HUD is starting
    log_startup("=== HUD Starting Up ===")
    
    # Load configuration from config module
    config = get_config()
    
    # Handle Wi-Fi adapter calibration if Wi-Fi locator is enabled
    if config.get('enable_wifi_locator', False):
        calibration_config = None
        
        if args.skip_calibration:
            # Try to load previous calibration
            log_startup("Skipping calibration, loading previous configuration...")
            calibration_config = load_calibration()
            
            if calibration_config:
                log_startup("Using previous calibration:")
                log_startup(f"  LEFT adapter:  {calibration_config.get('wifi_left_interface')}")
                log_startup(f"  RIGHT adapter: {calibration_config.get('wifi_right_interface')}")
                log_startup(f"  Separation:    {calibration_config.get('adapter_separation_m')}m")
            else:
                log_startup("WARNING: No previous calibration found!")
                log_startup("Please run calibration or disable Wi-Fi locator.")
                response = input("Run calibration now? (y/n): ")
                if response.lower() == 'y':
                    calibration_config = calibrate_wifi_adapters()
                else:
                    log_startup("Disabling Wi-Fi locator service.")
                    config['enable_wifi_locator'] = False
        else:
            # Run interactive calibration with timeout option
            log_startup("Wi-Fi locator enabled - adapter calibration required.")
            print("\nYou can skip calibration by pressing Ctrl+C within 30 seconds")
            print("or press Enter to start calibration now...")
            
            try:
                # Wait for user input with timeout
                import select
                import sys
                
                # Check if stdin is available (not in background/non-interactive mode)
                if sys.stdin.isatty():
                    print("Waiting for input (30 second timeout)...")
                    ready, _, _ = select.select([sys.stdin], [], [], 30)
                    
                    if ready:
                        input()  # Consume the Enter key
                        calibration_config = calibrate_wifi_adapters()
                    else:
                        log_startup("\nCalibration timeout - checking for previous configuration...")
                        calibration_config = load_calibration()
                        if calibration_config:
                            log_startup("Using previous calibration.")
                        else:
                            log_startup("No previous calibration found. Disabling Wi-Fi locator.")
                            config['enable_wifi_locator'] = False
                else:
                    # Non-interactive mode, try to load previous calibration
                    log_startup("Non-interactive mode detected, loading previous calibration...")
                    calibration_config = load_calibration()
                    if not calibration_config:
                        log_startup("No previous calibration found. Disabling Wi-Fi locator.")
                        config['enable_wifi_locator'] = False
                        
            except KeyboardInterrupt:
                log_startup("\nCalibration skipped by user.")
                calibration_config = load_calibration()
                if calibration_config:
                    log_startup("Using previous calibration.")
                else:
                    log_startup("No previous calibration found. Disabling Wi-Fi locator.")
                    config['enable_wifi_locator'] = False
            except Exception as e:
                log_startup(f"Error during calibration prompt: {e}")
                log_startup("Attempting to load previous calibration...")
                calibration_config = load_calibration()
                if not calibration_config:
                    log_startup("No previous calibration found. Disabling Wi-Fi locator.")
                    config['enable_wifi_locator'] = False
        
        # Apply calibration config if available
        if calibration_config:
            config.update(calibration_config)
    
    # Validate configuration and log warnings
    is_valid, warnings = validate_config(config)
    if warnings:
        log_startup("Configuration warnings:")
        for warning in warnings:
            log_startup(f"  - {warning}")
    
    # Log enabled services
    log_startup("Configuration:")
    log_startup(f"  System Metrics: {'Enabled' if config.get('enable_system_metrics') else 'Disabled'}")
    log_startup(f"  GPS: {'Enabled' if config.get('enable_gps') else 'Disabled'}")
    log_startup(f"  IMU: {'Enabled' if config.get('enable_imu') else 'Disabled'}")
    log_startup(f"  Wi-Fi Scanner: {'Enabled' if config.get('enable_wifi_scanner') else 'Disabled'}")
    log_startup(f"  Wi-Fi Locator: {'Enabled' if config.get('enable_wifi_locator') else 'Disabled'}")
    log_startup(f"  Audio: {'Enabled' if config.get('enable_audio') else 'Disabled'}")
    
    # Initialize SharedState instance
    log_startup("Initializing SharedState...")
    shared_state = SharedState()
    
    # Initialize CameraStream (no changes needed)
    log_startup("Initializing camera...")
    cam = CameraStream()
    
    # Initialize ServiceManager with shared_state and config
    log_startup("Initializing ServiceManager...")
    service_manager = ServiceManager(shared_state, config)
    
    # Call service_manager.start_all() to start all services
    log_startup("Starting services...")
    service_manager.start_all()
    
    # Create OpenCV window (keep existing code)
    log_startup("Creating OpenCV window...")
    cv2.namedWindow("HUD Camera Test", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("HUD Camera Test", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    # Begin the main loop to continuously capture and process frames for HUD display
    log_startup("Entering main loop...")
    try:
        while True:
            # Modify main loop to read frame from camera
            frame = cam.read()
            frame = cv2.rotate(frame, cv2.ROTATE_180)
            
            if frame is not None:
                # Modify main loop to call shared_state.get_snapshot()
                snapshot = shared_state.get_snapshot()
                
                # Modify main loop to call render_hud(frame, snapshot)
                frame = render_hud(frame, snapshot)
                
                # Display rendered frame (keep existing code)
                cv2.imshow("HUD Camera Test", frame)
            
            # Check for quit key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Quitting camera test.")
                break
                
    finally:
        # Cleanup: stop all services, camera stream, and close display windows
        log_startup("Shutting down...")
        
        # On shutdown, call service_manager.stop_all()
        service_manager.stop_all()
        
        # Stop camera stream
        cam.stop()
        
        # Close OpenCV windows
        cv2.destroyAllWindows()
        
        log_startup("=== HUD Shutdown Complete ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Keep existing error logging
        with open("error.log", "w") as f:
            f.write("Unhandled exception occurred:\n")
            traceback.print_exc(file=f)
        print("An error occurred. See error.log for details.")
