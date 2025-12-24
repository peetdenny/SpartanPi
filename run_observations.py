import argparse
import subprocess
import time
import os
import shutil
from datetime import datetime

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def check_disk_space(path="/"):
    """Check disk space and return stats in MB"""
    stat = shutil.disk_usage(path)
    total_mb = stat.total // (1024 * 1024)
    used_mb = stat.used // (1024 * 1024)
    free_mb = stat.free // (1024 * 1024)
    percent_used = (stat.used / stat.total) * 100
    return {
        'total_mb': total_mb,
        'used_mb': used_mb,
        'free_mb': free_mb,
        'percent_used': percent_used
    }

def radio_down():
    log("Radio silence ON: disabling wlan0 and eth0")
    for iface in ("wlan0", "eth0"):
        r = subprocess.run(["sudo", "ifconfig", iface, "down"], check=False)
        log(f"  {iface} down → rc={r.returncode}")

def radio_up():
    log("Radio silence OFF: enabling eth0 and wlan0")
    subprocess.run(["sudo", "ifconfig", "eth0", "up"], check=False)
    subprocess.run(["sudo", "ifconfig", "wlan0", "up"], check=False)
    log("Radio silence OFF (capture complete)")


def wait_for_network(max_seconds=30):
    """Wait until we can resolve DNS + ping something. Keeps it simple."""
    log("Waiting for network to come back...")
    deadline = time.time() + max_seconds
    while time.time() < deadline:
        # DNS resolution check (won't hang)
        r = subprocess.run(["getent", "hosts", "google.com"], capture_output=True, text=True)
        if r.returncode == 0:
            log("Network looks up (DNS OK).")
            return True
        time.sleep(1)
    log("WARNING: network did not look up within timeout (continuing anyway).")
    return False

parser = argparse.ArgumentParser()
parser.add_argument("--runs", type=int, default=1)
parser.add_argument("--pause", type=int, default=180)
parser.add_argument("--mode", choices=["on", "off"], required=True)
args = parser.parse_args()

# Fail fast if sudo will block
subprocess.run(["sudo", "-n", "true"], check=True)
CAPTURE_MIN_PER_RUN = 10
capture_timeout = 60 * CAPTURE_MIN_PER_RUN * args.runs

log(f"Capture timeout set to {capture_timeout//60} minutes")

try:
    for i in range(args.runs):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Check disk space before capture
        disk = check_disk_space()
        log(f"Disk space: {disk['free_mb']} MB free ({disk['percent_used']:.1f}% used)")
        
        # Warn if disk space is low
        if disk['free_mb'] < 1000:
            log(f"WARNING: Low disk space! Only {disk['free_mb']} MB remaining")
        if disk['free_mb'] < 500:
            log("ERROR: Critically low disk space (< 500 MB). Aborting.")
            raise RuntimeError(f"Insufficient disk space: {disk['free_mb']} MB free")
        
        log(f"Starting {args.mode} run {i+1}/{args.runs}")

        # Only silence during RF capture/processing
        radio_down()
        try:
            log(f"Radio silence ON (run {i+1}/{args.runs})")
            r=subprocess.run(
                ["python3", "capture_and_process.py", "--mode", args.mode],
                check=True,
                capture_output=True,
                text=True,
                timeout=capture_timeout,  
            )
            # Print captured output so it's visible in logs
            if r.stdout:
                for line in r.stdout.strip().splitlines():
                    print(line, flush=True)
            if r.stderr:
                for line in r.stderr.strip().splitlines():
                    print(line, flush=True)
            
            npz_path = r.stdout.strip().splitlines()[-1]
            log(f"Capture produced: {npz_path}")


        finally:
            # Always re-enable network even if capture fails
            radio_up()

        wait_for_network(max_seconds=45)

        # Now upload with network enabled + timeout so it can't hang forever
        log("Uploading results...")
        subprocess.run(
            ["python3", "upload_npz.py"],
            check=True,
            timeout=60*10,  # 10 min safety
        )
        
        # ✅ Delete only after successful upload
        if npz_path.endswith(".npz") and os.path.exists(npz_path):
            file_size_mb = os.path.getsize(npz_path) // (1024 * 1024)
            os.remove(npz_path)
            log(f"Deleted local file after upload: {npz_path} ({file_size_mb} MB)")
        else:
            log(f"WARNING: not deleting (path missing or not .npz): {npz_path}")
        
        # Log disk space after cleanup
        disk_after = check_disk_space()
        log(f"Disk space after cleanup: {disk_after['free_mb']} MB free")

        if i < args.runs - 1:
            log(f"Pausing for {args.pause} seconds before next run")
            time.sleep(args.pause)

except subprocess.TimeoutExpired as e:
    log(f"TIMEOUT: {e.cmd} exceeded {e.timeout}s")
    raise
except Exception as e:
    log(f"ERROR encountered: {e}")
    raise
finally:
    # Belt-and-braces: ensure network is up when script exits
    radio_up()
    log("Final cleanup: network forced ON")

