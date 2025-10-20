# rfgen — Universal RF Signal Generator

## Overview

**rfgen** is a cross-platform RF signal generator for testing and development. It generates continuous RF signals for various standards and protocols using software-defined radio hardware (HackRF, PlutoSDR) or file output for offline analysis.

**WARNING:** This tool generates radio frequency signals. Unauthorized transmission on many frequencies is illegal and may violate local regulations. Use only in shielded test environments or with appropriate licensing.

## UI Pages

The application is organized into thematic tabs:

### 1. Basic (General Signal Generator)

**Purpose:** Generate continuous test signals without protocol encoding.

**Features:**
- Carrier/AM/FM/PM modulation
- Patterns: Tone, Sweep, Noise, FF00, F0F0, 3333, 5555
- Configurable frequency, gain, IF offset
- Loop mode for continuous transmission

**Use Cases:**
- Testing SDR receivers
- Signal chain debugging
- Carrier/tone generation
- Bit pattern transmission

### 2. AIS (Automatic Identification System)

**Purpose:** Generate AIS signals for maritime vessel tracking.

**Features:**
- Channel A (161.975 MHz) / Channel B (162.025 MHz)
- GMSK modulation (9600 bps, BT≈0.4)
- MMSI and payload configuration
- Test patterns for continuous transmission

**Frequency:** 161.975 / 162.025 MHz
**Legal Notice:** AIS is a maritime safety system. Unauthorized transmission may interfere with navigation and is illegal.

### 3. 406 MHz (COSPAS-SARSAT Beacon)

**Purpose:** Generate 406 MHz emergency beacon signals for testing SAR equipment.

**Features:**
- BPSK modulation
- Beacon ID configuration
- FEC and interleaving
- Test mode with patterns

**Frequency:** 406.025 / 406.028 / 406.037 MHz
**Legal Notice:** 406 MHz is reserved for emergency distress beacons. Use ONLY in shielded test environment. Unauthorized transmission is a serious offense and may trigger search and rescue operations.

**Default Backend:** FileOut (safe mode) - recommends offline analysis only.

### 4. DSC VHF (Digital Selective Calling - VHF)

**Purpose:** Generate DSC VHF signals for maritime distress and calling.

**Features:**
- Channel 70 (156.525 MHz)
- Distress, Urgency, Safety, Routine calls
- MMSI addressing
- FSK modulation (170 Hz shift, 100 Bd)

**Frequency:** 156.525 MHz
**Legal Notice:** DSC Channel 70 is reserved for distress and safety communications. Unauthorized transmission may interfere with maritime safety and is illegal.

### 5. DSC HF (Digital Selective Calling - HF)

**Purpose:** Generate DSC HF signals for long-range maritime communication.

**Features:**
- Multiple HF frequencies (2, 4, 6, 8, 12, 16 MHz)
- Similar functionality to DSC VHF
- ITU-R M.541 compliance

**Frequencies:** 2187.5, 4207.5, 6312, 8414.5, 12577, 16804.5 kHz
**Legal Notice:** HF DSC frequencies are for maritime distress and safety. Unauthorized use is illegal.

### 6. NAVTEX (Navigational Telex)

**Purpose:** Generate NAVTEX signals for maritime navigational and meteorological warnings.

**Features:**
- 518 kHz (International) / 490 kHz (National) / 4209.5 kHz (HF)
- SITOR-B encoding
- FSK modulation (170 Hz shift, 100 Bd)
- Text message input or file import

**Frequencies:** 490, 518 kHz, 4209.5 kHz
**Legal Notice:** NAVTEX frequencies are for official maritime safety broadcasts. Unauthorized transmission is illegal.

### 7. 121.5 MHz (Emergency Locator Beacon)

**Purpose:** Generate 121.5 MHz emergency beacon signals for aviation SAR testing.

**Features:**
- Swept tone (300-1600 Hz) or continuous tone
- AM modulation
- Configurable sweep rate and depth

**Frequency:** 121.5 MHz
**Legal Notice:** 121.5 MHz is an international aviation emergency frequency. Use ONLY in shielded test environment. Unauthorized transmission may trigger emergency responses and is a serious offense.

### 8. Profiles (Profile Manager)

**Purpose:** Manage signal configuration profiles.

**Features:**
- List all profiles from `rfgen/profiles/`
- Load, Duplicate, Rename, Delete operations
- Import/Export profiles
- JSON preview with validation
- Migration from legacy profile locations

**Use Cases:**
- Save frequently used configurations
- Share configurations between systems
- Quick recall of test scenarios

### 9. Logs (Log Viewer & Diagnostics)

**Purpose:** View logs and system diagnostics.

**Features:**
- View logs from `rfgen/logs/`
- System diagnostics (Python version, HackRF utilities, running processes)
- Auto-refresh/tail mode
- Kill all hackrf_transfer processes
- Clear logs with confirmation
- Open logs folder in Explorer

**Use Cases:**
- Debug transmission issues
- Monitor HackRF processes
- Check system configuration

## Backends

### HackRF

Uses `hackrf_transfer` utility in loop mode (`-R` flag) for continuous transmission.

**Parameters:**
- Center frequency (Hz)
- Sample rate (Hz)
- TX gain (0-47 dB)
- PA enable/disable

### FileOut

Writes IQ samples to files for offline analysis.

**Formats:**
- `.sc8` (int8 interleaved IQ) - default
- `.cf32` (float32 complex) - optional

## File Structure

```
rfgen/
  ui_qt/          # Qt application (PySide6)
  core/           # Signal generation core
  standards/      # Protocol implementations
  backends/       # Hardware backends
  utils/          # Utilities (paths, profile I/O, migration)
  profiles/       # JSON profiles (gitignored)
  out/            # IQ output files (gitignored)
  logs/           # Log files (gitignored)
```

## Profiles

Profiles are JSON files stored in `rfgen/profiles/`:

```json
{
  "schema": 1,
  "name": "test_signal",
  "standard": "basic",
  "modulation": {
    "type": "FM",
    "deviation_hz": 5000
  },
  "pattern": {
    "type": "Tone",
    "tone_hz": 1000
  },
  "schedule": {
    "mode": "loop",
    "duration_s": 1.0
  },
  "device": {
    "backend": "hackrf",
    "fs_tx": 2000000,
    "tx_gain_db": 30,
    "target_hz": 162025000,
    "if_offset_hz": -25000
  }
}
```

## Legal and Safety Warnings

**IMPORTANT:** Many frequencies generated by this tool are legally restricted:

- **Maritime frequencies (AIS, DSC, NAVTEX):** Reserved for vessel safety and navigation. Unauthorized transmission may interfere with maritime operations and is illegal.

- **Emergency frequencies (406 MHz, 121.5 MHz):** Reserved for distress beacons. Unauthorized transmission may trigger search and rescue operations, waste emergency resources, and is a serious criminal offense.

- **General radio spectrum:** Most frequency bands require licensing from your national telecommunications authority.

**Legal Use:**

- Shielded test environment (anechoic chamber, Faraday cage, RF-tight enclosure)
- Attenuated/dummy load connection
- Licensed amateur radio bands (with appropriate license)
- FileOut backend for offline analysis

**Before transmitting:**

1. Verify the frequency is legal to use in your jurisdiction
2. Ensure you have appropriate licensing
3. Use adequate shielding or attenuation
4. Verify no interference with safety systems

**Violations may result in:**

- Criminal prosecution
- Heavy fines
- Equipment confiscation
- Interference with safety-of-life services

## Installation

### Requirements

- Python 3.9+
- PySide6 (Qt6 bindings)
- numpy < 2.0
- HackRF utilities (if using HackRF backend)

### Setup

```bash
# Install dependencies
pip install -r rfgen/requirements.txt

# Run application
python -m rfgen.ui_qt.app

# Or use convenience script
app_rfgen.bat
```

## CLI Interface

A command-line interface is also available:

```bash
python -m rfgen.cli.rfgen_cli --fs 2000000 --mod FM --dev 5000 --pattern Tone --tone 1000 --outdir out --name test_frame
```

## Support

For issues and questions, see the main project README.

## License

See LICENSE file in project root.

---

**Remember:** With great power comes great responsibility. Use this tool ethically and legally.
