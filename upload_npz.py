import os
import subprocess

# === Config ===
# Use environment variable or default to ../output relative to script
LOCAL_DIR = os.environ.get("OUTPUT_DIR", os.path.join(os.path.dirname(__file__), "..", "output"))
REMOTE_DIR = os.environ.get("REMOTE_DIR", "gdrive:")  # your Drive folder

# === Upload all .npz files ===
for filename in os.listdir(LOCAL_DIR):
    if filename.endswith(".npz"):
        local_path = os.path.join(LOCAL_DIR, filename)
        print(f"Uploading {filename} to {REMOTE_DIR}...")
        subprocess.run(["rclone", "copy", local_path, REMOTE_DIR])

