import time
from datetime import datetime
import psutil
import subprocess
import argparse

parser = argparse.ArgumentParser(description="Monitor system resources (CPU temp, CPU usage, memory)")
parser.add_argument("--once", action="store_true", help="Run once and output to console instead of continuous CSV logging")
parser.add_argument("--interval", type=int, default=60, help="Logging interval in seconds (default: 60)")
parser.add_argument("--log-file", type=str, default="resource_log.csv", help="CSV log file path (default: resource_log.csv)")
args = parser.parse_args()

def get_system_stats():
    """Collect system resource statistics"""
    # Get CPU temp
    temp_output = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
    cpu_temp = float(temp_output.strip().split('=')[1].split("'")[0])

    # Get CPU and memory info
    cpu_percent = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    used_mb = mem.used // (1024 * 1024)
    available_mb = mem.available // (1024 * 1024)
    total_mb = mem.total // (1024 * 1024)
    
    return {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'cpu_temp': cpu_temp,
        'cpu_percent': cpu_percent,
        'mem_used_mb': used_mb,
        'mem_available_mb': available_mb,
        'mem_total_mb': total_mb
    }

if args.once:
    # Single run mode - output to console
    stats = get_system_stats()
    print(f"System Resources at {stats['timestamp']}")
    print(f"  CPU Temperature: {stats['cpu_temp']:.1f}°C")
    print(f"  CPU Usage:       {stats['cpu_percent']:.1f}%")
    print(f"  Memory Used:     {stats['mem_used_mb']} MB / {stats['mem_total_mb']} MB ({stats['mem_used_mb']/stats['mem_total_mb']*100:.1f}%)")
    print(f"  Memory Available: {stats['mem_available_mb']} MB")
else:
    # Continuous logging mode - write to CSV
    LOG_FILE = args.log_file
    
    # Write header
    with open(LOG_FILE, "w") as f:
        f.write("timestamp,cpu_temp_c,cpu_percent,mem_used_mb,mem_available_mb\n")
    
    print(f"Logging system resources to {LOG_FILE} every {args.interval} seconds...")
    print("Press Ctrl+C to stop.")
    
    try:
        while True:
            stats = get_system_stats()
            
            # Log to CSV
            with open(LOG_FILE, "a") as f:
                f.write(f"{stats['timestamp']},{stats['cpu_temp']},{stats['cpu_percent']},{stats['mem_used_mb']},{stats['mem_available_mb']}\n")
            
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\nStopped logging. Data saved to {LOG_FILE}")


