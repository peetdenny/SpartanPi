# SpartanPi - Radio Astronomy Data Collection Node

This project automates radio astronomy data collection for the [Astron00b network](https://astron00b.com). It captures hydrogen line (21cm) radio signals at 1420.405751 MHz using an Airspy SDR, processes them with FFT, and uploads the results for analysis.

## 🌌 Overview

The SpartanPi system performs automated radio astronomy observations by:
1. **Capturing** raw IQ data from an Airspy Mini SDR
2. **Processing** the data with FFT to generate power spectra
3. **Uploading** compressed results (.npz files) to Google Drive
4. **Managing** RF interference by disabling WiFi/Ethernet during observations

## 📋 Prerequisites

### Hardware
- **Raspberry Pi** (or similar Linux computer)
- **Airspy Mini SDR** (or compatible Airspy device)
- **Radio antenna** tuned for 1420 MHz (hydrogen line)
- Stable internet connection for uploads

### Software Dependencies

```bash
# Install Airspy tools
sudo apt-get update
sudo apt-get install airspy

# Install Python dependencies
sudo apt-get install python3 python3-pip
pip3 install numpy psutil

# Install rclone for Google Drive uploads
curl https://rclone.org/install.sh | sudo bash
```

### Setup Google Drive Upload

1. Configure rclone with your Google Drive:
```bash
rclone config
```

2. Follow the prompts to:
   - Create a new remote called `gdrive`
   - Choose Google Drive as the storage type
   - Authorize your Google account

3. Verify the connection:
```bash
rclone lsd gdrive:
```

### Directory Structure

Create the output directory:
```bash
mkdir -p ~/output
# Or create it relative to the project:
# mkdir -p ../output
```

Your project structure should look like:
```
SpartanPi/
├── capture_and_process.py    # Core capture + FFT processing
├── run_observations.py        # Orchestrates multiple runs
├── upload_npz.py             # Uploads to Google Drive
├── observe.sh                # Wrapper script with logging
├── analyze_spectrum.py       # View statistics from .npz files
├── monitor_resources.py      # (Optional) System monitoring
├── turn_off_bias_T.sh        # Disables Airspy bias-T
├── logs/                     # Created automatically
└── README.md

output/                        # Created one level up from project
└── (collected .npz files)
```

### Permissions

The system needs sudo permissions to toggle network interfaces:
```bash
# Test sudo access (should not prompt for password)
sudo -n true
```

If it prompts for a password, configure passwordless sudo for network commands:
```bash
sudo visudo
```

Add this line (replace `youruser` with your username):
```
youruser ALL=(ALL) NOPASSWD: /sbin/ifconfig
```

## 🚀 Usage

### Basic Data Collection

#### Single Observation (ON mode)
Capture data with the antenna pointed at a radio source:
```bash
cd ~/dev/SpartanPi  # or wherever you cloned the project
python3 capture_and_process.py --mode on
```

#### Single Observation (OFF mode)
Capture background/reference data with antenna pointed away:
```bash
python3 capture_and_process.py --mode off
```

### Automated Multiple Runs

For unattended data collection with automatic uploads:

```bash
# 5 ON observations with 3-minute pauses between runs
./observe.sh --runs 5 --pause 180 --mode on

# Single OFF observation
./observe.sh --runs 1 --mode off
```

**Parameters:**
- `--runs N`: Number of observations to collect (default: 1)
- `--pause N`: Seconds to wait between runs (default: 180)
- `--mode on|off`: Antenna mode (ON = pointing at source, OFF = reference)

### What Happens During a Run

1. **Radio Silence ON**: WiFi and Ethernet are disabled to eliminate RF interference
2. **Data Capture**: Airspy captures 100 million samples (~33 seconds at 3 MSPS)
3. **FFT Processing**: Data is processed with 8192-point FFT and averaged
4. **Statistics**: Signal quality metrics calculated (SNR, RFI, Doppler shift, etc.)
5. **Save Results**: Compressed .npz file saved to `../output/` directory
6. **Radio Silence OFF**: Network interfaces re-enabled
7. **Upload**: Results uploaded to Google Drive via rclone
8. **Cleanup**: Local .npz file deleted after successful upload

### Viewing Logs

Logs are saved to `logs/run_observations.log`:
```bash
tail -f logs/run_observations.log
```

### Analyzing Collected Data

View detailed statistics from any captured .npz file:
```bash
python3 analyze_spectrum.py ../output/spectrum_20251224_143022.npz
```

This displays:
- Signal quality metrics (SNR, noise floor, peak power)
- Doppler shift and radial velocity calculations
- RFI assessment
- Hardware settings used
- All available data fields

## 📊 Output Data Format

Each observation produces a compressed `.npz` file containing:

**Core Data:**
- `spectrum`: Averaged power spectrum data
- `freq_axis`: Frequency axis (Hz)
- `sample_rate`: 3,000,000 Hz (3 MSPS)
- `fft_size`: 8192 points
- `averaging_windows`: Number of FFT windows averaged
- `timestamp`: Capture timestamp (YYYYMMDD_HHMMSS)
- `mode`: "on" or "off"

**Spectrum Statistics:**
- `peak_power_db`: Peak signal strength (dB)
- `noise_floor_db`: Noise floor estimate (dB, 25th percentile)
- `median_power_db`: Median power level (dB)
- `snr_db`: Signal-to-noise ratio (dB)
- `peak_frequency_hz`: Frequency of peak signal (Hz)
- `hydrogen_offset_khz`: Offset from 1420.405751 MHz (kHz) - **Doppler shift!**
- `rfi_percentage`: RFI indicator (% of bins > 10dB above noise)

**Hardware Settings:**
- `lna_gain`: LNA gain used (dB)
- `mix_gain`: Mixer gain used (dB)
- `vga_gain`: VGA gain used (dB)

### File Naming Convention
```
spectrum_20251224_143022.npz
         ^^^^^^^^_^^^^^^
         date     time
```

### Understanding Spectrum Statistics

When each capture completes, you'll see output like:
```
==================================================
           SPECTRUM STATISTICS
==================================================
Peak Power:            42.3 dB
Noise Floor:           35.1 dB (25th percentile)
Median Power:          36.8 dB
SNR:                    7.2 dB
--------------------------------------------------
Peak Frequency:    1420.405821 MHz
Target (H-line):   1420.405751 MHz
Frequency Offset:      +0.07 kHz
--------------------------------------------------
FFT Windows:           12207
RFI Indicator:          3.2% bins >10dB
RFI Assessment:    ✅ Clean (< 5%)
==================================================
```

**What these mean:**
- **SNR > 5 dB**: Good signal detection
- **RFI < 5%**: Clean data, minimal interference
- **Frequency Offset**: Doppler shift from Earth's motion (velocity toward/away from source)
- **FFT Windows**: More windows = better noise reduction

## 🔧 Advanced Configuration

### Adjust Capture Settings

Edit `capture_and_process.py` to modify:
```python
sample_rate = 3_000_000       # Sampling rate (Hz)
sample_count = 100_000_000    # Total samples (~33s at 3 MSPS)
freq = 1420.405751            # Center frequency (MHz)
fft_size = 8192               # FFT window size
```

### System Resource Monitoring

**Quick check** - view current system status:
```bash
python3 monitor_resources.py --once
```

**Continuous monitoring** - log to CSV during long runs:
```bash
# Default: log every 60 seconds to resource_log.csv
python3 monitor_resources.py &

# Custom interval and log file
python3 monitor_resources.py --interval 30 --log-file my_resources.csv &
```

The `--once` flag is useful for checking system health before/after observations.

### Disable Airspy Bias-T

If using an LNA with bias-T power, turn it off with:
```bash
./turn_off_bias_T.sh
```

## 📡 Best Practices for Astron00b Nodes

### Observation Protocol

1. **ON Observations**: Point antenna at interesting radio sources
   - Galactic center
   - Hydrogen clouds
   - Jupiter (strong radio emitter)
   - Sun (during daytime)

2. **OFF Observations**: Point antenna away from sources
   - Used as reference/background measurements
   - Typically toward empty sky

3. **Data Collection Schedule**
   - Run ON observations pointing at your target
   - Collect OFF observations for comparison
   - Alternate between ON/OFF or do batches of each

### Typical Collection Session

```bash
# Morning: 10 ON observations of galactic center
./observe.sh --runs 10 --pause 180 --mode on

# Evening: 5 OFF observations (reference)
./observe.sh --runs 5 --pause 180 --mode off
```

### Cron Automation

For fully automated observations, add to crontab:
```bash
crontab -e
```

Example: Run observations every 6 hours:
```cron
0 */6 * * * cd $HOME/dev/SpartanPi && ./observe.sh --runs 3 --pause 180 --mode on >> $HOME/dev/SpartanPi/logs/cron.log 2>&1
```

## 🐛 Troubleshooting

### Airspy Not Found
```bash
# Check if device is detected
airspy_info

# Check USB permissions
lsusb
# Look for "Airspy"
```

### Network Not Coming Back Up
The script has a 45-second timeout waiting for network. If it fails:
```bash
# Manually restore network
sudo ifconfig eth0 up
sudo ifconfig wlan0 up
```

### Upload Failures
```bash
# Test rclone connection
rclone ls gdrive:

# Check output directory exists
ls -la ../output/
```

### Capture Timeout
Default timeout is 10 minutes per run. For slower systems, edit `run_observations.py`:
```python
CAPTURE_MIN_PER_RUN = 10  # Increase this value
```

## 📚 Technical Details

### Signal Processing Pipeline

1. **Capture**: Airspy samples at 3 MSPS with 12-bit precision
2. **IQ Conversion**: 16-bit signed integers → complex floats
3. **DC Removal**: Mean subtraction to eliminate DC offset
4. **Windowing**: Hanning window applied to reduce spectral leakage
5. **FFT**: 8192-point FFT with fftshift for centered spectrum
6. **Averaging**: Multiple FFT windows averaged for noise reduction
7. **Storage**: Compressed NumPy archive for efficient storage

### Why Radio Silence?

WiFi and Ethernet emit RF signals that contaminate the sensitive 1420 MHz measurements. By disabling network interfaces during capture, we ensure clean data. The network is re-enabled immediately after processing for uploads.

## 🤝 Contributing to Astron00b

Your observations help build a distributed radio telescope network! Each node contributes to:
- Mapping hydrogen distribution in the Milky Way
- Tracking galactic rotation
- Measuring Doppler shifts
- Collaborative astronomy research

Visit [astron00b.com](https://astron00b.com) to learn more about the network.

## 📄 License

Open source - contribute and modify as needed for your Astron00b node!

## 🙏 Acknowledgments

Built for the Astron00b distributed radio astronomy network.

---

**Happy observing! 🔭📡**

