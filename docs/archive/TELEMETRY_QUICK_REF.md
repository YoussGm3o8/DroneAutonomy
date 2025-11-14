# Telemetry Module - Quick Reference

## State Properties

### Armed State
```python
# Read current armed state
if telemetry.armed:
    print("Armed")

# Check if state changed (useful for event-driven code)
if telemetry.armed_changed:
    action = "ARMED" if telemetry.armed else "DISARMED"
    print(f"Vehicle {action}")
    telemetry.clear_armed_changed()  # Reset flag
```

### Flight Mode
```python
# Read current flight mode
print(f"Current mode: {telemetry.flight_mode}")  # e.g., "GUIDED"

# Check if mode changed
if telemetry.flight_mode_changed:
    print(f"Mode changed to: {telemetry.flight_mode}")
    telemetry.clear_flight_mode_changed()  # Reset flag
```

## Commands

### Arm/Disarm
```python
telemetry.arm()      # Send arm command
telemetry.disarm()   # Send disarm command
# Note: Wait for armed_changed flag to confirm actual state change
```

### Change Flight Mode
```python
telemetry.set_mode("GUIDED")      # Valid modes:
telemetry.set_mode("LOITER")      # STABILIZE, ACRO, ALT_HOLD, AUTO,
telemetry.set_mode("RTL")         # GUIDED, LOITER, RTL, CIRCLE,
                                  # LAND, DRIFT, SPORT, FLIP, etc.
```

### Send Velocity Commands
```python
# NED frame (North-East-Down)
telemetry.send_velocity_ned(vx=1.0, vy=0.0, vz=0.1)

# Body frame (Forward-Right-Down)
telemetry.send_velocity_body(vx=2.0, vy=0.0, vz=0.0)

# With yaw rate
telemetry.send_velocity_ned(vx=1.0, vy=0.0, vz=0.1, yaw_rate=0.1)
```

### Send Position Commands
```python
# NED frame
telemetry.send_position_target(x=100, y=50, z=-20, yaw=0.0)
```

## Visual Odometry Publishing

```python
# Prepare data
position = np.array([10.5, 20.3, -5.2])      # [x, y, z] in NED (meters)
orientation = np.array([0.95, 0.1, 0.05, 0.01])  # [w, x, y, z] quaternion
velocity = np.array([1.0, 0.5, 0.1])         # [vx, vy, vz] in m/s
covariance = np.eye(6) * 0.05                 # 6x6 covariance matrix

# Publish
success = telemetry.publish_visual_odometry(
    position=position,
    orientation=orientation,  # ← Automatically converted to Euler!
    velocity=velocity,
    covariance=covariance
)
```

## Telemetry Data Access

```python
telem = telemetry.read_telemetry()

# Attitude
roll_deg = telem['attitude']['roll']
pitch_deg = telem['attitude']['pitch']
yaw_deg = telem['attitude']['yaw']
heading_deg = telem['attitude']['heading']  # 0-360

# Position
lat = telem['position']['latitude']
lon = telem['position']['longitude']
alt = telem['position']['altitude']
rel_alt = telem['position']['relative_altitude']

# Velocity
ground_speed = telem['velocity']['ground_speed']
vertical_speed = telem['velocity']['vertical_speed']  # positive = up
airspeed = telem['velocity']['airspeed']

# GPS
fix_type = telem['gps']['fix_type']  # 0=no fix, 1=GPS, 2=DGPS, 3=RTK-fixed
satellites = telem['gps']['satellites']
eph = telem['gps']['eph']  # Horizontal error (meters)
epv = telem['gps']['epv']  # Vertical error (meters)

# Battery
voltage = telem['battery']['voltage']  # volts
current = telem['battery']['current']  # amperes
remaining = telem['battery']['remaining']  # percentage (0-100)

# System
system_id = telem['system_id']
component_id = telem['component_id']
```

## Constants

```python
from drone_autonomy.mavlink.telemetry import (
    BATTERY_NO_VOLTAGE,        # 65535 (sentinel)
    BATTERY_NO_CURRENT,        # -1 (sentinel)
    BATTERY_NO_REMAINING,      # -1 (sentinel)
    RAD_TO_DEG,                # 57.29577951308232
    DEG_TO_RAD,                # 0.017453292519943
    MAV_MODE_FLAG_SAFETY_ARMED # 128 (0x80)
)
```

## Common Patterns

### Wait for Vehicle to Arm
```python
telemetry.arm()
while not telemetry.armed:
    time.sleep(0.1)
    telemetry.read_telemetry()
print("Vehicle armed!")
```

### Wait for Mode Change
```python
telemetry.set_mode("GUIDED")
while telemetry.flight_mode != "GUIDED":
    time.sleep(0.1)
    telemetry.read_telemetry()
print("In GUIDED mode!")
```

### Main Loop Pattern
```python
telemetry.connect()

while True:
    # Read all available telemetry
    telem = telemetry.read_telemetry()
    
    # Process state changes
    if telem.get('armed_changed'):
        print(f"Arm state: {telem['armed']}")
        telemetry.clear_armed_changed()
    
    if telem.get('flight_mode_changed'):
        print(f"Mode: {telem['flight_mode']}")
        telemetry.clear_flight_mode_changed()
    
    # Use telemetry data
    print(f"Altitude: {telem['position']['altitude']:.1f}m")
    print(f"Battery: {telem['battery']['remaining']:.0f}%")
    
    time.sleep(0.05)  # 20 Hz update rate
```

