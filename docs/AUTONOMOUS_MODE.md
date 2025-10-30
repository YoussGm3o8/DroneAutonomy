# Autonomous Navigation Mode - User Guide

## Overview

The DroneAutonomy system now includes a fully autonomous navigation mode that enables the drone to:

✅ **Avoid obstacles** using depth estimation  
✅ **Detect and track red circular targets**  
✅ **Center camera on targets** using PID control  
✅ **Safely approach targets** while maintaining minimum distance  
✅ **Log GPS coordinates, heading, and altitude** for each target  
✅ **Capture photos** when targets are locked  

---

## Quick Start

### Enable Autonomous Mode

```bash
# Basic autonomous mode (with default config)
python src/drone_autonomy/pipeline.py --autonomous

# With balanced performance mode (18 FPS)
python src/drone_autonomy/pipeline.py --autonomous --interval 2

# With full quality mode (12 FPS, best for obstacle detection)
python src/drone_autonomy/pipeline.py --autonomous --interval 1
```

### Recommended Settings for Real Drone

```bash
# Best configuration for real autonomous flight
python src/drone_autonomy/pipeline.py --autonomous --interval 2
```

This provides:
- **18 FPS** processing rate (balanced)
- **Depth estimation enabled** for obstacle avoidance
- **All detection enabled** (YOLO + Target detection)
- **Real-time control** with good safety margins

---

## Navigation State Machine

The autonomous controller operates as a state machine:

### States

1. **IDLE** 🟢
   - Initial state, waiting for activation
   - No commands sent to drone

2. **SEARCHING** 🔵
   - Actively searching for targets
   - Maintains position or executes search pattern (future)
   - Monitoring for obstacles

3. **TARGET_DETECTED** 🟡
   - Target found in frame
   - Transition state to CENTERING

4. **CENTERING** 🟡
   - Rotating drone to center target in frame
   - Uses PID controller for smooth yaw control
   - Target must be within ±50 pixels of center (configurable)

5. **APPROACHING** 🟠
   - Moving forward toward centered target
   - Continuously monitors depth to maintain safe distance
   - Target distance: **2.0m** (configurable)
   - Minimum distance: **1.5m** (safety limit)

6. **TARGET_LOCKED** 🟢
   - Target at perfect distance and centered
   - **GPS coordinates logged**
   - **Photo captured**
   - **CSV entry created**
   - Returns to SEARCHING for next target

7. **AVOIDING_OBSTACLE** 🔴
   - Obstacle detected in path
   - Lateral movement to avoid obstacle
   - Backs up if center blocked
   - Returns to SEARCHING when clear

8. **EMERGENCY_STOP** 🚨
   - Emergency halt (future: triggered by safety events)
   - All commands zeroed
   - Requires manual reset

---

## Configuration

### Autonomous Parameters

Edit `config/default_config.yaml` or `config/autonomous.yaml`:

```yaml
autonomous:
  # Obstacle detection
  obstacle_distance_threshold: 3.0  # meters - closer = obstacle
  
  # Target approach
  approach_distance_target: 2.0  # ideal distance from target
  approach_distance_min: 1.5  # minimum safe distance
  centering_tolerance: 50  # pixels from center
  
  # PID controller (for centering)
  pid_kp: 0.5  # Proportional gain
  pid_ki: 0.1  # Integral gain
  pid_kd: 0.2  # Derivative gain
  
  # Speed limits
  max_yaw_rate: 30.0  # deg/s
  max_forward_speed: 1.0  # m/s
  max_lateral_speed: 0.5  # m/s
  
  # Logging
  log_dir: logs/autonomous
  photo_dir: logs/autonomous/photos
```

### Tuning Tips

#### For Faster Response (Aggressive)
```yaml
pid_kp: 0.8  # Higher = faster correction
max_yaw_rate: 45.0  # deg/s
max_forward_speed: 1.5  # m/s
```

#### For Smoother Control (Conservative)
```yaml
pid_kp: 0.3  # Lower = smoother motion
max_yaw_rate: 20.0  # deg/s
max_forward_speed: 0.7  # m/s
```

#### For Indoor/Tight Spaces
```yaml
obstacle_distance_threshold: 4.0  # More conservative
approach_distance_target: 2.5  # Stop further away
max_forward_speed: 0.5  # Slower speed
```

---

## Output Files

### Target Log CSV

Location: `logs/autonomous/targets_YYYYMMDD_HHMMSS.csv`

Columns:
- `timestamp` - ISO 8601 timestamp
- `latitude` - GPS latitude (from MAVLink)
- `longitude` - GPS longitude (from MAVLink)
- `altitude_msl` - Altitude MSL in meters
- `altitude_rel` - Altitude relative to home in meters
- `heading` - Drone heading in degrees
- `distance_to_target` - Estimated distance in meters
- `target_center_x` - Target pixel x coordinate
- `target_center_y` - Target pixel y coordinate
- `photo_filename` - Associated photo filename

### Target Photos

Location: `logs/autonomous/photos/target_YYYYMMDD_HHMMSS.jpg`

- Full resolution (1920x1080) images
- Captured when target is locked (centered + at correct distance)
- Filenames match timestamps in CSV

---

## Depth-Based Distance Estimation

### How It Works

MiDaS depth estimation provides **relative depth**, not metric distance.

The system uses this mapping:
```
depth_value = 1.0 (black) → 0.5m (very close)
depth_value = 0.0 (white) → 10m (far)
```

### Calibration (Future Enhancement)

For **accurate metric distances**, you can calibrate using known targets:

1. Place target at known distance (e.g., 2.0m)
2. Record depth_value from target region
3. Update `_depth_to_distance()` function with calibration data

---

## Obstacle Avoidance Logic

### Detection

The system checks the **center region** (middle 1/3 of frame):

```
Obstacle detected if:
  - More than 10% of center pixels have depth > 0.7 (close)
  - Threshold distance: 3.0m (configurable)
```

### Avoidance Behavior

**If obstacle on left** → Move right  
**If obstacle on right** → Move left  
**If obstacle in center** → Back up  

The drone continues avoidance until the obstacle clears, then returns to SEARCHING state.

---

## Safety Features

### Built-in Safety

1. **Minimum Approach Distance** - Won't get closer than 1.5m to targets
2. **Continuous Obstacle Monitoring** - Checks depth on every frame
3. **Automatic Back-up** - Backs away if too close
4. **State Transitions** - Smooth transitions prevent jarring movements

### Recommended Pre-Flight Checks

✅ Verify **MAVLink connection** is active (GPS required for logging)  
✅ Test **depth estimation** in similar lighting conditions  
✅ Confirm **target detection** works (red circular targets)  
✅ Check **emergency stop** procedure (Ctrl+C or 'q' key)  
✅ Have **manual takeover** ready (RC transmitter)  

---

## Command Reference

### Basic Commands

```bash
# Start autonomous mode
python src/drone_autonomy/pipeline.py --autonomous

# Autonomous + performance mode selection
python src/drone_autonomy/pipeline.py --autonomous
# Then choose 1, 2, or 3 interactively

# Autonomous + specific performance mode
python src/drone_autonomy/pipeline.py --autonomous --interval 2

# Autonomous + custom config
python src/drone_autonomy/pipeline.py --autonomous --config config/autonomous.yaml

# Autonomous without display (headless)
python src/drone_autonomy/pipeline.py --autonomous --no-display
```

### During Operation

- Press **'q'** - Quit autonomous mode
- Press **Ctrl+C** - Emergency interrupt
- **Close window** - Stops pipeline

---

## Visual Indicators (On-Screen Display)

### State Display

Color-coded state indicator in top-left:

- **SEARCHING** - 🔵 Cyan
- **CENTERING** - 🟡 Yellow
- **APPROACHING** - 🟡 Yellow
- **TARGET_LOCKED** - 🟢 Green
- **AVOIDING_OBSTACLE** - 🟠 Orange
- **EMERGENCY_STOP** - 🔴 Red

### Other Indicators

- **Frame counter** - Top-left
- **FPS** - Below frame counter
- **VIO position** - 3D position estimate (if enabled)
- **OBSTACLE DETECTED!** - Red warning when obstacle present

---

## Troubleshooting

### No GPS Data in Logs

**Cause**: MAVLink not connected or GPS fix not acquired  
**Solution**: 
- Verify MAVLink connection: Check for "MAVLink connected" in logs
- Wait for GPS fix (satellite lock)
- Check `mavlink.connection_string` in config

### Target Not Centering

**Cause**: PID gains too low or target detection inconsistent  
**Solution**:
- Increase `pid_kp` for faster response
- Check target is clearly red and circular
- Verify good lighting conditions
- Reduce `centering_tolerance` if centering is too loose

### Depth Estimation Inaccurate

**Cause**: Poor lighting, reflective surfaces, or distance calibration  
**Solution**:
- Avoid direct sunlight and deep shadows
- Avoid shiny/reflective surfaces
- Calibrate depth-to-distance mapping for your environment
- Use Mode 1 (full quality) for best depth accuracy

### Drone Too Aggressive

**Cause**: PID gains or speed limits too high  
**Solution**:
- Reduce `pid_kp`, `pid_ki`, `pid_kd`
- Lower `max_yaw_rate`, `max_forward_speed`
- Use conservative tuning parameters (see above)

### Photos Not Captured

**Cause**: Target never reaches "locked" state  
**Solution**:
- Check `approach_distance_target` is achievable
- Verify depth estimation is working (view depth window)
- Increase `centering_tolerance` for easier locking
- Check `photo_dir` exists and is writable

---

## Example Mission Workflow

### 1. Pre-Flight Setup

```bash
# Start pipeline with autonomous mode
python src/drone_autonomy/pipeline.py --autonomous --interval 2

# Verify in terminal:
# - "AutonomousController initialized"
# - "MAVLink connected"
# - "Autonomous navigation ENABLED"
```

### 2. Place Red Targets

- Use red circular targets (solid color)
- Place at various distances (2-10m recommended)
- Ensure good visibility and contrast

### 3. Start Mission

- Drone takes off (manual or pre-programmed)
- Autonomous mode enters **SEARCHING** state
- Maintains position while scanning for targets

### 4. Target Acquisition

1. **TARGET_DETECTED** - Red target found
2. **CENTERING** - Drone rotates to center target (yaw adjustments)
3. **APPROACHING** - Drone moves forward toward target
4. **TARGET_LOCKED** - Photo captured, GPS logged
5. **SEARCHING** - Returns to search for next target

### 5. Mission Complete

- Press 'q' or Ctrl+C to stop
- Review logs in `logs/autonomous/`
- Check photos in `logs/autonomous/photos/`
- Analyze CSV for target locations

---

## Performance Notes

### Recommended Modes

| Mode | FPS | Use Case |
|------|-----|----------|
| Mode 1 (interval=1) | 12 FPS | Maximum accuracy, indoor, tight spaces |
| Mode 2 (interval=2) | 18 FPS | **Best for autonomous** - balanced |
| Mode 3 (interval=3) | 28 FPS | Fast movement, wide open areas |

### Processing Bottlenecks

- **Depth estimation**: ~47ms (MiDaS_small on RTX 3060)
- **YOLO detection**: ~10ms (YOLOv8n on CUDA)
- **Target detection**: ~6ms (optimized with downscale=2)
- **Autonomous control**: <1ms (negligible)

**Total**: ~63ms → **~16 FPS theoretical max** (Mode 1)

---

## Future Enhancements

Planned features:

- [ ] MAVLink velocity control commands (SET_POSITION_TARGET_LOCAL_NED)
- [ ] Search pattern generation (grid, spiral)
- [ ] Battery monitoring with auto-RTL
- [ ] Kalman filtering for depth smoothing
- [ ] Multi-target mission planning
- [ ] Geofencing and safety boundaries
- [ ] Real-time mission replanning
- [ ] Advanced PID auto-tuning

---

## Safety Disclaimer

⚠️ **IMPORTANT SAFETY NOTICE** ⚠️

- **Always have manual control available** (RC transmitter)
- **Test in safe, controlled environment** first
- **Never rely solely on autonomous mode** for critical operations
- **Monitor battery levels** and maintain safe margins
- **Comply with local regulations** (FAA Part 107, etc.)
- **This is experimental software** - use at your own risk

The autonomous system is designed as an **assisted capability**, not a replacement for human judgment and oversight.

---

## Support

For issues, questions, or feature requests, check:
- `docs/TECHNICAL.md` - Technical implementation details
- `docs/OPERATOR_GUIDE.md` - General operation guide
- `logs/` - System logs for debugging

---

**Happy Flying! 🚁**
