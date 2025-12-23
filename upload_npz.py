import os
import subprocess

# === Config ===
LOCAL_DIR = "/home/denny/output"  # or wherever you store your npz files
REMOTE_DIR = "gdrive:"     # your Drive folder

# === Upload all .npz files ===
for filename in os.listdir(LOCAL_DIR):
    if filename.endswith(".npz"):
        local_path = os.path.join(LOCAL_DIR, filename)
        print(f"Uploading {filename} to {REMOTE_DIR}...")
        subprocess.run(["rclone", "copy", local_path, REMOTE_DIR])

