# CRITICAL FIX: Mode Oscillation Issue

## Problem Identified

### Symptoms
- Mode rapidly oscillates between GUIDED and STABILIZE every ~1 second
- Mission Planner shows mode as solidly GUIDED
- Telemetry reports constant mode changes:
  ```
  Flight mode changed: GUIDED → STABILIZE
  Flight mode changed: STABILIZE → GUIDED
  (repeats every second)
  ```

### Root Cause
The telemetry code was receiving and processing HEARTBEAT messages from **ALL** systems on the MAVLink network, including:
1. **Autopilot (System ID 1)** - sends mode=GUIDED
2. **Mission Planner (System ID 255)** - sends mode=STABILIZE (its own state)
3. **Other GCS or companion computers** - may send different modes

The code was not filtering these HEARTBEATs by system ID, causing it to toggle between the autopilot's mode and Mission Planner's mode.

### Location
File: `src/drone_autonomy/mavlink/telemetry.py`
Line: ~508 (HEARTBEAT processing in `read_telemetry()`)

---

## Solution Applied

### Fix
Added system ID filtering to only process HEARTBEAT messages from the target vehicle (autopilot):

```python
elif msg_type == 'HEARTBEAT':
    # CRITICAL FIX: Only process HEARTBEAT from the target vehicle
    # Ground stations (Mission Planner, MAVProxy, etc.) also send HEARTBEATs
    # which can cause mode oscillation if not filtered out
    if hasattr(msg, '_sysid') and hasattr(msg, '_compid'):
        # Check if this HEARTBEAT is from our target vehicle
        if msg._sysid != self.connection.target_system:
            # Ignore HEARTBEATs from other systems (GCS, companion computers, etc.)
            self.logger.debug(f"Ignoring HEARTBEAT from system {msg._sysid}")
            continue
    
    # ... rest of HEARTBEAT processing ...
```

### How It Works
1. Check if the message has system ID (`_sysid`) and component ID (`_compid`)
2. Compare message's system ID with `connection.target_system` (usually 1 for autopilot)
3. If they don't match, skip (continue) processing this HEARTBEAT
4. Only process HEARTBEATs from the actual vehicle

---

## Verification

### Test Script
Created: `test_heartbeat_filter.py`

**Run**:
```powershell
.\venv\Scripts\python.exe test_heartbeat_filter.py
```

**What it does**:
- Monitors for 30 seconds
- Counts mode changes
- Detects rapid oscillation (> 3 changes in < 2 seconds each)
- Reports PASS/FAIL

**Expected Result After Fix**:
```
✅ PASS: Mode changes appear normal
```

No rapid oscillation between modes.

---

## Before vs After

### Before Fix
```
[  6.87s] 🔔 FLIGHT MODE CHANGED: STABILIZE
[  6.97s] 🔔 FLIGHT MODE CHANGED: GUIDED
[  7.88s] 🔔 FLIGHT MODE CHANGED: STABILIZE
[  7.98s] 🔔 FLIGHT MODE CHANGED: GUIDED
[  8.89s] 🔔 FLIGHT MODE CHANGED: STABILIZE
[  8.99s] 🔔 FLIGHT MODE CHANGED: GUIDED
... (oscillates continuously)
```

Mode changes every ~0.1 seconds - unusable!

### After Fix
```
[  2.34s] 🔔 FLIGHT MODE CHANGED: GUIDED
[  5.00s] Status: DISARMED | Mode: GUIDED
[ 10.00s] Status: DISARMED | Mode: GUIDED
[ 15.00s] Status: DISARMED | Mode: GUIDED
... (stays stable)
```

Mode changes only when actually commanded - correct behavior!

---

## Technical Details

### MAVLink System IDs
- **1**: Primary autopilot (ArduPilot, PX4)
- **255**: Ground Control Station (Mission Planner, QGC)
- **191-200**: Companion computers
- **2-127**: Other autopilots/components

### Why GCS Sends HEARTBEAT
Ground stations send HEARTBEAT to:
1. Announce their presence
2. Allow autopilot to know GCS is alive
3. Indicate GCS state (not the vehicle state!)

**Key Point**: GCS HEARTBEAT reflects GCS internal state, NOT vehicle state.

### pymavlink Filtering
The `recv_match()` function can filter by:
- `type`: Message type (e.g., 'HEARTBEAT')
- `blocking`: Wait for message or return immediately
- `timeout`: Max wait time

However, it **cannot** filter by system ID in the call itself. We must check `msg._sysid` manually after receiving.

---

## Impact on System

### Components Affected
1. ✅ `src/drone_autonomy/mavlink/telemetry.py` - Fixed
2. ✅ GUI mode display - Now stable
3. ✅ Autonomous flight logic - Won't get confused by oscillating modes
4. ✅ Mode change detection - Works correctly

### Performance Impact
- **Minimal**: Added one integer comparison per HEARTBEAT message
- **HEARTBEATs**: Typically 1-4 Hz, so < 10 comparisons/second
- **Benefit**: Eliminates spurious mode change events

---

## Testing Checklist

### ✅ Immediate Tests
```powershell
# 1. Syntax validation
.\venv\Scripts\python.exe -m py_compile src/drone_autonomy/mavlink/telemetry.py

# 2. Run filter test
.\venv\Scripts\python.exe test_heartbeat_filter.py

# 3. Run integration test
.\venv\Scripts\python.exe test_telemetry_integration.py --duration 30
```

### ✅ Manual Verification
1. Start SITL and Mission Planner
2. Set mode to GUIDED in Mission Planner
3. Run test script
4. **Verify**: Mode stays GUIDED, no oscillation
5. Change mode to LOITER
6. **Verify**: Single clean transition, no oscillation

---

## Additional Improvements (Optional)

### Option 1: Filter by Component ID
If needed, also filter by component ID (usually 1 for autopilot):

```python
if msg._sysid != self.connection.target_system:
    continue
if msg._compid != self.connection.target_component:
    continue  # Optional: stricter filtering
```

### Option 2: Debug Logging
Enable DEBUG logging to see ignored HEARTBEATs:

```python
# In config
logging.basicConfig(level=logging.DEBUG)
```

Output will show:
```
Ignoring HEARTBEAT from system 255 (target is 1)
```

### Option 3: Statistics
Track ignored HEARTBEATs for diagnostics:

```python
self.ignored_heartbeats = 0

# In HEARTBEAT handling
if msg._sysid != self.connection.target_system:
    self.ignored_heartbeats += 1
    continue
```

---

## Related Issues

### If Oscillation Persists
1. Check `connection.target_system` is correct (should be 1)
2. Verify autopilot system ID (check SITL output)
3. Enable DEBUG logging to see which HEARTBEATs are being processed
4. Check for multiple autopilots on same network

### Multiple Vehicles
If controlling multiple vehicles:
- Each needs separate `MAVLinkTelemetry` instance
- Each instance filters to its own `target_system`
- Use different connection strings or system IDs

---

## Summary

✅ **Problem**: Mode oscillation due to processing HEARTBEATs from all systems  
✅ **Solution**: Filter to only process target vehicle's HEARTBEATs  
✅ **Files Modified**: `src/drone_autonomy/mavlink/telemetry.py`  
✅ **Test Created**: `test_heartbeat_filter.py`  
✅ **Result**: Stable mode detection, no false mode changes  

**The fix is minimal, targeted, and solves the root cause of the oscillation issue.**
