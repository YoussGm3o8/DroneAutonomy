# Scripts Directory

Utility scripts for setup, debugging, and system management.

## Directory Structure

### `setup/`
Environment setup and configuration scripts:
- `activate_env.bat` / `activate_env.ps1` - Virtual environment activation
- `add_firewall_rule.bat` / `add_firewall_rule.ps1` - Windows firewall configuration
- `recreate_venv_py311.ps1` - Recreate Python 3.11 virtual environment
- `setup_gstreamer.ps1` - GStreamer installation and setup

### Diagnostic & Debug Scripts
- `debug_heartbeat.py` - Debug MAVLink heartbeat messages
- `diagnose_mavlink.py` - Comprehensive MAVLink diagnostics
- `fix_camera_orientation.py` - Camera orientation correction
- `fix_gazebo_env.py` - Gazebo environment fixes
- `fix_onnx_shapes.py` - ONNX model shape corrections

### Other Documentation
- `GSTREAMER_SETUP.md` - GStreamer setup instructions
- `INSTALLATION_SUMMARY.md` - Installation summary

## Usage

### Setup Scripts
```powershell
# Activate virtual environment
.\scripts\setup\activate_env.ps1

# Setup GStreamer
.\scripts\setup\setup_gstreamer.ps1

# Add firewall rules for network communication
.\scripts\setup\add_firewall_rule.ps1
```

### Diagnostic Scripts
```bash
# Debug MAVLink connection
python scripts/diagnose_mavlink.py

# Debug heartbeat messages
python scripts/debug_heartbeat.py

# Fix ONNX model shapes
python scripts/fix_onnx_shapes.py
```

### Camera & Gazebo
```bash
# Fix camera orientation
python scripts/fix_camera_orientation.py

# Fix Gazebo environment
python scripts/fix_gazebo_env.py
```
