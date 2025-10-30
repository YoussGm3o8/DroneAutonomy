# AirSim Simulation Mode Guide

## Overview

DroneAutonomy can run in simulation mode using AirSim, allowing you to test the complete pipeline without a physical drone. This is useful for:

- Development and testing
- Algorithm validation
- Dataset generation
- Safe testing of new features
- Training and demonstrations

## Prerequisites

### 1. Install AirSim Python Package

```bash
pip install airsim
```

### 2. Download and Setup AirSim Simulator

#### Windows:
1. Download AirSim binary from: https://github.com/Microsoft/AirSim/releases
2. Extract to a folder (e.g., `C:\AirSim`)
3. Run the `.exe` file to start the simulator

#### Linux:
1. Download from releases or build from source
2. Follow instructions at: https://github.com/Microsoft/AirSim

### 3. Configure AirSim Settings

Create or edit `Documents/AirSim/settings.json`:

```json
{
  "SeeDocsAt": "https://github.com/Microsoft/AirSim/blob/main/docs/settings.md",
  "SettingsVersion": 1.2,
  "SimMode": "Multirotor",
  "ClockSpeed": 1,
  "ViewMode": "SpringArmChase",
  "Vehicles": {
    "Drone1": {
      "VehicleType": "SimpleFlight",
      "X": 0, "Y": 0, "Z": 0,
      "Yaw": 0,
      "Cameras": {
        "0": {
          "CaptureSettings": [
            {
              "ImageType": 0,
              "Width": 1920,
              "Height": 1080,
              "FOV_Degrees": 90,
              "AutoExposureSpeed": 100,
              "MotionBlurAmount": 0
            }
          ],
          "X": 0, "Y": 0, "Z": 0,
          "Pitch": 0, "Roll": 0, "Yaw": 0
        }
      }
    }
  }
}
```

## Running in Simulation Mode

### Option 1: Using the Test Script (Recommended)

```bash
# Basic simulation test
python examples/test_airsim_pipeline.py

# Fast mode (skip depth estimation)
python examples/test_airsim_pipeline.py --fast

# Fast mode with frame interval for maximum FPS
python examples/test_airsim_pipeline.py --fast --interval 2

# With frame limit
python examples/test_airsim_pipeline.py --max-frames 100

# Headless mode (no display)
python examples/test_airsim_pipeline.py --no-display
```

### Option 2: Using the Main Pipeline

```bash
# Using simulation config
python src/drone_autonomy/pipeline.py --config config/airsim_simulation.yaml

# With performance options
python src/drone_autonomy/pipeline.py --config config/airsim_simulation.yaml --fast --interval 2
```

## Configuration

### Simulation Config File: `config/airsim_simulation.yaml`

Key settings for simulation mode:

```yaml
# Enable simulation
simulation:
  enabled: true          # Must be true for AirSim mode
  ip: "127.0.0.1"       # AirSim server IP
  port: 41451           # Default AirSim port
  camera_name: "0"      # Camera to use
  auto_takeoff: false   # Auto takeoff on start
  takeoff_height: 5.0   # Takeoff height in meters

# MAVLink is disabled in simulation
mavlink:
  auto_detect: false    # Disable MAVLink in sim

# Video source is ignored (using AirSim)
video:
  # These settings are not used in simulation mode
  # AirSim provides images directly
```

## Features in Simulation Mode

### What Works:
✅ Camera image capture from AirSim
✅ IMU data from simulation
✅ Ground truth pose (position + orientation)
✅ YOLO object detection
✅ Target detection (red circles)
✅ Depth estimation
✅ VIO (Visual Inertial Odometry)
✅ All display and visualization features
✅ Performance modes (fast, interval)

### What's Different:
- Video comes from AirSim instead of RTSP/camera
- MAVLink is automatically disabled
- IMU data comes from simulation
- Can get ground truth pose for validation

### What's Disabled:
- MAVLink communication (not needed in sim)
- Physical drone control
- Real camera input

## Flight Control in Simulation

The AirSim interface provides basic flight control:

```python
from drone_autonomy.simulation.airsim_interface import AirSimInterface

# Connect
airsim = AirSimInterface(config)
airsim.connect()

# Takeoff
airsim.takeoff(timeout_sec=10.0)

# Get camera image
frame = airsim.get_camera_image()

# Get IMU data
imu_data = airsim.get_imu_data()

# Get ground truth
position, orientation = airsim.get_ground_truth_pose()

# Land
airsim.land(timeout_sec=10.0)

# Reset simulation
airsim.reset()

# Disconnect
airsim.disconnect()
```

## Performance in Simulation

Simulation mode typically achieves:

- **Normal mode**: 5-10 FPS (with depth)
- **Fast mode**: 12-18 FPS (no depth)
- **Fast + interval=2**: 20-30 FPS

Simulation is faster than real drone mode because:
1. No network latency (RTSP streaming)
2. No camera connection overhead
3. Direct memory access to images
4. Can run at fixed FPS

## Troubleshooting

### Problem: "Failed to initialize pipeline"

**Solutions:**
1. Make sure AirSim simulator is running
2. Check that AirSim is accessible at `127.0.0.1:41451`
3. Verify `simulation.enabled: true` in config
4. Try restarting the AirSim simulator

### Problem: "Could not connect to AirSim"

**Solutions:**
1. Check firewall settings
2. Ensure no other program is using port 41451
3. Try running AirSim with administrator privileges
4. Check AirSim console for errors

### Problem: "No camera image"

**Solutions:**
1. Verify camera settings in AirSim `settings.json`
2. Check camera name matches config (`camera_name: "0"`)
3. Ensure vehicle is spawned in AirSim
4. Try resetting the simulation

### Problem: Low FPS in simulation

**Solutions:**
1. Use `--fast` mode to skip depth estimation
2. Use `--interval 2` to process every other frame
3. Reduce AirSim graphics quality
4. Close other applications
5. Use `config/high_performance.yaml` for optimized settings

## Switching Between Simulation and Real Drone

### For Simulation:
```bash
python src/drone_autonomy/pipeline.py --config config/airsim_simulation.yaml
```

### For Real Drone:
```bash
python src/drone_autonomy/pipeline.py --config config/default_config.yaml
```

Or use auto-detection:
```bash
python src/drone_autonomy/pipeline.py
# Automatically uses config/default_config.yaml
```

## Development Workflow

### Recommended workflow:
1. **Develop in simulation**: Test algorithms safely in AirSim
2. **Validate with data**: Use simulation to generate test datasets
3. **Test performance**: Measure FPS and processing times
4. **Deploy to drone**: Switch to real drone config when ready

### Testing checklist:
- [ ] AirSim simulator running
- [ ] Pipeline connects successfully
- [ ] Camera images displaying correctly
- [ ] Detection working on simulation objects
- [ ] Target detection finding red objects (if present)
- [ ] FPS is acceptable for your use case
- [ ] All visualizations working

## Example: Full Simulation Session

```bash
# 1. Start AirSim simulator (run the .exe)

# 2. Wait for AirSim to load the environment

# 3. Run the test script
python examples/test_airsim_pipeline.py --fast

# 4. Observe the pipeline running
# - Camera feed from simulation
# - Detection boxes on objects
# - FPS counter
# - Target circles if red objects present

# 5. Press 'q' to quit when done

# 6. Check logs in logs/ directory
```

## Advanced: Custom AirSim Environments

You can use custom Unreal Engine environments with AirSim:

1. Create/download custom environment
2. Package with AirSim plugin
3. Configure `settings.json` for your environment
4. Run the custom environment
5. Use same DroneAutonomy config

See AirSim documentation for creating custom environments:
https://github.com/Microsoft/AirSim/blob/main/docs/unreal_custenv.md

## Integration with Other Tools

### Recording Data:
- Use AirSim's recording API to save flight data
- Capture images with timestamps
- Save for dataset creation

### Testing Algorithms:
- Generate reproducible scenarios in simulation
- Test edge cases safely
- Validate before real flight

### Training:
- Collect labeled data from simulation
- Train detection models
- Validate improvements in sim before deployment

## Summary

**To run in simulation mode:**
1. Install: `pip install airsim`
2. Launch AirSim simulator
3. Run: `python examples/test_airsim_pipeline.py --fast`

**Benefits:**
- Safe testing environment
- No drone hardware needed
- Reproducible scenarios
- Faster development cycle
- No risk of crashes

**Next Steps:**
- Test in simulation first
- Validate algorithms
- Then deploy to real drone with `config/default_config.yaml`
