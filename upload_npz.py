import os
import subprocess
import sys

# === Config ===
# Use environment variable or default to ../output relative to script
LOCAL_DIR = os.environ.get("OUTPUT_DIR", os.path.join(os.path.dirname(__file__), "..", "output"))
REMOTE_DIR = os.environ.get("REMOTE_DIR", "gdrive:")  # your Drive folder

# === Upload all .npz files ===
files_to_upload = [f for f in os.listdir(LOCAL_DIR) if f.endswith(".npz")]

if not files_to_upload:
    print("No .npz files found to upload.")
    sys.exit(0)

print(f"Found {len(files_to_upload)} file(s) to upload")
print(f"Destination: {REMOTE_DIR}\n")

upload_failed = False
successful_uploads = []
failed_uploads = []

for filename in files_to_upload:
    local_path = os.path.join(LOCAL_DIR, filename)
    print(f"Uploading {filename}... ", end="", flush=True)
    
    result = subprocess.run(
        ["rclone", "copy", local_path, REMOTE_DIR, "-v"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ FAILED")
        print(f"  Error: {result.stderr.strip()}")
        upload_failed = True
        failed_uploads.append(filename)
    else:
        print(f"✅ SUCCESS")
        successful_uploads.append(filename)

# Summary
print("\n" + "="*60)
print("UPLOAD SUMMARY")
print("="*60)
print(f"Successful: {len(successful_uploads)}/{len(files_to_upload)}")
print(f"Failed:     {len(failed_uploads)}/{len(files_to_upload)}")

if failed_uploads:
    print("\n❌ UPLOAD FAILED - Files will NOT be deleted:")
    for f in failed_uploads:
        print(f"  - {f}")
    print("\nFiles remain in:", LOCAL_DIR)
    sys.exit(1)  # Exit with error code to prevent deletion
else:
    print("\n✅ All uploads successful - safe to delete local files")
    sys.exit(0)

