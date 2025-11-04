# MAVLink Object Avoidance System

## Overview

The MAVLink Object Avoidance System provides real-time autonomous obstacle detection and avoidance for drones using MAVLink protocol. This system integrates computer vision (depth estimation), path planning, and MAVLink command execution to enable safe autonomous flight in cluttered environments.

## Features

### 1. Real-Time Obstacle Detection
- **Depth-based detection**: Uses monocular depth estimation (Depth Anything V2, MiDaS) to detect obstacles
- **Multi-zone monitoring**: Divides camera view into configurable detection zones
- **Risk assessment**: Classifies obstacles by risk level (SAFE, LOW, MEDIUM, HIGH, CRITICAL)
- **Distance estimation**: Calculates real-world distance to obstacles in meters

### 2. Intelligent Path Planning
- **Multi-path generation**: Creates multiple candidate trajectories
- **Cost-based selection**: Evaluates paths based on clearance, length, and curvature
- **Tesla-style visualization**: Real-time path overlay similar to Tesla Autopilot
- **Safety guarantees**: Ensures minimum clearance requirements

### 3. MAVLink Command Execution
- **Velocity control**: Body-frame and NED-frame velocity commands
- **Position control**: GPS waypoint navigation
- **Emergency procedures**: Automatic brake/stop on critical obstacles
- **Mode management**: Automatic GUIDED mode switching
- **Comprehensive commands**: Takeoff, land, RTL, yaw control, and more

### 4. Safety Systems
- **Emergency stop**: Automatic brake on critical collision risk
- **Altitude monitoring**: Maintains safe altitude limits
- **Failsafe modes**: Graceful degradation on sensor failures
- **Manual override**: Operator can pause/resume/stop anytime

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Video Stream (Camera/RTSP)              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│          Depth Estimator (Depth Anything V2)            │
│              Generates dense depth map                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           Obstacle Avoider (Path Planner)               │
│   • Detects obstacles from depth map                    │
│   • Generates multiple path candidates                  │
│   • Evaluates paths for safety/efficiency               │
│   • Selects optimal avoidance trajectory                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│      MAVLink Avoidance Controller (Executor)            │
│   • Converts paths to velocity commands                 │
│   • Sends commands via MAVLink to drone                 │
│   • Monitors telemetry for feedback                     │
│   • Handles emergency situations                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         Drone / SITL (ArduPilot/PX4)                    │
│              Executes movement commands                  │
└─────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

```bash
# Python 3.8+
# CUDA-capable GPU (recommended)
# ArduPilot SITL or real drone

# Install dependencies
pip install -r requirements.txt

# For ArduPilot SITL testing
pip install pymavlink dronekit MAVProxy
```

### Setup ArduPilot SITL (for testing)

```bash
# Install ArduPilot SITL
git clone https://github.com/ArduPilot/ardupilot.git
cd ardupilot
./Tools/environment_install/install-prereqs-ubuntu.sh -y
. ~/.profile

# Build and run copter SITL
cd ArduCopter
../Tools/autotest/sim_vehicle.py --console --map
```

## Configuration

Edit `config/mavlink_avoidance.yaml`:

```yaml
# MAVLink Connection
mavlink:
  connection_string: 'udp:127.0.0.1:14550'  # SITL default
  # For real drone via USB: '/dev/ttyUSB0:57600'
  # For WiFi telemetry: 'udpin:0.0.0.0:14550'

# Obstacle Detection Thresholds
obstacle_avoidance:
  obstacle_distance_threshold: 5.0  # Detect within 5m
  critical_distance: 2.0            # Emergency stop at 2m
  warning_distance: 3.5             # High alert at 3.5m

# Controller Behavior
avoidance_controller:
  max_velocity: 3.0           # Maximum speed (m/s)
  avoidance_velocity: 1.5     # Speed during avoidance (m/s)
  emergency_distance: 1.5     # Emergency stop threshold (m)
  update_rate: 20             # Control loop frequency (Hz)
```

## Usage

### Basic Test with SITL

```bash
# Terminal 1: Start ArduPilot SITL
cd ~/ardupilot/ArduCopter
../Tools/autotest/sim_vehicle.py --console --map

# Terminal 2: Run avoidance system
cd ~/DroneAutonomy
python examples/test_mavlink_avoidance.py
```

### Interactive Controls

While the test script is running:

- **Q**: Quit the application
- **S**: Start/Stop the avoidance controller
- **P**: Pause (hold position)
- **R**: Resume from pause
- **E**: Emergency stop

### Simulation Mode (No Drone)

Test the vision and path planning without MAVLink:

```bash
python examples/test_mavlink_avoidance.py --simulate
```

### Custom Configuration

```bash
python examples/test_mavlink_avoidance.py --config my_config.yaml
```

## API Reference

### MAVLinkTelemetry

Enhanced MAVLink interface with comprehensive command support.

```python
from drone_autonomy.mavlink.telemetry import MAVLinkTelemetry

mavlink = MAVLinkTelemetry(config)
mavlink.connect()

# Basic commands
mavlink.arm()
mavlink.takeoff(altitude=10.0)
mavlink.set_mode("GUIDED")

# Movement commands
mavlink.send_velocity_body(vx=1.0, vy=0.0, vz=0.0, yaw_rate=0.0)
mavlink.goto_position_global(lat=47.123, lon=-122.456, alt=10.0)
mavlink.set_yaw(yaw_deg=90.0, relative=False)

# Safety commands
mavlink.pause()  # Brake/hold position
mavlink.return_to_launch()
mavlink.emergency_stop()  # Force disarm (USE WITH CAUTION!)
mavlink.land()

# Read telemetry
telemetry = mavlink.read_telemetry()
print(f"Position: {telemetry['position']}")
print(f"Velocity: {telemetry['velocity']}")
print(f"Battery: {telemetry['battery']['remaining']}%")
```

### ObstacleAvoider

Path planning and obstacle detection.

```python
from drone_autonomy.navigation.obstacle_avoidance import ObstacleAvoider

avoider = ObstacleAvoider(config)

# Detect obstacles from depth map
obstacles = avoider.detect_obstacles(depth_map)

# Generate avoidance paths
frame_shape = (480, 640)  # height, width
paths = avoider.generate_path_candidates(frame_shape, target_position=None)

# Check if avoidance needed
should_avoid = avoider.should_avoid(target_detected=False)

# Get avoidance command
command = avoider.get_avoidance_command()
# Returns: {'avoid': True, 'lateral': -0.3, 'clearance': 2.5, 'risk': 'medium'}

# Visualize
viz_frame = avoider.visualize(frame, depth_map)
```

### MAVLinkAvoidanceController

High-level controller combining detection, planning, and execution.

```python
from drone_autonomy.navigation.mavlink_avoidance_controller import (
    MAVLinkAvoidanceController
)

controller = MAVLinkAvoidanceController(
    mavlink=mavlink,
    avoider=avoider,
    config=controller_config
)

# Start autonomous avoidance
controller.start()

# Main loop
while True:
    frame = video_stream.read()
    depth_map = depth_estimator.estimate(frame)['depth_map']

    # Update controller
    status = controller.update(depth_map=depth_map)

    if status['avoiding']:
        print(f"Avoiding {status['num_obstacles']} obstacles")

    # Visualize
    viz = controller.get_visualization_frame(frame, depth_map)
    cv2.imshow('Avoidance', viz)

# Stop when done
controller.stop()
```

## MAVLink Commands Reference

### Flight Modes

```python
mavlink.set_mode("STABILIZE")  # Manual stabilization
mavlink.set_mode("ALT_HOLD")   # Altitude hold
mavlink.set_mode("LOITER")     # Position hold (GPS)
mavlink.set_mode("GUIDED")     # Autonomous control
mavlink.set_mode("RTL")        # Return to launch
mavlink.set_mode("LAND")       # Auto land
mavlink.set_mode("BRAKE")      # Emergency brake
```

### Position Control

```python
# Global position (GPS)
mavlink.goto_position_global(
    lat=47.123456,
    lon=-122.654321,
    alt=10.0  # meters AMSL
)

# Local position (NED frame)
mavlink.send_position_target(
    x=10.0,   # North (m)
    y=5.0,    # East (m)
    z=-10.0,  # Down (m, negative = up)
    yaw=1.57  # rad
)
```

### Velocity Control

```python
# Body frame (relative to drone heading)
mavlink.send_velocity_body(
    vx=2.0,      # Forward (m/s)
    vy=0.5,      # Right (m/s)
    vz=0.0,      # Down (m/s)
    yaw_rate=0.1 # Yaw rate (rad/s)
)

# NED frame (absolute directions)
mavlink.send_velocity_ned(
    vx=2.0,      # North (m/s)
    vy=1.0,      # East (m/s)
    vz=0.0,      # Down (m/s)
    yaw_rate=0.0
)

# With explicit yaw angle
mavlink.send_velocity_with_yaw(
    vx=2.0, vy=0.0, vz=0.0,
    yaw_deg=90.0,  # Face east
    frame="body"   # or "ned"
)
```

### Yaw Control

```python
# Absolute yaw (0-360 degrees, 0=North)
mavlink.set_yaw(yaw_deg=180.0, relative=False)

# Relative yaw (turn X degrees from current)
mavlink.set_yaw(yaw_deg=45.0, relative=True)

# With custom yaw rate
mavlink.set_yaw(yaw_deg=90.0, yaw_rate_degs=30.0)
```

### Safety Commands

```python
# Pause (switch to BRAKE or LOITER)
mavlink.pause()

# Resume autonomous control (GUIDED mode)
mavlink.resume_guided()

# Return to launch
mavlink.return_to_launch()

# Land at current position
mavlink.land()

# Emergency motor disarm (drone will fall!)
mavlink.emergency_stop()
```

## Safety Considerations

### ⚠️ Important Safety Notes

1. **Always test in simulation first** (SITL) before flying real hardware
2. **Maintain manual override capability** - keep RC controller ready
3. **Set appropriate safety thresholds** for your environment
4. **Monitor battery levels** - autonomous flight consumes more power
5. **Ensure GPS lock** before enabling GUIDED mode
6. **Test emergency stop procedures** before autonomous flight
7. **Respect airspace regulations** and fly in safe areas
8. **Check sensor calibration** (compass, accelerometer, etc.)

### Emergency Procedures

If the system behaves unexpectedly:

1. **Press 'E' for emergency stop** (brakes to hold position)
2. **Switch to manual RC control** using transmitter
3. **Land immediately** if unsafe behavior continues
4. **Review logs** in `logs/mavlink_avoidance_test.log`

### Recommended Safety Settings

```yaml
avoidance_controller:
  max_velocity: 2.0              # Conservative speed
  emergency_distance: 2.5        # Generous safety margin
  enable_emergency_stop: true    # Always enable
  min_altitude: 2.0              # Stay above ground obstacles

obstacle_avoidance:
  obstacle_distance_threshold: 6.0  # Early detection
  critical_distance: 2.5            # Conservative emergency threshold
  min_clearance: 2.0                # Adequate safety buffer
```

## Troubleshooting

### MAVLink Connection Issues

**Problem**: Cannot connect to drone

```bash
# Check available ports
ls /dev/ttyUSB* /dev/ttyACM*

# Check permissions
sudo usermod -a -G dialout $USER
# Log out and back in

# Test with MAVProxy
mavproxy.py --master=/dev/ttyUSB0 --baudrate=57600

# For SITL connection issues
mavproxy.py --master=udp:127.0.0.1:14550
```

### Depth Estimation Performance

**Problem**: Low FPS during depth estimation

```yaml
# Use faster model
depth:
  model: 'depth_anything_v2_vits'  # Fastest
  scale_output: 0.5                # Downsample

# Skip frames
performance:
  skip_frames: 1  # Process every other frame
```

### Obstacle Detection Sensitivity

**Problem**: Too many false positives

```yaml
obstacle_avoidance:
  obstacle_distance_threshold: 4.0  # Reduce range
  min_clearance: 1.0                # Less conservative
```

**Problem**: Not detecting obstacles

```yaml
obstacle_avoidance:
  obstacle_distance_threshold: 8.0  # Increase range
  num_zones_horizontal: 9           # More zones
  num_zones_vertical: 5
```

## Performance Optimization

### GPU Acceleration

Ensure CUDA is properly configured:

```bash
# Check CUDA
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"

# Use TensorRT (advanced)
performance:
  use_tensorrt: true
```

### Multi-threading

```yaml
performance:
  async_processing: true  # Process frames asynchronously
```

### Model Selection

Choose depth model based on hardware:

| Model | Speed | Accuracy | GPU Memory | Use Case |
|-------|-------|----------|------------|----------|
| `depth_anything_v2_vits` | Fast (100+ FPS) | Good | 2GB | Real-time avoidance |
| `depth_anything_v2_vitb` | Medium (50 FPS) | Better | 4GB | Balanced |
| `depth_anything_v2_vitl` | Slow (20 FPS) | Best | 6GB | Precision tasks |
| `dpt_hybrid` | Medium (60 FPS) | Good | 3GB | Alternative |

## Integration Examples

### Integrate with Existing Pipeline

```python
from drone_autonomy.pipeline import DronePipeline
from drone_autonomy.navigation.mavlink_avoidance_controller import (
    MAVLinkAvoidanceController
)

# Setup pipeline
pipeline = DronePipeline(config)

# Add avoidance controller
controller = MAVLinkAvoidanceController(
    mavlink=pipeline.mavlink,
    avoider=pipeline.obstacle_avoider,
    config=config['avoidance_controller']
)

# Start avoidance
controller.start()

# Run pipeline with avoidance
pipeline.run()
```

### Custom Avoidance Logic

```python
class CustomAvoidanceController(MAVLinkAvoidanceController):
    def _execute_avoidance(self):
        """Override with custom avoidance logic"""
        # Your custom path execution logic here
        super()._execute_avoidance()
```

## Logging and Debugging

### Enable Debug Logging

```bash
python examples/test_mavlink_avoidance.py --log-level DEBUG
```

### Log Files

- `logs/mavlink_avoidance_test.log` - Main application log
- `logs/avoidance/telemetry_YYYYMMDD_HHMMSS.csv` - Telemetry data
- `logs/avoidance/obstacles_YYYYMMDD_HHMMSS.csv` - Detected obstacles

### Analyze Telemetry

```python
import pandas as pd

# Load telemetry log
df = pd.read_csv('logs/avoidance/telemetry_20241104_120000.csv')

# Plot altitude over time
df.plot(x='timestamp', y='relative_altitude')

# Analyze velocity
print(df[['ground_speed', 'vertical_speed']].describe())
```

## Contributing

Contributions are welcome! Areas for improvement:

- [ ] Support for PX4 firmware
- [ ] Multi-path trajectory optimization
- [ ] Machine learning-based obstacle classification
- [ ] Integration with SLAM systems
- [ ] Swarm avoidance capabilities
- [ ] Improved emergency recovery behaviors

## License

See LICENSE file in project root.

## References

- [ArduPilot MAVLink Documentation](https://ardupilot.org/dev/docs/mavlink-basics.html)
- [Depth Anything V2 Paper](https://arxiv.org/abs/2406.09414)
- [MAVLink Protocol Specification](https://mavlink.io/en/)
- [ArduPilot SITL Documentation](https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html)

## Support

For issues and questions:
- GitHub Issues: [DroneAutonomy Issues](https://github.com/YoussGm3o8/DroneAutonomy/issues)
- Documentation: See `docs/` directory
- Examples: See `examples/` directory
