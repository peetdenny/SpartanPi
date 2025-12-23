import numpy as np
import subprocess
import time
import os
import shutil
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["on", "off"], required=True)
args = parser.parse_args()


# --- Settings ---
sample_rate = 3_000_000       # Airspy Mini: 3 MSPS
sample_count = 100_000_000    # ~33s of data = ~382MB file

freq=1420.405751 	# MHz
fft_size = 8192               # FFT window size
bin_file = "capture.bin"

timestamp = time.strftime("%Y%m%d_%H%M%S")
npz_file = f"../output/spectrum_{timestamp}.npz"


# --- Step 1: Capture IQ data ---
print(f"Capturing {sample_count} samples...")
subprocess.run([
    "airspy_rx",
    "-b1",
    "-f", str(freq),
    "-a", str(sample_rate),
    "-n", str(sample_count),
    "-r", bin_file
], check=True)



print("Proceeding to step 2")
# --- Step 2: Process the .bin file ---
print("Processing FFT...")
chunk_samples = fft_size
spectrum_accum = np.zeros(fft_size)
n_chunks = 0

with open(bin_file, 'rb') as f:
    while True:
        data = np.frombuffer(f.read(chunk_samples * 4), dtype=np.int16)
        if len(data) < chunk_samples * 2:
            break
        iq = data[::2].astype(np.float32) + 1j * data[1::2].astype(np.float32)
	# DC offset removal (important)
        iq = iq - np.mean(iq)
        windowed = iq * np.hanning(chunk_samples)
        fft = np.fft.fftshift(np.fft.fft(windowed))
        spectrum_accum += np.abs(fft)**2
        n_chunks += 1

spectrum_accum /= max(n_chunks, 1)
freq_axis = np.fft.fftshift(np.fft.fftfreq(fft_size, d=1/sample_rate))

# --- Step 3: Save output to .npz ---
print(f"Saving result to {npz_file}...")
np.savez_compressed(
    npz_file,
    spectrum=spectrum_accum,
    freq_axis=freq_axis,
    sample_rate=sample_rate,
    fft_size=fft_size,
    averaging_windows=n_chunks,
    timestamp=timestamp,
    mode=args.mode
)

# --- Step 4: Clean up ---
print("Deleting raw .bin file...")
os.remove(bin_file)

print("Done ✅")
print(npz_file)


