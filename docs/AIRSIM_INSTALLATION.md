# AirSim Installation Guide

This document provides step-by-step instructions for successfully installing AirSim in the DroneAutonomy project environment.

## Overview

AirSim is Microsoft's open-source simulator for drones and autonomous vehicles. It provides realistic simulation capabilities for testing computer vision and autonomy algorithms.

## Installation Challenges

AirSim 1.8.1 (the version available on PyPI) has some installation challenges with modern Python versions (3.12+) due to:
- Build-time dependency resolution issues
- Missing backports for older tornado versions
- Circular import dependencies during setup

## Successful Installation Steps

### Prerequisites

Ensure you have the following installed first:
```bash
pip install numpy>=1.24.0
pip install opencv-contrib-python>=4.8.0
```

### Step 1: Install AirSim Dependencies

Install the required dependencies in order:

```bash
# Install msgpack-rpc-python (AirSim's RPC framework)
pip install msgpack-rpc-python

# Install backports for SSL hostname matching (required by tornado 4.x)
pip install backports.ssl-match-hostname
```

### Step 2: Install AirSim with No Build Isolation

Due to the circular dependency issue, AirSim must be installed with the `--no-build-isolation` flag:

```bash
pip install --no-build-isolation airsim
```

This allows the installer to use the already-installed numpy and other packages during the build process.

### Complete Installation Command Sequence

For a fresh installation, run these commands in order:

```bash
# 1. Core dependencies
pip install numpy>=1.24.0
pip install opencv-contrib-python>=4.8.0

# 2. AirSim dependencies
pip install msgpack-rpc-python
pip install backports.ssl-match-hostname

# 3. AirSim itself
pip install --no-build-isolation airsim
```

## Verification

Verify the installation:

```python
import airsim
print(f"AirSim version: {airsim.__version__}")
print("AirSim successfully imported!")
```

Expected output:
```
AirSim version: 1.8.1
AirSim successfully imported!
```

## Testing with AirSim Simulator

### 1. Download and Run AirSim

Download the AirSim simulator for your platform:
- **Windows**: [Download Neighborhood Environment](https://github.com/Microsoft/AirSim/releases)
- **Linux**: Build from source or use pre-built binaries

### 2. Configure AirSim Settings

Create or edit `~/Documents/AirSim/settings.json`:

```json
{
  "SettingsVersion": 1.2,
  "SimMode": "Multirotor",
  "ViewMode": "SpringArmChase",
  "Vehicles": {
    "Drone1": {
      "VehicleType": "SimpleFlight",
      "X": 0, "Y": 0, "Z": 0,
      "Cameras": {
        "front_center": {
          "CaptureSettings": [
            {
              "ImageType": 0,
              "Width": 1920,
              "Height": 1080,
              "FOV_Degrees": 90
            }
          ]
        }
      }
    }
  }
}
```

### 3. Run Test Script

```bash
python examples/test_airsim.py
```

## Common Issues and Solutions

### Issue 1: "ModuleNotFoundError: No module named 'numpy'"

**Solution**: Install numpy before AirSim:
```bash
pip install numpy>=1.24.0
```

### Issue 2: "ModuleNotFoundError: No module named 'backports.ssl_match_hostname'"

**Solution**: Install the backports package:
```bash
pip install backports.ssl-match-hostname
```

### Issue 3: "Getting requirements to build wheel did not run successfully"

**Solution**: Use the `--no-build-isolation` flag:
```bash
pip install --no-build-isolation airsim
```

### Issue 4: "Connection refused" when running test

**Cause**: AirSim simulator is not running

**Solution**:
1. Launch the AirSim simulator executable
2. Ensure it's listening on port 41451 (default)
3. Verify firewall settings allow localhost connections

## Integration with DroneAutonomy

The DroneAutonomy pipeline includes an AirSim interface module at:
- `src/drone_autonomy/simulation/airsim_interface.py`

Enable AirSim simulation in `config/default_config.yaml`:

```yaml
simulation:
  enabled: true
  airsim_ip: 127.0.0.1
  airsim_port: 41451
```

## Alternative: Using AirSim with ROS

For ROS integration, see:
- [AirSim ROS Wrapper](https://microsoft.github.io/AirSim/airsim_ros_pkgs/)

## Dependencies Installed

The following packages are installed for AirSim support:
- `airsim==1.8.1` - Main AirSim Python client
- `msgpack-rpc-python==0.4.1` - RPC communication framework
- `msgpack-python==0.5.6` - MessagePack serialization (dependency)
- `tornado==4.5.3` - Async networking library (dependency)
- `backports.ssl-match-hostname==3.7.0.1` - SSL hostname matching backport

## References

- [AirSim GitHub Repository](https://github.com/Microsoft/AirSim)
- [AirSim Documentation](https://microsoft.github.io/AirSim/)
- [AirSim Python APIs](https://microsoft.github.io/AirSim/apis/)
- [AirSim Settings](https://microsoft.github.io/AirSim/settings/)

## Status

✅ **AirSim 1.8.1 successfully installed and verified**

Installation Date: October 30, 2025  
Python Version: 3.13  
Platform: Windows 11
