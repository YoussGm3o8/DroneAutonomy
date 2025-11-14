# Tests Directory

This directory contains all test files organized by category.

## Directory Structure

### `unit/`
Unit tests for individual modules and components:
- `test_fixed_model.py` - Tests for depth model loading
- `test_model_selection.py` - Tests for model selection logic
- `test_mode_changes.py` - Tests for mode change handling
- `test_heartbeat_filter.py` - Tests for MAVLink heartbeat filtering
- `test_tensorrt_depth.py` - Tests for TensorRT depth estimation
- `check_onnx_model.py` - ONNX model validation
- `check_opencv_gstreamer.py` - OpenCV GStreamer support check
- `test_opencv_gstreamer.py` - OpenCV GStreamer functionality tests

### `integration/`
Integration tests for system components:
- `test_mavlink_connection.py` - MAVLink connection tests
- `test_telemetry_fix.py` - Telemetry system tests
- `test_telemetry_integration.py` - Full telemetry integration tests
- `verify_environment.py` - Environment verification script
- `verify_integration.py` - Integration verification script
- `verify_mavlink_avoidance_gui.py` - GUI+MAVLink+Avoidance integration test
- `test_gazebo_manager_fix.py` - Gazebo manager tests
- `test_wsl_gazebo_camera.py` - WSL Gazebo camera integration tests

### `gstreamer/`
GStreamer-specific tests:
- `test_gstreamer_debug.bat` - Windows GStreamer debugging
- `test_gstreamer_reception.py` - GStreamer video reception tests
- `test_gstreamer_windows.bat` - Windows GStreamer tests
- `test_stream_wsl.sh` - WSL GStreamer streaming tests

## Running Tests

### Unit Tests
```bash
python -m pytest tests/unit/
```

### Integration Tests
```bash
python -m pytest tests/integration/
```

### GStreamer Tests
```bash
cd tests/gstreamer
./test_stream_wsl.sh  # Linux/WSL
test_gstreamer_windows.bat  # Windows
```

### Individual Test
```bash
python tests/unit/test_fixed_model.py
```

## Test Requirements

- All dependencies from `requirements.txt`
- pytest for running test suites
- GStreamer installed for GStreamer tests
- MAVProxy/SITL for MAVLink tests
- Gazebo Harmonic for Gazebo tests
