# DroneAutonomy - Real-Time Monocular Vision Pipeline

A comprehensive autonomous perception and decision support system for obstacle avoidance and target detection using a single monocular camera, integrating state estimation, depth perception, and object/marker detection suitable for non-GPS and GPS-degraded flight.

## Overview

DroneAutonomy provides a laptop-hosted real-time pipeline that consumes a GStreamer video stream, fuses vision outputs, and interfaces to the flight stack via MAVLink visual odometry and telemetry, enabling testing and flight with ArduPilot-based vehicles.

## System Requirements

### Hardware
- **GPU**: NVIDIA RTX 3060 or equivalent
- **Platform**: Windows laptop (compatible with Linux/macOS)
- **Camera**: Forward-facing RGB camera with stable exposure
- **Network**: Wi-Fi/UDP for MAVLink communication

### Software
- Python 3.8+
- **OpenCV with GStreamer support** (pre-compiled at `C:\opencv\build\bin\Release`)
- **GStreamer** (installed at `C:\gstreamer\1.0\msvc_x86_64\bin`)
- CUDA-capable GPU drivers
- Optional: TensorRT for optimized inference
- Optional: AirSim for simulation testing

## Quick Start

### 1. Setup Gazebo Video (First Time Only)

If you're using Gazebo simulation, run the automated setup:

```powershell
# Automated setup - installs GStreamer in WSL and configures NVIDIA GPU
powershell -ExecutionPolicy Bypass -File scripts/setup_gazebo_video.ps1
```

This will:
- Install GStreamer plugins in WSL
- Configure NVIDIA GPU acceleration for Gazebo
- Fix RTP video streaming issues
- Set up firewall rules

For manual setup or troubleshooting, see: `docs/GAZEBO_VIDEO_QUICK_REFERENCE.md`

### 2. Setup Virtual Environment

This project uses a virtual environment with automatic DLL path configuration for OpenCV and GStreamer:

```powershell
# Activate the environment (PowerShell)
.\activate_env.ps1

# Or use Command Prompt
activate_env.bat
```

The activation scripts will:
- Activate the Python virtual environment
- Configure OpenCV and GStreamer DLL paths automatically
- Prepare the environment for computer vision operations

### 3. Install Dependencies

Dependencies are already installed if you cloned this repository. To reinstall or update:

```bash
pip install -e .
```

### 3. Verify Setup

Test that OpenCV with GStreamer is working correctly:

```bash
python tests\test_dll_setup.py
```

You should see all tests pass with GStreamer backend available.

### 4. Run Examples

#### Real Drone Mode
```bash
# Test YOLO detection
python examples\test_yolo_detection.py

# Test depth estimation
python examples\test_depth_estimation.py

# Test obstacle avoidance visualization (Tesla-style)
python examples\test_obstacle_avoidance.py

# Test MAVLink object avoidance (NEW!)
python examples\simple_mavlink_avoidance.py
python examples\test_mavlink_avoidance.py

# Run basic pipeline with real drone
python examples\run_basic.py
```

#### Simulation Mode (AirSim)
```bash
# Test pipeline in AirSim simulation
python examples\test_airsim_pipeline.py

# Fast mode simulation (20+ FPS)
python examples\test_airsim_pipeline.py --fast --interval 2
```

For more details, see:
- [Virtual Environment Setup Guide](docs/VENV_SETUP.md)
- [AirSim Simulation Guide](docs/AIRSIM_SIMULATION.md)

## Features

### Core Capabilities

1. **Graphical User Interface** 🆕
   - Modern PyQt6-based control interface
   - Live video display with multiple overlay modes
   - Task selection and configuration
   - Media gallery for photos/videos/deliverables
   - Real-time telemetry monitoring
   - Results viewer with scoring and logs
   - See [GUI Documentation](src/drone_autonomy/gui/README.md)

2. **Video Input**
   - GStreamer pipeline support for H.264/H.265 over UDP
   - OpenCV fallback for standard camera input
   - Configurable resolution and frame rate

3. **Autonomous Navigation**
   - Obstacle avoidance using depth estimation
   - Target detection and tracking (red circular markers)
   - Camera centering with PID control
   - Safe approach with depth-based distance control
   - GPS/telemetry logging for each target
   - Automatic photo capture on target lock
   - See [Autonomous Mode Guide](docs/AUTONOMOUS_MODE.md)

3.5. **MAVLink Object Avoidance** 🆕
   - Real-time obstacle detection with depth estimation
   - Multi-path trajectory planning and evaluation
   - MAVLink velocity command execution for avoidance
   - Emergency stop on critical obstacles
   - Tesla-style visualization overlay
   - Comprehensive MAVLink command support (takeoff, land, RTL, waypoints)
   - Compatible with ArduPilot and PX4
   - See [MAVLink Object Avoidance Guide](docs/MAVLINK_OBJECT_AVOIDANCE.md)

4. **Competition Tasks** 🆕
   - Target Search with GPS logging
   - Waypoint Navigation
   - Obstacle Course
   - Precision Landing
   - Autonomous Wet-Capture with deliverables
   - Landmark-based target descriptions
   - See [Tasks Documentation](src/drone_autonomy/tasks/README.md)

5. **Visual Odometry (VIO)**
   - 6-DoF pose estimation using monocular camera
   - Feature-based visual odometry
   - IMU integration support (when available)
   - Compatible with VINS-Mono and ORB-SLAM3 backends

6. **Monocular Depth Estimation** 🔄 *Multiple Models Supported*
   - **Depth Anything V2** - State-of-the-art accuracy (Small/Base/Large variants)
   - **MiDaS DPT_SwinV2_T_256** - Fastest with local model (80-150 FPS, no download)
   - Real-time inference on NVIDIA GPUs
   - Switch models dynamically via GUI or config
   - Dense depth maps with superior accuracy
   - See [Depth Model Selection Guide](DEPTH_MODELS.md)

7. **Object Detection**
   - YOLO-based obstacle detection (YOLOv8)
   - TensorRT optimization support
   - Real-time inference on NVIDIA GPUs
   - Configurable confidence thresholds

8. **Target Detection**
   - Red circular target detection
   - HSV color thresholding
   - Hough Circle Transform
   - Robust against clutter

9. **Fusion and Decision Layer**
   - Combines depth and detection outputs
   - Computes keep-out regions
   - Target gate identification
   - Prioritizes close detections

10. **MAVLink Integration**
   - Visual odometry publication to ArduPilot
   - UDP-based telemetry
   - Compatible with ArduPilot VIO/VISO interface
   - Ground station communication

11. **Simulation Support**
   - AirSim integration
   - Safe testing environment
   - Dataset generation
   - Hardware-in-the-loop testing

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/YoussGm3o8/DroneAutonomy.git
cd DroneAutonomy
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Optional Components

#### TensorRT (for optimized YOLO inference)
Follow NVIDIA's installation guide: https://docs.nvidia.com/deeplearning/tensorrt/install-guide/index.html

#### AirSim (for simulation)
```bash
pip install airsim
```

## Quick Start

### GUI Mode (Recommended for Beginners) 🆕

Launch the graphical interface for interactive control:

```bash
# Quick start with demo mode (no hardware needed)
python examples/demo_gui.py

# Launch GUI with webcam
python launch_gui.py --video-source webcam

# Launch with RTSP stream
python launch_gui.py --video-source rtsp://192.168.1.100:8554/stream

# Launch with custom config
python launch_gui.py --config config/high_performance.yaml
```

**GUI Features:**
- 🎥 Live video with multiple overlay modes
- ⚙️ Task selection and configuration
- 📁 Media gallery (photos, videos, deliverables)
- 📊 Results viewer with scoring
- 📡 Real-time telemetry display

See [GUI Documentation](src/drone_autonomy/gui/README.md) for full details.

### Running Modes

DroneAutonomy supports two primary modes: **Real Drone** and **Simulation**.

#### Mode 1: Real Drone (RTSP Camera)

Use with physical drone and RTSP camera stream:

```bash
# Full pipeline with all features
python src/drone_autonomy/pipeline.py

# High-performance mode (20+ FPS)
python src/drone_autonomy/pipeline.py --fast --interval 2 --config config/high_performance.yaml

# Custom configuration
python src/drone_autonomy/pipeline.py --config config/default_config.yaml
```

**Features:**
- 1080p 60 FPS GStreamer RTSP input
- MAVLink telemetry (UDP/USB auto-detect)
- Visual odometry output
- Real-time obstacle detection

#### Mode 2: AirSim Simulation

Use for safe testing without physical drone:

```bash
# Basic simulation test
python examples/test_airsim_pipeline.py

# High-performance simulation (20+ FPS)
python examples/test_airsim_pipeline.py --fast --interval 2

# Direct pipeline usage with sim config
python src/drone_autonomy/pipeline.py --config config/airsim_simulation.yaml
```

**Features:**
- Safe testing environment
- Ground truth data available
- No MAVLink needed
- Reproducible scenarios

See [AirSim Simulation Guide](docs/AIRSIM_SIMULATION.md) for detailed setup.

### Performance Modes

For achieving 20+ FPS (both real drone and simulation):

```bash
# Fast mode: Skip depth estimation (2.4x speedup)
python src/drone_autonomy/pipeline.py --fast

# Frame interval: Process every 2nd frame (2x speedup)  
python src/drone_autonomy/pipeline.py --interval 2

# Combined: 15-25 FPS
python src/drone_autonomy/pipeline.py --fast --interval 2 --config config/high_performance.yaml
```

See [Usage Guide](docs/USAGE_GUIDE.md) for complete performance optimization details.

### Basic Usage

```bash
python -m drone_autonomy.pipeline --config config/default_config.yaml
```

### With Custom Configuration

```bash
python -m drone_autonomy.pipeline --config my_config.yaml
```

### Headless Mode (no display)

```bash
python -m drone_autonomy.pipeline --config config/default_config.yaml --no-display
```

## Configuration

The system is configured via YAML files. See `config/default_config.yaml` for a complete example.

### Key Configuration Sections

#### Video Input
```yaml
video:
  gstreamer_pipeline: "udpsrc port=5600 ! ..."
  width: 1280
  height: 720
  fps: 30
```

#### Camera Calibration
```yaml
camera:
  fx: 500.0
  fy: 500.0
  cx: 640.0
  cy: 360.0
```

#### Depth Estimation
```yaml
depth:
  model: depth_anything_v2_vits
  device: cuda
```

#### Object Detection
```yaml
detection:
  yolo_model: yolov8n.pt
  confidence_threshold: 0.5
  use_tensorrt: false
```

#### MAVLink
```yaml
mavlink:
  connection_string: "udp:127.0.0.1:14550"
  vio_publish_rate: 30
```

## Camera Calibration

Camera calibration is essential for accurate VIO and metric depth estimation.

### Using Chessboard Pattern

1. Print a chessboard calibration pattern
2. Capture multiple images from different angles
3. Run calibration:

```python
from drone_autonomy.utils.camera_calibration import CameraCalibration

calib = CameraCalibration()
calib.calibrate_from_chessboard(
    images_path='calibration_images',
    pattern_size=(9, 6),
    square_size=0.025  # 25mm squares
)
calib.save_to_file('config/camera_calibration.json')
```

## MAVLink Integration

### ArduPilot Configuration

1. Enable visual odometry in ArduPilot:
   ```
   EK3_SRC1_POSXY = 6 (ExternalNav)
   EK3_SRC1_VELXY = 6 (ExternalNav)
   EK3_SRC1_POSZ = 1 (Baro)
   VISO_TYPE = 1 (MAV)
   ```

2. Configure MAVLink connection in `config.yaml`:
   ```yaml
   mavlink:
     connection_string: "udp:192.168.1.10:14550"
   ```

3. Start the pipeline - it will automatically publish VIO data

## Simulation with AirSim

### Setup

1. Install and launch AirSim
2. Enable simulation in configuration:
   ```yaml
   simulation:
     enabled: true
     airsim_ip: 127.0.0.1
   ```

3. Run the pipeline:
   ```bash
   python -m drone_autonomy.pipeline --config config/default_config.yaml
   ```

### Autonomous Navigation Mode 🆕

Enable fully autonomous obstacle avoidance and target approach:

```bash
# Basic autonomous mode
python -m drone_autonomy.pipeline --autonomous

# With performance mode (recommended: balanced 18 FPS)
python -m drone_autonomy.pipeline --autonomous --interval 2

# Test autonomous with example script
python examples\test_autonomous.py
```

**Features:**
- ✅ Avoid obstacles using depth maps
- ✅ Detect and track red circular targets
- ✅ Center camera on target (PID control)
- ✅ Safely approach target (maintains 1.5-2.0m distance)
- ✅ Log GPS coordinates, heading, altitude
- ✅ Capture photos on target lock

**Output:**
- Target logs: `logs/autonomous/targets_*.csv`
- Photos: `logs/autonomous/photos/target_*.jpg`

**See full documentation:** [Autonomous Mode Guide](docs/AUTONOMOUS_MODE.md)

## Training Custom Models

### YOLO Obstacle Detection

1. Collect and label training data
2. Train using Ultralytics:
   ```bash
   yolo train data=obstacles.yaml model=yolov8n.pt epochs=100
   ```

3. Update configuration:
   ```yaml
   detection:
     yolo_model: path/to/custom_model.pt
   ```

## Performance Optimization

### TensorRT Optimization

Enable TensorRT in configuration:
```yaml
detection:
  use_tensorrt: true
```

The first run will export and optimize the model.

### GPU Memory Management

For systems with limited GPU memory, use smaller models:
```yaml
depth:
  model: depth_anything_v2_vits  # Lightest and fastest
detection:
  yolo_model: yolov8n.pt  # nano model
```

## Testing and Validation

### Bench Testing

1. Test VIO with handheld camera movement
2. Verify MAVLink messages in ground station
3. Monitor pose stability and accuracy

### Simulation Testing

1. Run scripted missions in AirSim
2. Validate detection accuracy
3. Measure FPS and latency

### Field Testing

1. Start with hover tests
2. Progress to translational motion
3. Monitor VIO health indicators
4. Log all data for post-flight analysis

## Logging and Telemetry

Logs are saved to the `logs/` directory with timestamps.

### Log Contents
- Frame timing and FPS statistics
- VIO estimates and covariance
- Detection results and confidence
- Depth summaries
- MAVLink communication status

### Viewing Logs

```bash
tail -f logs/drone_autonomy_*.log
```

## Troubleshooting

### Video Stream Issues

**Problem**: Cannot open GStreamer pipeline

**Solution**: 
- Verify GStreamer installation: `gst-launch-1.0 --version`
- Test pipeline manually: `gst-launch-1.0 udpsrc port=5600 ! ...`
- Check firewall settings for UDP port

### GPU/CUDA Issues

**Problem**: CUDA out of memory

**Solution**:
- Reduce model sizes in configuration
- Lower video resolution
- Close other GPU-intensive applications

### MAVLink Connection Issues

**Problem**: Cannot connect to vehicle

**Solution**:
- Verify connection string and IP address
- Check vehicle is powered on and MAVLink is enabled
- Test with QGroundControl or Mission Planner first

### Low FPS

**Problem**: Frame rate below real-time

**Solution**:
- Enable TensorRT optimization
- Use smaller models (depth_anything_v2_vits, yolov8n)
- Reduce video resolution
- Check GPU utilization

## Project Structure

```
DroneAutonomy/
├── src/drone_autonomy/
│   ├── video/              # Video stream input
│   ├── vio/                # Visual odometry
│   ├── depth/              # Depth estimation
│   ├── detection/          # Object and target detection
│   ├── fusion/             # Fusion and decision layer
│   ├── mavlink/            # MAVLink communication
│   ├── simulation/         # AirSim integration
│   ├── utils/              # Utilities
│   └── pipeline.py         # Main orchestrator
├── config/                 # Configuration files
├── docs/                   # Documentation
├── examples/               # Example scripts
├── tests/                  # Unit tests
├── requirements.txt        # Python dependencies
└── setup.py               # Package setup
```

## API Reference

See individual module documentation:
- [Video Stream](src/drone_autonomy/video/stream.py)
- [VIO Estimator](src/drone_autonomy/vio/vio_estimator.py)
- [Depth Estimator](src/drone_autonomy/depth/depth_estimator.py)
- [YOLO Detector](src/drone_autonomy/detection/yolo_detector.py)
- [Target Detector](src/drone_autonomy/detection/target_detector.py)
- [Decision Layer](src/drone_autonomy/fusion/decision_layer.py)
- [MAVLink Telemetry](src/drone_autonomy/mavlink/telemetry.py)

## Safety Considerations

⚠️ **Important Safety Notes**

1. **Always test in simulation first** before field deployment
2. **Validate VIO accuracy** with known trajectories
3. **Verify MAVLink integration** on the bench
4. **Monitor system health** during flight
5. **Have manual override** ready at all times
6. **Test in controlled environment** initially
7. **Check GPU temperature** during extended operation

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Depth Anything V2 team for state-of-the-art depth estimation
- Ultralytics for YOLOv8
- ArduPilot community for VIO integration guidance
- Microsoft for AirSim simulation platform

## Support

For issues and questions:
- GitHub Issues: https://github.com/YoussGm3o8/DroneAutonomy/issues

## Citation

If you use this work in research, please cite:

```bibtex
@software{droneautonomy2024,
  title = {DroneAutonomy: Real-Time Monocular Vision Pipeline},
  author = {DroneAutonomy Team},
  year = {2024},
  url = {https://github.com/YoussGm3o8/DroneAutonomy}
}
```