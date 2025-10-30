"""README for examples directory."""

# DroneAutonomy Examples

This directory contains example scripts demonstrating various components of the DroneAutonomy system.

## Available Examples

### Basic Pipeline
- **run_basic.py**: Run the complete pipeline with default camera input
  ```bash
  python examples/run_basic.py
  ```

### Component Tests

#### Camera Calibration
- **calibrate_camera.py**: Camera calibration utility
  ```bash
  # Capture calibration images
  python examples/calibrate_camera.py --capture --images data/calib_images
  
  # Run calibration
  python examples/calibrate_camera.py --images data/calib_images --output config/camera.json
  ```

#### Depth Estimation
- **test_depth_estimation.py**: Test MiDaS depth estimation
  ```bash
  python examples/test_depth_estimation.py
  ```

#### Object Detection
- **test_yolo_detection.py**: Test YOLO object detection
  ```bash
  python examples/test_yolo_detection.py
  ```

#### Target Detection
- **test_target_detection.py**: Test red circle target detection
  ```bash
  python examples/test_target_detection.py
  ```

#### Simulation
- **test_airsim.py**: Test AirSim integration
  ```bash
  # Make sure AirSim is running first
  python examples/test_airsim.py
  ```

## Requirements

All examples require the base DroneAutonomy installation:
```bash
pip install -r requirements.txt
```

Some examples have additional requirements:
- Depth estimation: MiDaS model (auto-downloaded)
- YOLO detection: YOLOv8 model (auto-downloaded)
- AirSim: `pip install airsim`

## Usage Tips

1. Start with component tests before running the full pipeline
2. Test depth and detection modules first to verify GPU setup
3. Use camera calibration for best VIO performance
4. Test in simulation (AirSim) before field deployment

## Common Issues

**Camera not found**: 
- Check camera is connected
- Try different camera ID (0, 1, 2, etc.)

**CUDA out of memory**:
- Use smaller models (MiDaS_small, yolov8n)
- Reduce video resolution

**Model download failed**:
- Check internet connection
- Models are cached in `~/.cache/torch/hub/`
