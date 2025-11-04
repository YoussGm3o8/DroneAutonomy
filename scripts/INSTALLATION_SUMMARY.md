# GStreamer Camera Plugin Installation Summary

## What Has Been Created

I've created a complete installation and setup system for the GstCameraPlugin for Gazebo on WSL:

### 1. Installation Script
**File**: `scripts/install_gazebo_gstreamer.sh`
- Installs Gazebo 11 on WSL
- Installs GStreamer and all required plugins
- Builds the custom GstCameraPlugin from source
- Configures environment variables automatically

### 2. Plugin Source Code
The installation script creates:
- **CMakeLists.txt**: Build configuration
- **GstCameraPlugin.cc**: C++ plugin source that:
  - Extends Gazebo's CameraPlugin
  - Captures camera frames in real-time
  - Encodes video with H.264
  - Streams via UDP using GStreamer
  - Configurable host/port via SDF parameters

### 3. Example Model
**File**: `config/gazebo_models/iris_with_gst_camera.sdf`
- Ready-to-use drone model with GStreamer camera
- Pre-configured plugin settings
- Easy to modify for custom parameters

### 4. Test Script
**File**: `scripts/test_gstreamer_setup.sh`
- Comprehensive installation verification
- Tests 15+ components
- Checks dependencies and configurations
- Provides detailed diagnostic output

### 5. Quick Start Script
**File**: `scripts/quickstart_gstreamer.sh`
- Interactive menu system
- Test local streaming
- Test Windows streaming
- View streams
- Test GStreamer pipeline
- Show plugin information

### 6. PowerShell Manager
**File**: `setup_gstreamer.ps1`
- Windows-friendly interface
- One-command installation
- Easy testing and launching
- Stream viewer integration

### 7. Documentation
**File**: `scripts/GSTREAMER_SETUP.md`
- Complete setup guide
- Usage instructions
- Troubleshooting tips
- Configuration examples
- Integration examples

## Quick Start Guide

### Step 1: Install Everything
From PowerShell in your project directory:

```powershell
.\setup_gstreamer.ps1 install
```

This will take 10-15 minutes and install everything automatically.

### Step 2: Verify Installation
```powershell
.\setup_gstreamer.ps1 test
```

### Step 3: Run Interactive Menu
```powershell
.\setup_gstreamer.ps1 quickstart
```

Or directly from WSL:
```bash
wsl bash scripts/quickstart_gstreamer.sh
```

## How the Plugin Works

### Architecture

```
Gazebo Camera Sensor
         ↓
  GstCameraPlugin
         ↓
  OnNewFrame() callback
         ↓
  Raw RGB frame data
         ↓
  GStreamer Pipeline:
    appsrc → videoconvert → x264enc → rtph264pay → udpsink
         ↓
  UDP Stream (port 5600)
         ↓
  Receiver (Windows/Linux)
```

### Plugin Parameters

In your SDF file:

```xml
<plugin name="gst_camera_plugin" filename="libGstCameraPlugin.so">
  <udp_host>127.0.0.1</udp_host>  <!-- Target IP address -->
  <udp_port>5600</udp_port>        <!-- UDP port -->
</plugin>
```

### Streaming Options

**Local (WSL to WSL)**:
- Host: `127.0.0.1`
- View with: `gst-launch-1.0 udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink`

**WSL to Windows**:
- Host: `172.x.x.x` (Windows host IP)
- Find IP: `wsl bash -c "ip route show | grep -i default | awk '{ print \\$3}'"`
- View with VLC: `udp://@:5600`

**WSL to Network**:
- Host: Any IP on your network
- Requires firewall rules on target machine

## Viewing Options

### Option 1: GStreamer (Recommended)
```bash
# Linux/WSL
gst-launch-1.0 udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink

# Windows (if GStreamer installed)
gst-launch-1.0.exe udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink
```

### Option 2: VLC Media Player
1. Open VLC
2. Media → Open Network Stream
3. Enter: `udp://@:5600`
4. Click Play

### Option 3: FFplay
```bash
ffplay -fflags nobuffer -flags low_delay -framedrop udp://127.0.0.1:5600
```

### Option 4: Python + OpenCV
```python
import cv2

cap = cv2.VideoCapture("udp://127.0.0.1:5600", cv2.CAP_FFMPEG)

while True:
    ret, frame = cap.read()
    if ret:
        cv2.imshow("Gazebo Stream", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
```

## Integration with Your Project

### Update Existing Models

To add GStreamer streaming to your current drone model, add this to the camera sensor:

```xml
<sensor name="camera" type="camera">
  <camera>
    <!-- Your existing camera config -->
  </camera>
  <always_on>1</always_on>
  <update_rate>30</update_rate>
  
  <!-- Add this plugin -->
  <plugin name="gst_camera_plugin" filename="libGstCameraPlugin.so">
    <udp_host>127.0.0.1</udp_host>
    <udp_port>5600</udp_port>
  </plugin>
</sensor>
```

### Python Integration

You can modify your existing video capture code:

```python
# Old way (Gazebo topics)
# import rospy
# from sensor_msgs.msg import Image

# New way (GStreamer direct)
import cv2

class DroneCamera:
    def __init__(self, port=5600):
        self.cap = cv2.VideoCapture(f"udp://127.0.0.1:{port}", cv2.CAP_FFMPEG)
        
    def get_frame(self):
        ret, frame = self.cap.read()
        return frame if ret else None
```

## Troubleshooting

### Plugin Not Loaded
```bash
# Check if plugin exists
ls ~/gazebo_gst_plugin/build/libGstCameraPlugin.so

# Set environment
export GAZEBO_PLUGIN_PATH=$GAZEBO_PLUGIN_PATH:~/gazebo_gst_plugin/build

# Test Gazebo with verbose output
gazebo --verbose config/gazebo_models/iris_with_gst_camera.sdf
```

### No Video Stream
```bash
# Test GStreamer pipeline separately
gst-launch-1.0 videotestsrc ! x264enc ! rtph264pay ! udpsink host=127.0.0.1 port=5600

# In another terminal
gst-launch-1.0 udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink
```

### Firewall Issues (Windows)
```powershell
# Allow UDP port 5600
New-NetFirewallRule -DisplayName "GStreamer UDP 5600" -Direction Inbound -Protocol UDP -LocalPort 5600 -Action Allow
```

### Build Errors
```bash
# Reinstall dependencies
sudo apt-get install --reinstall libgazebo11-dev libgstreamer1.0-dev

# Rebuild plugin
cd ~/gazebo_gst_plugin/build
rm -rf *
cmake ..
make
sudo make install
```

## Performance Tips

### Reduce Latency
Modify `GstCameraPlugin.cc`:
```cpp
"x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! "
```

### Increase Quality
```cpp
"x264enc tune=zerolatency bitrate=2000 speed-preset=medium ! "
```

### Multiple Cameras
Use different ports:
```xml
<!-- Camera 1 -->
<plugin name="gst_camera_1" filename="libGstCameraPlugin.so">
  <udp_port>5600</udp_port>
</plugin>

<!-- Camera 2 -->
<plugin name="gst_camera_2" filename="libGstCameraPlugin.so">
  <udp_port>5601</udp_port>
</plugin>
```

## Next Steps

1. **Install**: Run `.\setup_gstreamer.ps1 install`
2. **Test**: Run `.\setup_gstreamer.ps1 test`
3. **Try it**: Run `.\setup_gstreamer.ps1 quickstart`
4. **Integrate**: Modify your SDF files to use the plugin
5. **Customize**: Adjust parameters for your needs

## Support Files

All created files:
- ✓ `scripts/install_gazebo_gstreamer.sh` - Main installer
- ✓ `scripts/test_gstreamer_setup.sh` - Test suite
- ✓ `scripts/quickstart_gstreamer.sh` - Interactive menu
- ✓ `setup_gstreamer.ps1` - PowerShell manager
- ✓ `scripts/GSTREAMER_SETUP.md` - Detailed documentation
- ✓ `config/gazebo_models/iris_with_gst_camera.sdf` - Example model
- ✓ `scripts/INSTALLATION_SUMMARY.md` - This file

Everything is ready to go! 🚀
