#!/usr/bin/env python3
"""
Send periodic heartbeat pings to Astron00b backend
"""

import requests
import time
import os
import argparse
from datetime import datetime, timezone

# Configuration (can be overridden by environment variables)
NODE_ID = os.environ.get("NODE_ID", "Spartan-001")
BACKEND_URL = os.environ.get("BACKEND_URL", "https://astron00b.com")
HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL", "30"))  # seconds

def get_uptime_seconds():
    """Get system uptime in seconds"""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            return int(uptime_seconds)
    except:
        return None

def get_load_average():
    """Get system load average as string"""
    try:
        with open('/proc/loadavg', 'r') as f:
            load_parts = f.readline().split()[:3]
            return ' '.join(load_parts)
    except:
        return None

def send_heartbeat(node_id, backend_url, run_index=None, total_runs=None, last_capture=None):
    """
    Send a single heartbeat ping to the backend
    
    Args:
        node_id: Node identifier (e.g., "Spartan-001")
        backend_url: Base URL of the backend (e.g., "https://astron00b.com")
        run_index: Current run number (optional)
        total_runs: Total runs in batch (optional)
        last_capture: Last capture filename (optional)
    
    Returns:
        True if successful, False otherwise
    """
    url = f"{backend_url}/api/nodes/heartbeat/{node_id}"
    
    # Build payload
    payload = {
        "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }
    
    # Add optional fields
    uptime = get_uptime_seconds()
    if uptime is not None:
        payload["uptime_s"] = uptime
    
    load = get_load_average()
    if load is not None:
        payload["load"] = load
    
    if run_index is not None:
        payload["run_index"] = run_index
    
    if total_runs is not None:
        payload["total_runs"] = total_runs
    
    if last_capture is not None:
        payload["last_capture"] = last_capture
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Heartbeat failed: {e}")
        return False

def continuous_heartbeat(node_id, backend_url, interval=30):
    """
    Send heartbeats continuously at specified interval
    
    Args:
        node_id: Node identifier
        backend_url: Base URL of the backend
        interval: Seconds between heartbeats (default: 30)
    """
    print(f"Starting heartbeat service for {node_id}")
    print(f"Backend: {backend_url}")
    print(f"Interval: {interval}s")
    print("Press Ctrl+C to stop\n")
    
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        success = send_heartbeat(node_id, backend_url)
        
        if success:
            print(f"[{timestamp}] ✓ Heartbeat sent")
        else:
            print(f"[{timestamp}] ✗ Heartbeat failed")
        
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\nHeartbeat service stopped.")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send heartbeats to Astron00b backend")
    parser.add_argument("--node-id", default=NODE_ID, help=f"Node identifier (default: {NODE_ID})")
    parser.add_argument("--backend-url", default=BACKEND_URL, help=f"Backend URL (default: {BACKEND_URL})")
    parser.add_argument("--interval", type=int, default=HEARTBEAT_INTERVAL, help=f"Seconds between heartbeats (default: {HEARTBEAT_INTERVAL})")
    parser.add_argument("--once", action="store_true", help="Send single heartbeat and exit")
    
    args = parser.parse_args()
    
    if args.once:
        # Send single heartbeat
        success = send_heartbeat(args.node_id, args.backend_url)
        exit(0 if success else 1)
    else:
        # Continuous mode
        continuous_heartbeat(args.node_id, args.backend_url, args.interval)

