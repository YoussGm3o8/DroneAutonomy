# Drone Autonomy GUI

Modern PyQt6-based graphical interface for drone computer vision and autonomous task execution.

## Features

### 🎥 Live Video Display
- Real-time video streaming from multiple sources (webcam, RTSP, files)
- Overlay visualization modes:
  - RGB Only
  - Depth Overlay (adjustable opacity)
  - Depth Heatmap (TURBO colormap)
  - Detections Only
  - Full Overlay (all visualizations combined)
- Detection bounding boxes with class labels and confidence scores
- Telemetry overlay (GPS, altitude, speed, heading)
- State machine status display
- Click-to-point interaction on video frame
- Screenshot capture with automatic timestamping

### ⚙️ Task Control Panel
- Task selection from available competition tasks:
  - Target Search
  - Waypoint Navigation
  - Obstacle Course
  - Precision Landing
  - Autonomous Wet-Capture
  - Custom Competition Tasks
- Dynamic configuration UI based on selected task
- Start/Stop/Pause/Resume controls
- Real-time progress tracking
- Live score display
- Task execution logs with timestamps

### 📁 Media Gallery
- Organized tabs for different media types:
  - 📷 Photos - Target captures and deliverables
  - 🎥 Videos - Recorded sessions
  - 🖼️ Screenshots - Manual captures
  - 📋 Deliverables - Competition submissions (TXT, JSON, CSV)
- Thumbnail grid view for images/videos
- Full preview panel with file information
- Double-click video playback
- Export and delete functionality
- Open folder in system explorer
- Auto-refresh on file changes

### 📊 Results Viewer
- Multi-tab results display:
  - **Scores** - Performance metrics table with color coding
  - **Descriptions** - Target descriptions (text/JSON formatted)
  - **Logs** - Execution logs with level-based color coding (INFO, WARNING, ERROR, SUCCESS)
  - **Errors** - Separate error tracking panel
- Schema validation for competition deliverables
- Export descriptions and logs to files
- Session summary with key metrics

### 📡 Telemetry Display
- Real-time drone data monitoring:
  - **GPS Position** - Latitude, longitude, altitude, fix type
  - **Attitude** - Roll, pitch, yaw, heading
  - **Velocity** - Ground speed, vertical speed, airspeed
  - **Battery** - Voltage, current, percentage with color-coded progress bar
  - **System Status** - Armed state, failsafe, RC signal strength
- Connection status indicator with visual feedback
- Flight mode display
- Automatic unit formatting (degrees, m/s, meters, volts, etc.)

## Installation

### Prerequisites
- Python 3.11 or 3.12
- PyQt6 framework
- OpenCV with CUDA support (optional but recommended)
- All base project dependencies

### Install GUI Dependencies

```bash
# Install PyQt6
pip install PyQt6 PyQt6-Qt6

# Or install all requirements
pip install -r requirements.txt
```

## Usage

### Launch GUI

```bash
# Basic launch with webcam
python launch_gui.py

# Launch with RTSP stream
python launch_gui.py --video-source rtsp://192.168.1.100:8554/stream

# Launch with video file
python launch_gui.py --video-source file:output/videos/test.mp4

# Launch with custom configuration
python launch_gui.py --config config/high_performance.yaml

# Launch in fullscreen mode
python launch_gui.py --fullscreen

# Launch in demo mode (simulated data)
python launch_gui.py --demo-mode
```

### Quick Start Guide

1. **Connect Video Source**
   - Click toolbar buttons: 📷 Webcam, 📡 RTSP Stream, or 📁 Video File
   - Or use command line arguments when launching

2. **Select Task**
   - Go to "Task Control" tab
   - Choose task from dropdown
   - Configure task-specific parameters

3. **Start Execution**
   - Click "▶ Start Task" button
   - Monitor progress in status panel
   - View live scoring and logs

4. **View Results**
   - Check "Scores" tab for performance metrics
   - View "Descriptions" for competition deliverables
   - Review "Logs" for execution details

5. **Review Media**
   - Switch to "Media" tab
   - Browse photos, videos, screenshots
   - Double-click videos to play
   - Export or delete files as needed

6. **Monitor Telemetry**
   - Right panel shows real-time drone data
   - GPS, attitude, velocity, battery
   - Connection status and flight mode

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open Configuration |
| `Ctrl+S` | Save Screenshot |
| `Ctrl+Q` | Quit Application |
| `F1` | Open Documentation |
| `F5` | Refresh Media Gallery |
| `F11` | Toggle Fullscreen |

## Menu Bar

### File
- **Open Configuration...** - Load task configuration YAML
- **Save Configuration...** - Save current settings
- **Export Results...** - Export task results to JSON
- **Exit** - Close application

### View
- **Fullscreen** - Toggle fullscreen mode
- **Refresh Media Gallery** - Reload media files
- **Clear Results** - Reset results viewer

### Tools
- **Camera Calibration...** - Launch calibration tool
- **Run Diagnostics** - System health check

### Help
- **Documentation** - Open project README
- **About** - Application information

## Toolbar Actions

| Button | Function |
|--------|----------|
| 📷 Webcam | Switch to webcam input |
| 📡 RTSP Stream | Connect to RTSP stream |
| 📁 Video File | Open video file |
| ⏺ Record | Start/stop video recording |
| 📸 Screenshot | Capture current frame |
| 🔌 Connect | Connect to drone (MAVLink) |

## Video Visualization Modes

### RGB Only
Pure camera feed without overlays.

### Depth Overlay
Blends depth heatmap with RGB frame. Opacity adjustable via slider (0-100%).

### Depth Heatmap
Full depth visualization using TURBO colormap:
- 🔵 Blue = Close
- 🟢 Green = Medium
- 🔴 Red = Far

### Detections Only
Shows bounding boxes, labels, and confidence scores for detected objects. Color coded by class:
- Red = Targets
- Blue = Obstacles
- Green = Landing pads
- Yellow = People

### Full Overlay
Combines all visualizations:
- Depth heatmap (adjustable opacity)
- Detection bounding boxes
- Telemetry data (top-left)
- State machine status (bottom-left)
- Center crosshairs on detections

## Task Configuration Examples

### Target Search
```yaml
max_targets: 5
timeout: 300  # seconds
confidence_threshold: 0.6
auto_capture: true
```

### Autonomous Wet-Capture
```yaml
approach_distance: 0.7  # meters
stabilization_time: 2.0  # seconds
water_duration: 2.0  # seconds
auto_upload: true
```

### Waypoint Navigation
```yaml
waypoint_tolerance: 2.0  # meters
max_altitude: 30  # meters
cruise_speed: 5.0  # m/s
```

## Integration with Pipeline

The GUI integrates with the existing `DroneAutonomy` pipeline:

```python
from drone_autonomy.gui.main_window import MainWindow
from drone_autonomy.pipeline import Pipeline

# Create pipeline
pipeline = Pipeline(config_path="config/default_config.yaml")

# Create GUI window
window = MainWindow()
window.set_pipeline(pipeline)

# Start video processing
window.start_video_thread()
```

## Architecture

### Component Structure

```
gui/
├── __init__.py              # Module exports
├── main_window.py           # Main application window
├── video_widget.py          # Video display with overlays
├── task_control.py          # Task selection and control
├── media_gallery.py         # Media file browser
├── results_viewer.py        # Results and logs display
└── telemetry_display.py     # Real-time telemetry panel
```

### Signal/Slot Connections

- **VideoWidget.frame_clicked** → MainWindow (click coordinates)
- **TaskControlPanel.task_start_requested** → MainWindow (task name, config)
- **TaskControlPanel.task_stop_requested** → MainWindow (stop signal)
- **MediaGallery.media_selected** → MainWindow (file path)
- **MediaGallery.video_play_requested** → MainWindow (playback request)
- **VideoProcessingThread.frame_ready** → VideoWidget (frame update)

### Threading Model

- **Main Thread** - GUI event loop (PyQt6)
- **VideoProcessingThread** - Pipeline processing (~30 FPS)
- Non-blocking UI with responsive interaction

## Customization

### Adding Custom Tasks

1. Create task class in `src/drone_autonomy/tasks/`
2. Add to `TaskControlPanel._build_config_ui()`
3. Update task descriptions dictionary
4. Implement configuration widgets

### Custom Overlays

Extend `VideoWidget` with custom drawing methods:

```python
def _draw_custom_overlay(self, frame: np.ndarray) -> np.ndarray:
    """Draw custom visualization"""
    # Your custom drawing code
    return frame
```

### Theming

Modify stylesheets in component `init_ui()` methods:

```python
widget.setStyleSheet("""
    QWidget {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    QPushButton {
        background-color: #007bff;
        border-radius: 5px;
        padding: 10px;
    }
""")
```

## Troubleshooting

### PyQt6 Import Errors
```bash
pip install --upgrade PyQt6 PyQt6-Qt6
```

### Video Not Displaying
- Check video source connection
- Verify camera permissions
- Test with `opencv-python` directly

### Telemetry Not Updating
- Verify MAVLink connection string
- Check firewall settings for UDP ports
- Test with `examples/test_airsim.py`

### High CPU Usage
- Reduce video resolution in config
- Lower frame rate in VideoProcessingThread
- Disable depth overlay if not needed

### GUI Freezing
- Ensure VideoProcessingThread is running
- Check for blocking operations in main thread
- Use async I/O for file operations

## Performance Tips

1. **GPU Acceleration** - Enable CUDA for depth estimation and YOLO
2. **Resolution** - Use 640x480 or 1280x720 for real-time performance
3. **Overlay Opacity** - Lower depth opacity reduces blending overhead
4. **Frame Skip** - Process every 2nd or 3rd frame for slower systems
5. **Disable Unused** - Turn off overlays not needed for current task

## Future Enhancements

- [ ] Mission planning map view (GPS waypoint editor)
- [ ] Graph plots for telemetry history
- [ ] Multi-drone control interface
- [ ] Real-time data streaming to competition server
- [ ] Augmented reality overlay for target tracking
- [ ] Voice command integration
- [ ] Mobile companion app (remote monitoring)

## Contributing

To add new GUI features:

1. Create component in `src/drone_autonomy/gui/`
2. Integrate with `MainWindow`
3. Add to `__init__.py` exports
4. Update this README
5. Test on Windows and Linux

## License

Same license as parent DroneAutonomy project.

## Support

For GUI-specific issues:
- Check console output for Qt warnings
- Enable debug logging: `export QT_LOGGING_RULES="*.debug=true"`
- Test components individually before integration

---

**Built with PyQt6 and ❤️ for drone autonomy**
