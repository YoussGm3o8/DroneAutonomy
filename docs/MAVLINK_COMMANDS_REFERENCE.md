# MAVLink Commands Quick Reference

Quick reference for all MAVLink commands available in the DroneAutonomy system.

## Connection

```python
from drone_autonomy.mavlink.telemetry import MAVLinkTelemetry

mavlink = MAVLinkTelemetry({
    'connection_string': 'udp:127.0.0.1:14550',  # SITL
    # 'connection_string': '/dev/ttyUSB0:57600',  # Serial
    # 'connection_string': 'udpin:0.0.0.0:14550',  # WiFi
})

mavlink.connect()
```

## Basic Commands

### Arm/Disarm

```python
mavlink.arm()         # Arm motors
mavlink.disarm()      # Disarm motors (safe on ground)
```

### Flight Modes

```python
mavlink.set_mode("STABILIZE")   # Manual stabilization
mavlink.set_mode("ALT_HOLD")    # Altitude hold
mavlink.set_mode("LOITER")      # Position hold (GPS)
mavlink.set_mode("GUIDED")      # Autonomous control
mavlink.set_mode("RTL")         # Return to launch
mavlink.set_mode("LAND")        # Auto land
mavlink.set_mode("BRAKE")       # Emergency brake
```

### Takeoff/Land

```python
mavlink.takeoff(altitude=10.0)   # Takeoff to 10m
mavlink.land()                   # Land at current position
mavlink.return_to_launch()       # RTL
```

## Movement Commands

### Velocity Control (Body Frame)

```python
# Forward, right, down, yaw_rate
mavlink.send_velocity_body(
    vx=2.0,      # Forward 2 m/s
    vy=0.5,      # Right 0.5 m/s
    vz=0.0,      # Hold altitude
    yaw_rate=0.1 # Rotate slowly
)
```

### Velocity Control (NED Frame)

```python
# North, East, Down, yaw_rate
mavlink.send_velocity_ned(
    vx=2.0,  # North 2 m/s
    vy=1.0,  # East 1 m/s
    vz=0.0,  # Hold altitude
    yaw_rate=0.0
)
```

### Velocity with Yaw

```python
mavlink.send_velocity_with_yaw(
    vx=2.0, vy=0.0, vz=0.0,
    yaw_deg=90.0,  # Face east
    frame="body"   # or "ned"
)
```

### Position Control (Local)

```python
# North, East, Down (negative = up), yaw
mavlink.send_position_target(
    x=10.0,   # 10m north
    y=5.0,    # 5m east
    z=-10.0,  # 10m up
    yaw=1.57  # Face east (radians)
)
```

### Position Control (Global GPS)

```python
mavlink.goto_position_global(
    lat=47.123456,
    lon=-122.654321,
    alt=10.0  # meters above sea level
)
```

### Yaw Control

```python
# Absolute yaw (0-360°, 0=North)
mavlink.set_yaw(yaw_deg=180.0, relative=False)

# Relative yaw (turn from current)
mavlink.set_yaw(yaw_deg=45.0, relative=True)

# With custom rate
mavlink.set_yaw(
    yaw_deg=90.0,
    yaw_rate_degs=30.0,  # Rotate at 30°/s
    relative=False
)
```

## Safety Commands

### Pause/Resume

```python
mavlink.pause()          # Hold position (BRAKE/LOITER)
mavlink.resume_guided()  # Resume GUIDED mode
```

### Emergency Stop

```python
mavlink.emergency_stop()  # Force disarm (DANGER: drone will fall!)
```

### Set Home Position

```python
# Set home to current position
mavlink.set_home_position()

# Set home to specific location
mavlink.set_home_position(
    lat=47.123456,
    lon=-122.654321,
    alt=100.0
)
```

## Telemetry Reading

### Read All Telemetry

```python
telemetry = mavlink.read_telemetry()

# Returns dict with:
# - attitude: roll, pitch, yaw, heading, rates
# - position: lat, lon, altitude, relative_altitude
# - velocity: ground_speed, vertical_speed
# - gps: fix_type, satellites, accuracy
# - battery: voltage, current, remaining
# - flight_mode: current mode
# - armed: True/False
```

### Flattened Telemetry (for GUI)

```python
flat = mavlink.get_flattened_telemetry()

# Access directly:
print(f"Altitude: {flat['relative_altitude']:.1f}m")
print(f"Battery: {flat['battery_remaining']}%")
print(f"Armed: {flat['armed']}")
```

### Specific Telemetry

```python
# Attitude
if mavlink.attitude:
    roll = mavlink.attitude['roll']    # radians
    pitch = mavlink.attitude['pitch']
    yaw = mavlink.attitude['yaw']

# Position
if mavlink.position:
    lat = mavlink.position['lat']      # degrees
    lon = mavlink.position['lon']
    alt = mavlink.position['relative_alt']  # meters

# Battery
if mavlink.battery_status:
    voltage = mavlink.battery_status['voltage']      # volts
    current = mavlink.battery_status['current']      # amps
    remaining = mavlink.battery_status['remaining']  # percent
```

### State Properties

```python
is_armed = mavlink.armed
current_mode = mavlink.flight_mode
is_connected = mavlink.is_connected

# Check for state changes
if mavlink.armed_changed:
    print(f"Armed state changed to: {mavlink.armed}")
    mavlink.clear_armed_changed()

if mavlink.flight_mode_changed:
    print(f"Flight mode changed to: {mavlink.flight_mode}")
    mavlink.clear_flight_mode_changed()
```

## Visual Odometry

### Publish VIO

```python
import numpy as np

position = np.array([1.0, 2.0, -5.0])  # NED: North, East, Down
orientation = np.array([1.0, 0.0, 0.0, 0.0])  # Quaternion [w,x,y,z]
velocity = np.array([0.5, 0.0, 0.0])  # Optional
covariance = np.eye(6) * 0.1  # Optional 6x6 matrix

mavlink.publish_visual_odometry(
    position=position,
    orientation=orientation,
    velocity=velocity,
    covariance=covariance
)
```

## Command Logging

### Set Callback for GUI

```python
def log_callback(message, level):
    print(f"[{level}] {message}")

mavlink.set_command_logger(log_callback)

# Now all commands will be logged via callback
mavlink.arm()  # Logs: "ARM command sent to vehicle"
```

## Complete Example

```python
from drone_autonomy.mavlink.telemetry import MAVLinkTelemetry
import time

# Connect
mavlink = MAVLinkTelemetry({'connection_string': 'udp:127.0.0.1:14550'})
if not mavlink.connect():
    print("Connection failed")
    exit(1)

# Wait for valid position
while True:
    telemetry = mavlink.read_telemetry()
    if 'position' in telemetry:
        print(f"GPS position: {telemetry['position']}")
        break
    time.sleep(0.5)

# Setup for autonomous flight
mavlink.set_mode("GUIDED")
time.sleep(1)

mavlink.arm()
time.sleep(1)

# Takeoff
mavlink.takeoff(altitude=5.0)
print("Taking off to 5m...")
time.sleep(10)

# Fly forward slowly
print("Flying forward...")
for _ in range(20):
    mavlink.send_velocity_body(1.0, 0, 0, 0)  # 1 m/s forward
    time.sleep(0.5)

# Stop
mavlink.send_velocity_body(0, 0, 0, 0)
print("Holding position...")
time.sleep(3)

# Return and land
print("Returning to launch...")
mavlink.return_to_launch()
time.sleep(20)

# Cleanup
mavlink.disarm()
mavlink.disconnect()
print("Done!")
```

## Type Masks for Position/Velocity Commands

When using `set_position_target_local_ned_send`, the type_mask controls which fields are used:

```python
# Velocity only (position ignored)
type_mask = 0b0000111111000111

# Position only (velocity ignored)
type_mask = 0b0000111111111000

# Position + Velocity
type_mask = 0b0000111111000000

# All fields active
type_mask = 0b0000000000000000
```

## Coordinate Frames

### Body Frame (FRD)
- **X**: Forward (nose direction)
- **Y**: Right (right wing)
- **Z**: Down

### NED Frame (World)
- **X**: North
- **Y**: East
- **Z**: Down

### Conversions

```python
# Degrees ↔ Radians
DEG_TO_RAD = 0.017453292519943  # π/180
RAD_TO_DEG = 57.29577951308232  # 180/π

yaw_rad = yaw_deg * DEG_TO_RAD
yaw_deg = yaw_rad * RAD_TO_DEG
```

## Error Handling

```python
try:
    if not mavlink.connect():
        raise ConnectionError("Failed to connect to MAVLink")

    if not mavlink.set_mode("GUIDED"):
        raise RuntimeError("Failed to set GUIDED mode")

    # Your flight code here...

except Exception as e:
    print(f"Error: {e}")
    if mavlink.is_connected:
        mavlink.emergency_stop()  # Safe failsafe
finally:
    if mavlink.is_connected:
        mavlink.disconnect()
```

## Best Practices

1. **Always check connection** before sending commands
2. **Wait for mode changes** to take effect (use telemetry feedback)
3. **Use rate limiting** for velocity commands (10-20 Hz is sufficient)
4. **Implement timeouts** for critical operations
5. **Monitor battery** and GPS status before autonomous flight
6. **Test in SITL** before flying real hardware
7. **Keep manual RC control** as backup override
8. **Set geofence limits** in ArduPilot parameters

## Troubleshooting

### Connection Issues
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Command Not Executing
```python
# Check telemetry for actual state
telemetry = mavlink.read_telemetry()
print(f"Mode: {telemetry['flight_mode']}")
print(f"Armed: {telemetry['armed']}")

# Ensure GUIDED mode for autonomous commands
if telemetry['flight_mode'] != 'GUIDED':
    mavlink.set_mode('GUIDED')
    time.sleep(2)
```

### Lost Connection Recovery
```python
# Reconnect
mavlink.disconnect()
time.sleep(1)
if mavlink.connect():
    print("Reconnected!")
```

## Related Documentation

- [MAVLink Protocol Specification](https://mavlink.io/en/)
- [ArduPilot MAVLink Commands](https://ardupilot.org/dev/docs/copter-commands-in-guided-mode.html)
- [MAVLink Object Avoidance Guide](MAVLINK_OBJECT_AVOIDANCE.md)
