# DroneAutonomy Operator Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Pre-Flight Checklist](#pre-flight-checklist)
3. [Setup and Configuration](#setup-and-configuration)
4. [Operation Procedures](#operation-procedures)
5. [Monitoring and Telemetry](#monitoring-and-telemetry)
6. [Troubleshooting](#troubleshooting)
7. [Safety Protocols](#safety-protocols)

## System Overview

DroneAutonomy provides real-time autonomous perception for obstacle avoidance and target detection using:
- Monocular RGB camera input
- Visual odometry for positioning
- Depth estimation for proximity awareness
- Object and target detection
- MAVLink integration with ArduPilot

### System Components

```
┌─────────────────┐
│  Forward Camera │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  Video Stream   │──────▶│ NVIDIA GPU   │
│  (GStreamer)    │      │ Processing   │
└─────────────────┘      └──────┬───────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
                    ▼           ▼           ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐
              │   VIO   │ │  Depth  │ │Detection│
              └────┬────┘ └────┬────┘ └────┬────┘
                   │           │           │
                   └───────────┼───────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │Fusion Layer  │
                        └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   MAVLink    │
                        │to ArduPilot  │
                        └──────────────┘
```

## Pre-Flight Checklist

### Hardware Checks

- [ ] NVIDIA RTX 3060 laptop powered on and drivers up-to-date
- [ ] Forward camera connected and functional
- [ ] Wi-Fi/UDP connection established between laptop and vehicle
- [ ] Vehicle powered on and ArduPilot running
- [ ] Ground station connected and monitoring telemetry
- [ ] Laptop battery charged or AC power connected
- [ ] Camera lens clean and unobstructed

### Software Checks

- [ ] DroneAutonomy environment activated
- [ ] Configuration file prepared and validated
- [ ] Camera calibration file loaded
- [ ] YOLO weights available
- [ ] MiDaS model downloaded
- [ ] MAVLink connection string configured
- [ ] Log directory writable

### ArduPilot Configuration

Verify the following parameters are set on the vehicle:

```
# Visual Odometry Settings
EK3_SRC1_POSXY = 6   # ExternalNav for position
EK3_SRC1_VELXY = 6   # ExternalNav for velocity
EK3_SRC1_POSZ = 1    # Baro for altitude
VISO_TYPE = 1        # MAV vision odometry

# Optional: Fallback settings
EK3_SRC2_POSXY = 3   # GPS fallback
EK3_SRC2_VELXY = 3   # GPS fallback
```

## Setup and Configuration

### 1. Camera Calibration

Before first flight, calibrate the camera:

```bash
python examples/calibrate_camera.py --images calibration_images/ --output config/camera_calibration.json
```

Update `config/flight_config.yaml`:

```yaml
camera:
  calibration_file: config/camera_calibration.json
```

### 2. Configuration File

Create a flight-specific configuration file based on `config/default_config.yaml`:

```bash
cp config/default_config.yaml config/flight_config.yaml
```

Edit key parameters:

```yaml
# Video configuration
video:
  gstreamer_pipeline: "udpsrc port=5600 ! ..."  # Match your camera
  width: 1280
  height: 720

# MAVLink configuration
mavlink:
  connection_string: "udp:192.168.1.100:14550"  # Vehicle IP

# Detection thresholds
detection:
  confidence_threshold: 0.6  # Adjust for environment

fusion:
  proximity_threshold: 3.0   # Obstacle avoidance distance (meters)
```

### 3. Network Setup

Ensure laptop and vehicle are on the same network:

```bash
# Test connectivity
ping 192.168.1.100  # Vehicle IP

# Test MAVLink port
nc -zu 192.168.1.100 14550
```

## Operation Procedures

### Bench Test Procedure

Before field operation, verify system on the bench:

1. **Start the pipeline without vehicle:**
   ```bash
   python -m drone_autonomy.pipeline --config config/flight_config.yaml
   ```

2. **Verify video stream:**
   - Confirm camera feed displays
   - Check frame rate (should be 20-30 FPS)

3. **Test VIO with handheld movement:**
   - Move camera slowly through workspace
   - Observe pose estimates in log
   - Verify pose stays stable when stationary

4. **Connect to vehicle (on bench, motors off):**
   - Verify MAVLink connection established
   - Check ground station receives vision messages
   - Monitor VIO health in Mission Planner/QGroundControl

### Simulation Test Procedure

Test in AirSim before field operation:

1. **Launch AirSim:**
   - Start AirSim with drone environment
   - Note IP address (usually 127.0.0.1)

2. **Configure for simulation:**
   ```yaml
   simulation:
     enabled: true
     airsim_ip: 127.0.0.1
   ```

3. **Run pipeline:**
   ```bash
   python -m drone_autonomy.pipeline --config config/sim_config.yaml
   ```

4. **Execute test mission:**
   - Takeoff to 5m altitude
   - Fly forward at 2 m/s
   - Verify obstacle detection
   - Test target detection with placed targets
   - Validate avoidance commands

### Field Operation Procedure

#### Pre-Flight

1. **Position Setup:**
   - Place laptop 10-20m from takeoff location
   - Ensure clear line of sight to vehicle
   - Set up shade for laptop screen

2. **Start System:**
   ```bash
   python -m drone_autonomy.pipeline --config config/flight_config.yaml
   ```

3. **Verify Status:**
   - Check "Connected to MAVLink" in log
   - Verify video feed active
   - Monitor FPS (should be >20)
   - Confirm VIO initialization

4. **Ground Station Check:**
   - Open Mission Planner or QGroundControl
   - Verify VISION_POSITION_ESTIMATE messages received
   - Check EKF status (should show ExternalNav active)

#### In-Flight Monitoring

1. **Hover Test (1-2 minutes):**
   - Takeoff to 2m altitude
   - Hold position
   - Monitor VIO drift
   - Verify depth estimates
   - Check detection latency

2. **Slow Translation (2-5 m/s):**
   - Fly forward slowly
   - Observe obstacle detection
   - Monitor avoidance commands
   - Check target detection if applicable

3. **Performance Monitoring:**
   Watch for:
   - FPS drops (should stay >20)
   - VIO tracking loss
   - Detection confidence
   - GPU temperature
   - Latency increases

#### Post-Flight

1. **Stop Pipeline:**
   - Press 'q' or Ctrl+C
   - Wait for graceful shutdown
   - Verify logs saved

2. **Review Logs:**
   ```bash
   cd logs
   tail -f drone_autonomy_YYYYMMDD_HHMMSS.log
   ```

3. **Performance Analysis:**
   - Check average FPS
   - Review VIO accuracy (if ground truth available)
   - Analyze detection performance
   - Note any anomalies

## Monitoring and Telemetry

### Real-Time Display

The main display shows:
- Live camera feed with detection overlays
- Depth map visualization (separate window)
- Frame count and FPS
- VIO position estimate
- Detection bounding boxes
- Target markers

### Console Output

Monitor the console for:
```
INFO - Frame 30, FPS: 25.3
INFO - Detections: 2 (person, car)
INFO - Targets: 1 (confidence 0.85)
INFO - VIO position: [1.23, 0.45, -0.78]
WARNING - Detection confidence low: 0.45
```

### Ground Station Telemetry

In Mission Planner/QGroundControl:
1. Open MAVLink Inspector
2. Filter for VISION_POSITION_ESTIMATE messages
3. Verify rate is 20-30 Hz
4. Check EKF status shows ExternalNav active

### Log Files

Logs are saved to `logs/drone_autonomy_TIMESTAMP.log`:
- Frame timing and performance
- VIO estimates and covariance
- Detection results
- MAVLink status
- Warnings and errors

## Troubleshooting

### Video Stream Issues

**Symptom:** No video feed

**Checks:**
1. Verify camera connection: `ls /dev/video*`
2. Test GStreamer pipeline:
   ```bash
   gst-launch-1.0 udpsrc port=5600 ! ...
   ```
3. Check firewall rules
4. Try fallback to OpenCV: Set `backend: opencv` in config

### VIO Issues

**Symptom:** VIO tracking loss or drift

**Solutions:**
1. Ensure adequate texture in environment
2. Avoid fast rotation
3. Check camera exposure (not over/under exposed)
4. Verify camera calibration
5. Reduce motion speed

**Symptom:** VIO initialization fails

**Solutions:**
1. Move camera to see textured surfaces
2. Avoid featureless environments (sky, blank walls)
3. Check camera calibration parameters
4. Verify adequate lighting

### MAVLink Issues

**Symptom:** Cannot connect to vehicle

**Solutions:**
1. Verify IP address and port
2. Check network connectivity
3. Ensure vehicle MAVLink enabled
4. Test with ground station first
5. Check firewall rules

**Symptom:** VIO messages not accepted by ArduPilot

**Solutions:**
1. Verify ArduPilot parameters (EK3_SRC1_POSXY, VISO_TYPE)
2. Check message format in MAVLink inspector
3. Verify message rate is 20-30 Hz
4. Restart ArduPilot after parameter changes

### Performance Issues

**Symptom:** Low FPS (<20)

**Solutions:**
1. Enable TensorRT optimization
2. Use smaller models (MiDaS_small, yolov8n)
3. Reduce video resolution
4. Close other GPU applications
5. Check GPU temperature and throttling

**Symptom:** High latency

**Solutions:**
1. Reduce depth output scale
2. Skip depth estimation every other frame
3. Reduce detection frequency
4. Optimize GStreamer pipeline

### Detection Issues

**Symptom:** False positives

**Solutions:**
1. Increase confidence threshold (0.6-0.7)
2. Adjust fusion weights
3. Filter by detection size
4. Fine-tune YOLO on environment

**Symptom:** Missed detections

**Solutions:**
1. Decrease confidence threshold (0.4-0.5)
2. Improve lighting conditions
3. Clean camera lens
4. Use larger YOLO model (yolov8s or yolov8m)

## Safety Protocols

### Emergency Procedures

**Loss of VIO:**
1. Vehicle should automatically switch to GPS mode (if EK3_SRC2 configured)
2. Pilot takes manual control
3. Land immediately if no GPS
4. Do not attempt to restart VIO in flight

**System Freeze/Crash:**
1. Pilot maintains manual control
2. Land vehicle safely
3. Restart system on ground
4. Review logs before next flight

**Obstacle Detection Alert:**
1. System should log warning
2. Monitor avoidance commands
3. Pilot ready to override if needed
4. Reduce speed if multiple obstacles

### Operational Limits

**DO NOT OPERATE:**
- In heavy rain or fog (camera will fail)
- In very dark conditions (<100 lux)
- In featureless environments (sky, ocean)
- At speeds >10 m/s (VIO may fail)
- With GPU temperature >85°C

**OPERATIONAL RESTRICTIONS:**
- Maintain line of sight to vehicle
- Keep laptop within Wi-Fi range
- Monitor battery levels (laptop and vehicle)
- Have manual override ready
- Test in simulation first

### Pre-Flight Safety Brief

Before each flight:
1. Brief all personnel on system status
2. Identify safety pilot with manual override
3. Establish communication protocols
4. Define abort procedures
5. Mark safe landing zones
6. Check emergency shutoff procedure

## Parameter Tuning

### Detection Sensitivity

Adjust based on environment:

**High-clutter environment:**
```yaml
detection:
  confidence_threshold: 0.65
fusion:
  min_confidence: 0.7
```

**Open environment:**
```yaml
detection:
  confidence_threshold: 0.45
fusion:
  min_confidence: 0.55
```

### Avoidance Behavior

Adjust proximity threshold:

**Conservative (early avoidance):**
```yaml
fusion:
  proximity_threshold: 5.0  # meters
```

**Aggressive (close approach):**
```yaml
fusion:
  proximity_threshold: 2.0  # meters
```

### VIO Tuning

Adjust output rate based on needs:

**High accuracy (slower):**
```yaml
vio:
  output_rate: 20  # Hz
```

**Low latency (faster):**
```yaml
vio:
  output_rate: 40  # Hz
```

## Maintenance

### Daily
- Check camera lens cleanliness
- Verify log storage space
- Monitor GPU temperature trends

### Weekly
- Review detection performance
- Update model weights if available
- Check for software updates

### Monthly
- Re-calibrate camera if needed
- Review and archive logs
- Performance benchmark tests
- Update documentation

## Contact Information

For technical support:
- GitHub Issues: https://github.com/YoussGm3o8/DroneAutonomy/issues
- Emergency: [Your contact info]

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-01-01 | Initial operator guide |
