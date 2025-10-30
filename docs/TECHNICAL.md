# DroneAutonomy Technical Documentation

## Architecture Overview

The DroneAutonomy system is built as a modular pipeline with the following components:

```
┌──────────────────────────────────────────────────────────────┐
│                     Main Pipeline                             │
│                    (pipeline.py)                              │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│Video Stream │    │     VIO     │    │   Depth     │
│  (video/)   │    │   (vio/)    │    │  (depth/)   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │
       └──────────────────┴──────────────────┘
                          │
                          ▼
                  ┌──────────────┐
                  │  Detection   │
                  │(detection/)  │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │   Fusion     │
                  │  (fusion/)   │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │   MAVLink    │
                  │ (mavlink/)   │
                  └──────────────┘
```

## Module Documentation

### Video Module (`video/`)

Handles video stream input from GStreamer or OpenCV.

**Key Classes:**
- `VideoStream`: Main video stream handler

**Features:**
- GStreamer pipeline support for H.264/H.265
- OpenCV fallback for standard cameras
- Frame timing and synchronization
- FPS monitoring

### VIO Module (`vio/`)

Visual Inertial Odometry for 6-DoF pose estimation.

**Key Classes:**
- `VIOEstimator`: Visual odometry estimator

**Features:**
- Feature-based visual odometry
- ORB feature detection and matching
- Essential matrix estimation
- Pose recovery and tracking
- Ready for VINS-Mono/ORB-SLAM3 integration

**Algorithm:**
1. Extract ORB features from frame
2. Match features with previous frame
3. Estimate essential matrix using RANSAC
4. Recover rotation and translation
5. Update cumulative pose

### Depth Module (`depth/`)

Monocular depth estimation using MiDaS.

**Key Classes:**
- `DepthEstimator`: MiDaS-based depth estimator

**Features:**
- Multiple MiDaS models (small, hybrid, large)
- GPU acceleration
- Relative depth estimation
- Depth visualization

**Models:**
- `MiDaS_small`: Fast, suitable for real-time (default)
- `DPT_Hybrid`: Balanced accuracy and speed
- `DPT_Large`: High accuracy, slower

### Detection Module (`detection/`)

Object and target detection.

**Key Classes:**
- `YOLODetector`: YOLO-based object detection
- `TargetDetector`: Red circular target detection

**YOLO Features:**
- YOLOv8 support (nano to large models)
- TensorRT optimization
- Real-time inference on GPU
- Configurable confidence thresholds

**Target Detection Features:**
- HSV color thresholding for red
- Hough Circle Transform
- Circle validation
- Robust to clutter

### Fusion Module (`fusion/`)

Combines depth and detection outputs.

**Key Classes:**
- `DecisionLayer`: Fusion and decision making

**Features:**
- Detection-depth fusion
- Weighted confidence scoring
- Avoidance command generation
- Target approach computation
- Proximity-based prioritization

**Fusion Algorithm:**
1. Sample depth at detection locations
2. Compute fused confidence (depth + detection)
3. Filter by proximity threshold
4. Generate avoidance/approach commands

### MAVLink Module (`mavlink/`)

Communication with ArduPilot autopilot.

**Key Classes:**
- `MAVLinkTelemetry`: MAVLink interface

**Features:**
- UDP-based communication
- Visual odometry publishing
- Telemetry reading
- Rate limiting
- VISION_POSITION_ESTIMATE messages

**Message Types:**
- Outbound: VISION_POSITION_ESTIMATE
- Inbound: ATTITUDE, GLOBAL_POSITION_INT, LOCAL_POSITION_NED, GPS_RAW_INT

### Simulation Module (`simulation/`)

AirSim integration for testing.

**Key Classes:**
- `AirSimInterface`: AirSim client wrapper

**Features:**
- Camera image retrieval
- IMU data access
- Ground truth pose
- Takeoff/landing control
- Simulation reset

### Utilities Module (`utils/`)

Helper utilities and tools.

**Key Classes:**
- `Config`: Configuration manager
- `CameraCalibration`: Camera calibration utilities
- `setup_logging`: Logging configuration

**Configuration System:**
- YAML-based configuration
- Deep merge of configs
- Dot notation access
- Default values

## Data Flow

### Main Pipeline Loop

```python
1. Get frame from video stream
   ↓
2. Process VIO (if enabled)
   - Extract features
   - Match with previous frame
   - Estimate pose
   - Publish to MAVLink
   ↓
3. Estimate depth
   - Run MiDaS inference
   - Normalize depth map
   ↓
4. Run detections (parallel)
   - YOLO object detection
   - Target circle detection
   ↓
5. Fusion layer
   - Fuse detections with depth
   - Compute avoidance commands
   - Compute target approach
   ↓
6. Output and logging
   - Display results
   - Log performance
   - Save telemetry
```

### Performance Considerations

**Bottlenecks:**
1. Depth estimation (MiDaS inference)
2. YOLO detection
3. Video decoding (GStreamer)

**Optimization Strategies:**
1. Use smaller models for real-time performance
2. Enable TensorRT for YOLO
3. Reduce depth output scale
4. Process every N frames for heavy modules
5. GPU memory management

**Typical Performance (RTX 3060):**
- MiDaS_small: ~50ms per frame
- YOLOv8n: ~20ms per frame
- Target detection: ~10ms per frame
- VIO: ~5ms per frame
- Total: ~25-30 FPS achievable

## Configuration Reference

### Complete Configuration Structure

```yaml
video:
  gstreamer_pipeline: str
  width: int
  height: int
  fps: int
  backend: str (gstreamer|opencv)
  camera_id: int

camera:
  fx: float  # Focal length x
  fy: float  # Focal length y
  cx: float  # Principal point x
  cy: float  # Principal point y
  k1-k2: float  # Radial distortion
  p1-p2: float  # Tangential distortion

vio:
  enabled: bool
  type: str (vins-mono|orb-slam3)
  imu_rate: int
  output_rate: int

depth:
  model: str (MiDaS_small|DPT_Hybrid|DPT_Large)
  device: str (cuda|cpu)
  input_size: [int, int]
  output_scale: float

detection:
  yolo_model: str
  confidence_threshold: float
  nms_threshold: float
  device: str
  use_tensorrt: bool
  classes: list[str]

target_detection:
  hsv_lower: [int, int, int]
  hsv_upper: [int, int, int]
  min_radius: int
  max_radius: int
  circle_threshold: float

mavlink:
  connection_string: str
  baud: int
  vio_publish_rate: int
  telemetry_rate: int

fusion:
  depth_weight: float
  detection_weight: float
  min_confidence: float
  proximity_threshold: float

simulation:
  enabled: bool
  airsim_ip: str
  airsim_port: int

logging:
  level: str (DEBUG|INFO|WARNING|ERROR)
  save_video: bool
  save_detections: bool
  log_dir: str
```

## API Reference

### Pipeline Class

```python
class DronePipeline:
    def __init__(self, config_path: Optional[str] = None)
    def initialize(self) -> bool
    def run(self, display: bool = True, max_frames: Optional[int] = None)
    def stop()
```

### VideoStream Class

```python
class VideoStream:
    def __init__(self, config: dict)
    def start(self) -> bool
    def read(self) -> Tuple[bool, Optional[np.ndarray], float]
    def stop()
    def get_frame_info(self) -> dict
```

### DepthEstimator Class

```python
class DepthEstimator:
    def __init__(self, config: dict)
    def load_model(self) -> bool
    def estimate_depth(self, frame: np.ndarray) -> Tuple[Optional[np.ndarray], float]
    def visualize_depth(self, depth_map: np.ndarray) -> np.ndarray
```

### YOLODetector Class

```python
class YOLODetector:
    def __init__(self, config: dict)
    def load_model(self) -> bool
    def detect(self, frame: np.ndarray) -> Tuple[List[dict], float]
    def draw_detections(self, frame: np.ndarray, detections: List[dict]) -> np.ndarray
```

### DecisionLayer Class

```python
class DecisionLayer:
    def __init__(self, config: dict)
    def fuse_detections_with_depth(self, detections: List[dict], depth_map: np.ndarray, depth_scale: float) -> List[dict]
    def compute_avoidance_command(self, fused_detections: List[dict], frame_width: int, frame_height: int) -> Dict[str, float]
```

## Extending the System

### Adding a New Detector

1. Create detector class in `detection/` module
2. Implement `detect()` method returning list of detections
3. Add to pipeline initialization
4. Update configuration schema

### Adding a New VIO Backend

1. Create VIO wrapper in `vio/` module
2. Implement standard interface (position, orientation)
3. Add configuration option
4. Update documentation

### Adding Custom Decision Logic

1. Extend `DecisionLayer` class
2. Implement custom fusion logic
3. Update command generation
4. Test with simulation

## Testing

### Unit Tests

```bash
python tests/test_integration.py
```

### Component Tests

```bash
python tests/test_integration.py --test <component>
# Available: video, calibration, target, fusion, config, vio
```

### Integration Testing

1. Test in simulation (AirSim)
2. Bench test with hardware
3. Field test with safety protocols

## Contributing

See [CONTRIBUTING.md] for guidelines on:
- Code style
- Testing requirements
- Pull request process
- Documentation standards
