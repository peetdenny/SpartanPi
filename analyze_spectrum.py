#!/usr/bin/env python3
"""
Quick analysis tool to view spectrum statistics from .npz files
Usage: python3 analyze_spectrum.py spectrum_20251224_143022.npz
"""

import numpy as np
import sys
import os

if len(sys.argv) < 2:
    print("Usage: python3 analyze_spectrum.py <npz_file>")
    print("\nExample: python3 analyze_spectrum.py ../output/spectrum_20251224_143022.npz")
    sys.exit(1)

npz_path = sys.argv[1]

if not os.path.exists(npz_path):
    print(f"Error: File not found: {npz_path}")
    sys.exit(1)

# Load the data
data = np.load(npz_path)

print("\n" + "="*60)
print(f"  Analysis of: {os.path.basename(npz_path)}")
print("="*60)

# Basic info
print("\n📊 OBSERVATION INFO:")
print(f"  Timestamp:     {data['timestamp']}")
print(f"  Mode:          {data['mode']} (antenna {'ON source' if data['mode'] == 'on' else 'OFF source'})")
print(f"  Sample Rate:   {data['sample_rate']/1e6:.1f} MSPS")
print(f"  FFT Size:      {data['fft_size']}")
print(f"  FFT Windows:   {data['averaging_windows']}")

# Hardware settings
print("\n⚙️  HARDWARE SETTINGS:")
print(f"  LNA Gain:      {data['lna_gain']} dB")
print(f"  Mixer Gain:    {data['mix_gain']} dB")
print(f"  VGA Gain:      {data['vga_gain']} dB")

# Signal quality
print("\n📡 SIGNAL QUALITY:")
print(f"  Peak Power:    {data['peak_power_db']:.1f} dB")
print(f"  Noise Floor:   {data['noise_floor_db']:.1f} dB")
print(f"  Median Power:  {data['median_power_db']:.1f} dB")
print(f"  SNR:           {data['snr_db']:.1f} dB", end="")
if data['snr_db'] > 10:
    print("  ✅ Excellent")
elif data['snr_db'] > 5:
    print("  ✅ Good")
elif data['snr_db'] > 3:
    print("  ⚠️  Fair")
else:
    print("  ❌ Poor")

# Frequency analysis
print("\n🔭 FREQUENCY ANALYSIS:")
print(f"  Peak at:       {data['peak_frequency_hz']/1e6:.6f} MHz")
print(f"  H-line (21cm): 1420.405751 MHz")
print(f"  Doppler Shift: {data['hydrogen_offset_khz']:+.2f} kHz")

# Convert frequency offset to velocity (using Doppler formula)
c = 299792.458  # Speed of light in km/s
velocity_km_s = (data['hydrogen_offset_khz'] / 1420405.751) * c
print(f"  Radial Velocity: {velocity_km_s:+.1f} km/s")
if abs(velocity_km_s) < 50:
    print("    (Low velocity - local hydrogen or Earth motion)")
elif abs(velocity_km_s) < 200:
    print("    (Galactic hydrogen)")
else:
    print("    (High velocity - galactic rotation or unusual source)")

# RFI assessment
print("\n📻 RFI ASSESSMENT:")
print(f"  RFI Indicator: {data['rfi_percentage']:.1f}% bins >10dB")
if data['rfi_percentage'] < 5:
    print("  Status:        ✅ Clean data (< 5%)")
elif data['rfi_percentage'] < 15:
    print("  Status:        ⚠️  Moderate RFI (5-15%)")
else:
    print("  Status:        ❌ High RFI (> 15%) - consider re-observation")

# Data size
print("\n💾 DATA SIZE:")
spectrum_size = data['spectrum'].nbytes / (1024 * 1024)
total_size = sum(data[k].nbytes for k in data.files) / (1024 * 1024)
print(f"  Spectrum:      {spectrum_size:.2f} MB")
print(f"  Total (all):   {total_size:.2f} MB")
print(f"  Compression:   ~{os.path.getsize(npz_path)/(1024*1024):.2f} MB on disk")

print("\n" + "="*60)

# List all available fields
print("\n📋 Available data fields:")
for key in sorted(data.files):
    value = data[key]
    if hasattr(value, 'shape'):
        if value.shape == ():
            print(f"  {key:25s} = {value}")
        else:
            print(f"  {key:25s} : array shape {value.shape}")
    else:
        print(f"  {key:25s} = {value}")

print()

