# metrics.py
# Collects CPU, RAM, and other system metrics

import psutil

def read_cpu_temp():
    try:
        # Open the system file that contains the CPU temperature in millidegrees Celsius
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            millideg = int(f.read().strip())
            # Convert millidegrees to degrees Celsius and return
            return millideg / 1000.0  # Convert to Celsius
    except Exception:
        # If reading the temperature fails, return "N/A"
        return "N/A"

def get_system_metrics():
    metrics = {}

    # Get the current system-wide CPU utilization as a percentage
    metrics["CPU"] = psutil.cpu_percent(interval=None)

    # Get the current RAM usage as a percentage of total available memory
    metrics["RAM"] = psutil.virtual_memory().percent

    # Get the CPU temperature in degrees Celsius
    metrics["Temp"] = read_cpu_temp()

    # Get network I/O statistics: total bytes sent and received since boot
    net_io = psutil.net_io_counters()
    # Convert bytes sent to kilobytes and store in metrics
    metrics["Net_Sent"] = net_io.bytes_sent / 1024
    # Convert bytes received to kilobytes and store in metrics
    metrics["Net_Recv"] = net_io.bytes_recv / 1024

    # Return the dictionary containing all collected metrics
    return metrics
