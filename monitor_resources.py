import time
from datetime import datetime
import psutil
import subprocess

LOG_FILE = "resource_log.csv"

# Write header
with open(LOG_FILE, "w") as f:
    f.write("timestamp,cpu_temp_c,cpu_percent,mem_used_mb,mem_available_mb\n")

while True:
    # Get CPU temp
    temp_output = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
    cpu_temp = float(temp_output.strip().split('=')[1].split("'")[0])

    # Get CPU and memory info
    cpu_percent = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    used_mb = mem.used // (1024 * 1024)
    available_mb = mem.available // (1024 * 1024)

    # Log entry
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"{now},{cpu_temp},{cpu_percent},{used_mb},{available_mb}\n")

    time.sleep(60)  # Log every minute


