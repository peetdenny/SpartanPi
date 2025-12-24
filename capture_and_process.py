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
lna_gain = 0                  # Airspy LMA Gain = 0 dB (0-14 possible). Sawbird already has LNA gain
mix_gain = 5                  # Airspy Mix Gain = 5 dB (0-15 possible). 
vga_gain = 6                 # Airspy VGA Gain = 6 dB (0-15 possible). .
sample_count = 100_000_000    # ~33s of data = ~382MB file

freq=1420.405751 	# MHz
fft_size = 8192               # FFT window size
bin_file = "capture.bin"

timestamp = time.strftime("%Y%m%d_%H%M%S")
npz_file = f"../output/spectrum_{timestamp}.npz"


# --- Step 1: Capture IQ data ---
print("\n" + "="*50)
print("           CAPTURE CONFIGURATION")
print("="*50)
print(f"Frequency:       {freq} MHz (Hydrogen line)")
print(f"Sample Rate:     {sample_rate/1e6:.1f} MSPS")
print(f"Sample Count:    {sample_count:,} (~{sample_count/sample_rate:.0f}s)")
print(f"LNA Gain:        {lna_gain} dB")
print(f"Mixer Gain:      {mix_gain} dB")
print(f"VGA Gain:        {vga_gain} dB")
print(f"Output File:     {bin_file}")
print("="*50 + "\n")

print(f"Starting capture...")
airspy_rx_command = [
    "airspy_rx",
    "-b1",
    "-l", str(lna_gain),
    "-m", str(mix_gain),
    "-v", str(vga_gain),
    "-f", str(freq),
    "-a", str(sample_rate),
    "-n", str(sample_count),
    "-r", bin_file
]
subprocess.run(airspy_rx_command, check=True)



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

# --- Step 2.5: Calculate Spectrum Statistics ---
print("Calculating spectrum statistics...")

# 1. Peak signal strength
peak_power = np.max(spectrum_accum)
peak_power_db = 10 * np.log10(peak_power + 1e-10)  # Convert to dB, avoid log(0)

# 2. Noise floor estimate (use 25th percentile to avoid outliers)
noise_floor = np.percentile(spectrum_accum, 25)
noise_floor_db = 10 * np.log10(noise_floor + 1e-10)

# 3. Signal-to-noise ratio
snr_db = peak_power_db - noise_floor_db

# 4. Frequency of peak signal
peak_idx = np.argmax(spectrum_accum)
peak_frequency_hz = freq_axis[peak_idx]
peak_frequency_mhz = peak_frequency_hz / 1e6

# 5. Offset from hydrogen line (1420.405751 MHz)
hydrogen_line_hz = freq * 1e6  # Convert MHz to Hz
freq_offset_khz = (peak_frequency_hz - hydrogen_line_hz) / 1000

# 6. RFI detection - bins with power > 10 dB above noise floor
rfi_threshold = noise_floor * 10  # 10 dB = 10x power
strong_signals = spectrum_accum > rfi_threshold
num_strong_bins = np.sum(strong_signals)
rfi_percentage = (num_strong_bins / fft_size) * 100

# 7. Median power (another robustness metric)
median_power = np.median(spectrum_accum)
median_power_db = 10 * np.log10(median_power + 1e-10)

# Print statistics to console
print("\n" + "="*50)
print("           SPECTRUM STATISTICS")
print("="*50)
print(f"Peak Power:        {peak_power_db:>8.1f} dB")
print(f"Noise Floor:       {noise_floor_db:>8.1f} dB (25th percentile)")
print(f"Median Power:      {median_power_db:>8.1f} dB")
print(f"SNR:               {snr_db:>8.1f} dB")
print("-"*50)
print(f"Peak Frequency:    {peak_frequency_mhz:>12.6f} MHz")
print(f"Target (H-line):   {freq:>12.6f} MHz")
print(f"Frequency Offset:  {freq_offset_khz:>+11.2f} kHz")
print("-"*50)
print(f"FFT Windows:       {n_chunks:>8d}")
print(f"RFI Indicator:     {rfi_percentage:>8.1f}% bins >10dB")
if rfi_percentage < 5:
    print(f"RFI Assessment:    ✅ Clean (< 5%)")
elif rfi_percentage < 15:
    print(f"RFI Assessment:    ⚠️  Moderate (5-15%)")
else:
    print(f"RFI Assessment:    ❌ High (> 15%)")
print("="*50 + "\n")

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
    mode=args.mode,
    # Spectrum statistics
    peak_power_db=peak_power_db,
    noise_floor_db=noise_floor_db,
    median_power_db=median_power_db,
    snr_db=snr_db,
    peak_frequency_hz=peak_frequency_hz,
    hydrogen_offset_khz=freq_offset_khz,
    rfi_percentage=rfi_percentage,
    # Gain settings
    lna_gain=lna_gain,
    mix_gain=mix_gain,
    vga_gain=vga_gain
)

# --- Step 4: Clean up ---
print("Deleting raw .bin file...")
os.remove(bin_file)

print("Done ✅")
print(npz_file)


