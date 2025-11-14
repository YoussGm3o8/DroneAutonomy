# Gazebo Configuration Files

Gazebo simulation configuration files and plugins.

## Contents

### World Files
- `test_world.sdf` - Test world for drone simulation
- `iris_with_camera_FIXED.sdf` - Iris quadcopter with camera model (fixed version)

### Plugins
- `GstCameraPlugin_FIXED.cc` - Fixed GStreamer camera plugin source code

## Usage

### Launch Gazebo with Test World
```bash
gz sim test_world.sdf
```

### Use Iris Drone Model
The `iris_with_camera_FIXED.sdf` model is used by the main application when connecting to Gazebo simulation.

### Camera Plugin
The `GstCameraPlugin_FIXED.cc` plugin enables GStreamer video streaming from the Gazebo camera sensor. This is compiled and loaded automatically when Gazebo starts with a world that includes the camera sensor.

## Related

- Main Gazebo configuration: `../gazebo_simulation.yaml`
- Gazebo launch script: `../../launch_gazebo.py`
- Gazebo manager: `../../src/drone_autonomy/utils/gazebo_manager.py`
