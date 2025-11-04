# GStreamer Camera Plugin Setup for Gazebo on WSL

This guide will help you install and configure the GstCameraPlugin for Gazebo on WSL, enabling GStreamer video feed from your simulated drone camera.

## Prerequisites

- WSL2 with Ubuntu 20.04 or 22.04
- Windows 10/11 with WSL enabled

## Installation

### Step 1: Run the Installation Script

From PowerShell in your project directory:

```powershell
wsl bash scripts/install_gazebo_gstreamer.sh
```

This script will:
1. Install Gazebo 11
2. Install GStreamer and all necessary plugins
3. Build the GstCameraPlugin
4. Configure environment variables

**Installation takes approximately 10-15 minutes.**

### Step 2: Verify Installation

After installation, restart your terminal or source the environment:

```bash
wsl bash -c "source ~/.bashrc && gazebo --version"
```

Check if the plugin is built:

```bash
wsl bash -c "ls ~/gazebo_gst_plugin/build/libGstCameraPlugin.so"
```

## Usage

### Option 1: Use the Plugin in Your SDF Model

Add the GstCameraPlugin to your camera sensor in the SDF file:

```xml
<sensor name="camera" type="camera">
  <camera>
    <horizontal_fov>1.047</horizontal_fov>
    <image>
      <width>1280</width>
      <height>720</height>
      <format>R8G8B8</format>
    </image>
    <clip>
      <near>0.1</near>
      <far>100</far>
    </clip>
  </camera>
  <always_on>1</always_on>
  <update_rate>30</update_rate>
  
  <!-- GStreamer Plugin -->
  <plugin name="gst_camera_plugin" filename="libGstCameraPlugin.so">
    <udp_host>127.0.0.1</udp_host>
    <udp_port>5600</udp_port>
  </plugin>
</sensor>
```

### Option 2: Use the Example Model

We've created a ready-to-use model with GStreamer support:

```bash
wsl bash -c "gazebo config/gazebo_models/iris_with_gst_camera.sdf"
```

## Viewing the Video Stream

### From WSL (Linux)

View the stream using GStreamer:

```bash
wsl bash -c "gst-launch-1.0 udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink"
```

### From Windows

You have several options:

#### Option 1: GStreamer on Windows

1. Install GStreamer for Windows from: https://gstreamer.freedesktop.org/download/
2. Add GStreamer to your PATH
3. Run:
```powershell
gst-launch-1.0.exe udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink
```

#### Option 2: VLC Media Player

1. Open VLC
2. Go to Media → Open Network Stream
3. Enter: `udp://@:5600`
4. Click Play

#### Option 3: FFplay (from FFmpeg)

```powershell
ffplay -fflags nobuffer -flags low_delay -framedrop -strict experimental udp://127.0.0.1:5600
```

## Configuration Options

### Plugin Parameters

- **udp_host**: IP address to stream to (default: 127.0.0.1)
- **udp_port**: UDP port for streaming (default: 5600)

### Example: Stream to Windows from WSL

To stream from WSL to Windows host, you need the Windows IP:

```xml
<plugin name="gst_camera_plugin" filename="libGstCameraPlugin.so">
  <udp_host>172.x.x.x</udp_host>  <!-- Your Windows IP -->
  <udp_port>5600</udp_port>
</plugin>
```

Find your Windows IP from WSL:

```bash
wsl bash -c "ip route show | grep -i default | awk '{ print \$3}'"
```

## Troubleshooting

### Plugin Not Found

If Gazebo can't find the plugin:

```bash
wsl bash -c "export GAZEBO_PLUGIN_PATH=\$GAZEBO_PLUGIN_PATH:~/gazebo_gst_plugin/build && gazebo"
```

### No Video Stream

1. Check if Gazebo is running with the plugin:
```bash
wsl bash -c "gazebo --verbose"
```

2. Test GStreamer pipeline:
```bash
wsl bash -c "gst-launch-1.0 videotestsrc ! x264enc ! rtph264pay ! udpsink host=127.0.0.1 port=5600"
```

3. In another terminal, receive:
```bash
wsl bash -c "gst-launch-1.0 udpsrc port=5600 ! application/x-rtp ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink"
```

### Firewall Issues

If streaming to Windows doesn't work, check Windows Firewall:

```powershell
New-NetFirewallRule -DisplayName "GStreamer UDP 5600" -Direction Inbound -Protocol UDP -LocalPort 5600 -Action Allow
```

## Advanced Configuration

### Change Video Quality

Modify the pipeline in `GstCameraPlugin.cc`:

```cpp
std::string pipelineStr = 
  "appsrc name=source ! "
  "videoconvert ! "
  "video/x-raw,format=I420 ! "
  "x264enc tune=zerolatency bitrate=2000 speed-preset=fast ! "  // Higher bitrate
  "rtph264pay ! "
  "udpsink host=" + udpHost + " port=" + std::to_string(udpPort);
```

Then rebuild:

```bash
wsl bash -c "cd ~/gazebo_gst_plugin/build && make && sudo make install"
```

### Multiple Cameras

To stream multiple cameras, use different ports:

```xml
<!-- Camera 1 -->
<plugin name="gst_camera_plugin_1" filename="libGstCameraPlugin.so">
  <udp_port>5600</udp_port>
</plugin>

<!-- Camera 2 -->
<plugin name="gst_camera_plugin_2" filename="libGstCameraPlugin.so">
  <udp_port>5601</udp_port>
</plugin>
```

## Integration with Python

Example Python code to receive the stream:

```python
import cv2

# For local stream
cap = cv2.VideoCapture("udp://127.0.0.1:5600", cv2.CAP_FFMPEG)

while True:
    ret, frame = cap.read()
    if ret:
        cv2.imshow("Gazebo Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
```

## References

- [Gazebo Plugin Tutorial](http://gazebosim.org/tutorials?tut=plugins_hello_world)
- [GStreamer Documentation](https://gstreamer.freedesktop.org/documentation/)
- [ROS Gazebo Plugins](http://gazebosim.org/tutorials?tut=ros_gzplugins)

## Support

If you encounter issues:
1. Check Gazebo logs: `~/.gazebo/server.log`
2. Verify GStreamer installation: `wsl bash -c "gst-inspect-1.0 --version"`
3. Test plugin loading: `wsl bash -c "gst-inspect-1.0 | grep -i plugin"`
