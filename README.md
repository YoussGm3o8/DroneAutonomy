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
- CUDA-capable GPU drivers
- GStreamer (for video streaming)
- Optional: TensorRT for optimized inference
- Optional: AirSim for simulation testing

## Features

### Core Capabilities

1. **Video Input**
   - GStreamer pipeline support for H.264/H.265 over UDP
   - OpenCV fallback for standard camera input
   - Configurable resolution and frame rate

2. **Visual Odometry (VIO)**
   - 6-DoF pose estimation using monocular camera
   - Feature-based visual odometry
   - IMU integration support (when available)
   - Compatible with VINS-Mono and ORB-SLAM3 backends

3. **Monocular Depth Estimation**
   - MiDaS-based depth estimation
   - Real-time inference on NVIDIA GPUs
   - Multiple model sizes (small, hybrid, large)
   - Dense or semi-dense depth maps

4. **Object Detection**
   - YOLO-based obstacle detection (YOLOv8)
   - TensorRT optimization support
   - Real-time inference on NVIDIA GPUs
   - Configurable confidence thresholds

5. **Target Detection**
   - Red circular target detection
   - HSV color thresholding
   - Hough Circle Transform
   - Robust against clutter

6. **Fusion and Decision Layer**
   - Combines depth and detection outputs
   - Computes keep-out regions
   - Target gate identification
   - Prioritizes close detections

7. **MAVLink Integration**
   - Visual odometry publication to ArduPilot
   - UDP-based telemetry
   - Compatible with ArduPilot VIO/VISO interface
   - Ground station communication

8. **Simulation Support**
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
  model: MiDaS_small
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
  model: MiDaS_small
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
- Use smaller models (MiDaS_small, yolov8n)
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

- Intel ISL for MiDaS depth estimation
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