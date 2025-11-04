# MAVLink Connection Testing Suite

## Overview

This testing suite provides tools to verify MAVLink communication between your code and ArduPilot SITL, specifically testing:
- ✅ Connection establishment
- ✅ Arm/Disarm state detection
- ✅ Flight mode changes
- ✅ Command execution
- ✅ Telemetry data flow

## Test Scripts

### 1. `diagnose_mavlink.py` - Quick Diagnostic Tool

**Purpose**: Quickly check if ArduPilot SITL is reachable and responding.

**Usage**:
```powershell
# Test default connection
.\venv\Scripts\python.exe diagnose_mavlink.py

# Test specific connection
.\venv\Scripts\python.exe diagnose_mavlink.py tcp:127.0.0.1:5762

# Scan multiple common ports
.\venv\Scripts\python.exe diagnose_mavlink.py --scan
```

**When to use**: Run this FIRST to check if SITL is running and reachable.

---

### 2. `test_mavlink_connection.py` - Standalone Connection Test

**Purpose**: Comprehensive test using raw pymavlink (no project dependencies).

**Features**:
- Connection verification with heartbeat
- Automated test sequence (mode changes, arm/disarm)
- Real-time state change detection
- Message statistics
- Works independently of your codebase

**Usage**:
```powershell
# Basic test (30 second automated sequence)
.\venv\Scripts\python.exe test_mavlink_connection.py

# Test with different connection
.\venv\Scripts\python.exe test_mavlink_connection.py tcp:127.0.0.1:5762
```

**Output Example**:
```
======================================================================
MAVLink Connection Test
======================================================================
Connection string: udp:127.0.0.1:14550
...
✓ Heartbeat received!

Connection Details:
  - System ID:     1
  - Component ID:  1
  - Armed:        DISARMED
  - Flight Mode:  STABILIZE

[  5.23s] 🔔 MODE CHANGED: STABILIZE → GUIDED
[  8.12s] 🔔 ARMED STATE CHANGED: ARMED
[ 15.89s] 🔔 ARMED STATE CHANGED: DISARMED

✅ TEST PASSED: Connection is healthy
```

---

### 3. `test_telemetry_integration.py` - Integration Test

**Purpose**: Test your actual `MAVLinkTelemetry` class from the codebase.

**Features**:
- Uses your `src/drone_autonomy/mavlink/telemetry.py` class
- Tests the exact same interface used by your GUI
- Validates state change detection properties
- Tests command logging callback feature

**Usage**:
```powershell
# Basic integration test (30 seconds)
.\venv\Scripts\python.exe test_telemetry_integration.py

# Custom duration
.\venv\Scripts\python.exe test_telemetry_integration.py --duration 60

# Also test command logging
.\venv\Scripts\python.exe test_telemetry_integration.py --test-commands
```

**What it tests**:
- `telemetry.connect()` - Connection establishment
- `telemetry.read_telemetry()` - Telemetry reading
- `telemetry.armed` - Armed state property
- `telemetry.flight_mode` - Flight mode property
- `telemetry.armed_changed` - State change detection
- `telemetry.flight_mode_changed` - Mode change detection
- `telemetry.set_command_logger()` - Command logging callback

---

## Complete Test Workflow

### Step 1: Start ArduPilot SITL

**In WSL**:
```bash
cd ~/ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter -f gazebo-iris --console --map
```

**Expected output**:
```
Awaiting connections via udp:127.0.0.1:14550
```

### Step 2: Run Diagnostic

```powershell
.\venv\Scripts\python.exe diagnose_mavlink.py
```

**Expected result**:
```
✅ HEARTBEAT RECEIVED!
✅ CONNECTION IS WORKING!
```

If this fails, SITL is not running or not reachable.

### Step 3: Run Standalone Test

```powershell
.\venv\Scripts\python.exe test_mavlink_connection.py
```

This will:
1. Connect to SITL
2. Run automated test sequence
3. Report state changes and statistics

### Step 4: Run Integration Test

```powershell
.\venv\Scripts\python.exe test_telemetry_integration.py
```

This validates your actual telemetry class works correctly.

---

## Manual Testing with MAVProxy

You can also test manually while the tests are running:

### Start MAVProxy
```bash
mavproxy.py --master=udp:127.0.0.1:14550 --console
```

### MAVProxy Commands
```
mode GUIDED         # Change to GUIDED mode
mode LOITER         # Change to LOITER mode
mode STABILIZE      # Change to STABILIZE mode
arm throttle        # Arm the vehicle
disarm              # Disarm the vehicle
```

The test scripts will detect and report these changes in real-time.

---

## Troubleshooting

### Problem: "No heartbeat received"

**Solution**:
1. Check if SITL is running: `ps aux | grep sim_vehicle`
2. Check SITL output for connection string
3. Try diagnostic scan: `diagnose_mavlink.py --scan`

### Problem: "Connection refused"

**Solution**:
1. Check if port is correct (default: 14550)
2. Check firewall settings
3. If using WSL, check port forwarding:
   ```powershell
   netsh interface portproxy show all
   ```

### Problem: "Module not found" errors

**Solution**:
```powershell
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Problem: State changes not detected

**Solution**:
1. Ensure data streams are requested (automatic in tests)
2. Check SITL is sending messages (look for HEARTBEAT in output)
3. Try increasing test duration

---

## Understanding Test Output

### Armed State Changes
```
[  8.12s] 🔔 ARMED STATE CHANGED: ARMED
```
This confirms the telemetry class correctly detected arming.

### Flight Mode Changes
```
[  5.23s] 🔔 MODE CHANGED: STABILIZE → GUIDED
```
This confirms mode changes are detected correctly.

### Command Acknowledgments
```
[  7.45s] 📋 Command ACK: 400 - SUCCESS
```
This confirms commands are executed successfully.

### Message Statistics
```
Message Type Statistics:
  HEARTBEAT                :   30
  GLOBAL_POSITION_INT      :   28
  ATTITUDE                 :   28
```
This shows telemetry is flowing correctly.

---

## Integration with Your Codebase

These tests validate the MAVLink interface used by:

### `src/drone_autonomy/mavlink/telemetry.py`
The main telemetry class providing:
- `connect()` - Connection management
- `read_telemetry()` - Telemetry reading
- `armed` / `armed_changed` - Armed state tracking
- `flight_mode` / `flight_mode_changed` - Mode tracking
- `arm()` / `disarm()` - Control commands

### `src/drone_autonomy/gui/main_window.py`
The GUI uses telemetry for:
- Real-time status display
- Armed state indicator
- Flight mode display
- Telemetry data visualization

### `src/drone_autonomy/controller/mavlink_controller.py`
The controller uses telemetry for:
- Flight control
- Mode management
- Safety checks

---

## Test Success Criteria

### ✅ Pass Criteria
- Heartbeat received within timeout
- Armed state changes detected correctly
- Flight mode changes detected correctly
- Commands acknowledged
- Telemetry data flowing

### ❌ Fail Criteria
- No heartbeat received
- State changes not detected
- Commands timeout
- No telemetry data

---

## Advanced Usage

### Testing Different ArduPilot Versions
```powershell
# ArduPilot Copter
sim_vehicle.py -v ArduCopter

# ArduPilot Plane
sim_vehicle.py -v ArduPlane

# ArduPilot Rover
sim_vehicle.py -v Rover
```

### Testing with Real Hardware
```powershell
# Serial connection (find COM port in Device Manager)
.\venv\Scripts\python.exe test_mavlink_connection.py COM3:57600

# USB connection (auto-detected)
.\venv\Scripts\python.exe test_mavlink_connection.py /dev/ttyUSB0:115200
```

### Testing with Multiple GCS Connections
ArduPilot SITL supports multiple simultaneous connections:
```bash
# SITL on 14550
sim_vehicle.py -v ArduCopter --out=udp:127.0.0.1:14551

# Test script on 14550
.\venv\Scripts\python.exe test_mavlink_connection.py udp:127.0.0.1:14550

# MAVProxy on 14551
mavproxy.py --master=udp:127.0.0.1:14551
```

---

## Files Created

- `test_mavlink_connection.py` - Standalone connection test
- `test_telemetry_integration.py` - Integration test with your telemetry class
- `diagnose_mavlink.py` - Quick diagnostic tool
- `TEST_MAVLINK_GUIDE.md` - Detailed guide for test_mavlink_connection.py
- `README_MAVLINK_TESTS.md` - This file

---

## Next Steps

After successful tests:

1. ✅ **Integrate into CI/CD**: Add tests to automated testing
2. ✅ **Monitor in production**: Use diagnostic tool for health checks
3. ✅ **Extend tests**: Add tests for specific mission scenarios
4. ✅ **Test with hardware**: Validate with real drone hardware
5. ✅ **Add logging**: Integrate with your logging system

---

## Support

For issues or questions:
1. Check SITL is running: `diagnose_mavlink.py`
2. Review test output for specific errors
3. Check `TEST_MAVLINK_GUIDE.md` for detailed troubleshooting
4. Verify ArduPilot version compatibility

---

## Summary

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `diagnose_mavlink.py` | Quick check | First, to verify SITL is running |
| `test_mavlink_connection.py` | Standalone test | Verify MAVLink protocol works |
| `test_telemetry_integration.py` | Integration test | Verify your code works with SITL |

**Recommended order**: Diagnostic → Standalone → Integration
