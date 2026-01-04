import argparse
import subprocess
import time
import os
import shutil
from datetime import datetime

# Import heartbeat functionality
try:
    from heartbeat import send_heartbeat
    HEARTBEAT_ENABLED = True
    NODE_ID = os.environ.get("NODE_ID", "Spartan-001")
    BACKEND_URL = os.environ.get("BACKEND_URL", "https://astron00b.com")
except ImportError:
    HEARTBEAT_ENABLED = False
    log("WARNING: heartbeat.py not found, heartbeat disabled")

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

def send_heartbeat_safe(run_index=None, total_runs=None, last_capture=None):
    """Send heartbeat with error handling (non-blocking)"""
    if not HEARTBEAT_ENABLED:
        return
    
    try:
        send_heartbeat(
            NODE_ID, 
            BACKEND_URL, 
            run_index=run_index, 
            total_runs=total_runs, 
            last_capture=last_capture
        )
    except Exception as e:
        # Don't fail the observation if heartbeat fails
        log(f"Heartbeat error (non-fatal): {e}")

def radio_down():
    if args.no_radio_silence:
        log("Radio silence SKIPPED (--no-radio-silence flag set)")
        return
    
    log("Radio silence ON: disabling wlan0 and eth0")
    for iface in ("wlan0", "eth0"):
        r = subprocess.run(["sudo", "ifconfig", iface, "down"], check=False, capture_output=True)
        if r.returncode != 0:
            log(f"  {iface} down → WARNING: failed (rc={r.returncode}) - continuing anyway")
        else:
            log(f"  {iface} down → OK")

def radio_up():
    if args.no_radio_silence:
        return
    
    log("Radio silence OFF: enabling eth0 and wlan0")
    subprocess.run(["sudo", "ifconfig", "eth0", "up"], check=False, capture_output=True)
    subprocess.run(["sudo", "ifconfig", "wlan0", "up"], check=False, capture_output=True)
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
parser.add_argument("--name", type=str, default="observation", help="Observation name for filename")
parser.add_argument("--no-radio-silence", action="store_true", help="Skip network disable (for laptops/systems without sudo)")
args = parser.parse_args()

# Fail fast if sudo will block
subprocess.run(["sudo", "-n", "true"], check=True)
CAPTURE_MIN_PER_RUN = 10
capture_timeout = 60 * CAPTURE_MIN_PER_RUN * args.runs

log(f"Capture timeout set to {capture_timeout//60} minutes")

# Send initial heartbeat
if HEARTBEAT_ENABLED:
    log(f"Heartbeat enabled: Node {NODE_ID} → {BACKEND_URL}")
    send_heartbeat_safe(run_index=0, total_runs=args.runs)

# Collect all captured files for batch upload at the end
captured_files = []

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
        npz_path = None  # Initialize to handle errors
        try:
            log(f"Starting capture (run {i+1}/{args.runs})")
            r=subprocess.run(
                ["python3", "capture_and_process.py", "--mode", args.mode, "--name", args.name],
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
            
            # Add to list for batch upload later
            if npz_path.endswith(".npz") and os.path.exists(npz_path):
                captured_files.append(npz_path)
            else:
                log(f"WARNING: Unexpected output path: {npz_path}")
                
        except subprocess.CalledProcessError as capture_error:
            # Show the actual error from capture script
            log(f"❌ Capture failed with exit code {capture_error.returncode}")
            if capture_error.stdout:
                log("=== Capture stdout ===")
                print(capture_error.stdout)
            if capture_error.stderr:
                log("=== Capture stderr ===")
                print(capture_error.stderr)
            raise  # Re-raise to trigger cleanup

        finally:
            # Always re-enable network even if capture fails
            radio_up()

        # Wait for network, then send heartbeat while network is up
        wait_for_network(max_seconds=45)
        
        # Send heartbeat with progress (network is now up) - only if capture succeeded
        if npz_path and npz_path.endswith(".npz") and os.path.exists(npz_path):
            send_heartbeat_safe(
                run_index=i+1, 
                total_runs=args.runs, 
                last_capture=os.path.basename(npz_path)
            )

        if i < args.runs - 1:
            log(f"Pausing for {args.pause} seconds before next run")
            time.sleep(args.pause)
    
    # ===== Batch Upload at the End =====
    if captured_files:
        log(f"\n{'='*60}")
        log(f"All captures complete. Starting batch upload of {len(captured_files)} files...")
        log(f"{'='*60}")
        
        wait_for_network(max_seconds=45)
        
        # Upload all files at once
        log("Uploading results...")
        subprocess.run(
            ["python3", "upload_npz.py"],
            check=True,
            timeout=60*20,  # 20 min safety for batch uploads
        )
        
        # ✅ Delete files only after successful upload
        log("Upload successful. Cleaning up local files...")
        total_size_mb = 0
        for npz_path in captured_files:
            if os.path.exists(npz_path):
                file_size_mb = os.path.getsize(npz_path) // (1024 * 1024)
                total_size_mb += file_size_mb
                os.remove(npz_path)
                log(f"  Deleted: {os.path.basename(npz_path)} ({file_size_mb} MB)")
            else:
                log(f"  WARNING: File not found: {npz_path}")
        
        log(f"Cleaned up {len(captured_files)} files ({total_size_mb} MB total)")
        
        # Log final disk space
        disk_after = check_disk_space()
        log(f"Final disk space: {disk_after['free_mb']} MB free")
        
        # Send final heartbeat
        send_heartbeat_safe(run_index=args.runs, total_runs=args.runs, last_capture="batch_complete")
    else:
        log("No files captured to upload.")

except subprocess.CalledProcessError as e:
    log(f"UPLOAD FAILED: {e.cmd} returned exit code {e.returncode}")
    log(f"❌ Files NOT deleted - they remain in ../output/")
    if captured_files:
        log(f"Protected files ({len(captured_files)}):")
        for f in captured_files:
            log(f"  - {os.path.basename(f)}")
    log("\nTo retry upload manually: python3 upload_npz.py")
    raise
except subprocess.TimeoutExpired as e:
    log(f"TIMEOUT: {e.cmd} exceeded {e.timeout}s")
    # Try to upload any captured files before exiting
    if captured_files:
        log(f"Attempting emergency upload of {len(captured_files)} captured files...")
        try:
            subprocess.run(["python3", "upload_npz.py"], timeout=60*20)
            log("Emergency upload successful")
        except Exception as upload_err:
            log(f"Emergency upload failed: {upload_err}")
            log(f"Files remain in ../output/: {[os.path.basename(f) for f in captured_files]}")
    raise
except Exception as e:
    log(f"ERROR encountered: {e}")
    # Try to upload any captured files before exiting
    if captured_files:
        log(f"Attempting emergency upload of {len(captured_files)} captured files...")
        try:
            subprocess.run(["python3", "upload_npz.py"], timeout=60*20)
            log("Emergency upload successful")
        except Exception as upload_err:
            log(f"Emergency upload failed: {upload_err}")
            log(f"Files remain in ../output/: {[os.path.basename(f) for f in captured_files]}")
    raise
finally:
    # Belt-and-braces: ensure network is up when script exits
    radio_up()
    log("Final cleanup: network forced ON")

