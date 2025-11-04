# Telemetry Flash Fix - Armed State & Flight Mode

## Issue Description
When connected via MAVLink, the GUI telemetry display was experiencing flickering/flashing between current and startup values for:
- Arming state (ARMED/DISARMED)
- Flight mode (STABILIZE, GUIDED, etc.)

## Root Causes Identified

### 1. Change Flags Never Cleared (PRIMARY CAUSE)
**THE CRITICAL BUG:** In `src/drone_autonomy/mavlink/telemetry.py`, the change detection flags were being set but **NEVER CLEARED**:

```python
# When a change was detected:
self._armed_changed = True
self._flight_mode_changed = True

# These flags were returned in telemetry:
result['armed_changed'] = self._armed_changed
result['flight_mode_changed'] = self._flight_mode_changed

# BUT THEY WERE NEVER RESET TO False!
```

**Impact:** Every subsequent call to `read_telemetry()` or `get_flattened_telemetry()` would continue returning `armed_changed=True` and `flight_mode_changed=True`, even though no actual change occurred. This caused the GUI to continuously think the state was changing, leading to flickering displays.

### 2. Redundant State Assignments
In the HEARTBEAT message handler, state variables were being reassigned even when they hadn't changed:

```python
# OLD CODE (BUGGY)
if new_mode != self._flight_mode:
    # ... handle change ...
else:
    self._flight_mode = new_mode  # ← Redundant assignment

if new_armed != self._armed:
    # ... handle change ...
else:
    self._armed = new_armed  # ← Redundant assignment
```

### 3. Data Structure Mismatch
The telemetry system returned nested data structures but the GUI expected flat structures, preventing proper caching.

## Fixes Applied

### Fix 1: Auto-Clear Change Flags (CRITICAL FIX)
**File:** `src/drone_autonomy/mavlink/telemetry.py`

Added automatic flag clearing in `get_flattened_telemetry()`:

```python
# Clear the change flags after reading them (consumed by this call)
# This prevents the same change from being reported multiple times
if telemetry.get('armed_changed', False):
    self.clear_armed_changed()
if telemetry.get('flight_mode_changed', False):
    self.clear_flight_mode_changed()
```

**Why this works:** Once the GUI reads the change flags, they're immediately cleared. The next call will only show `armed_changed=True` or `flight_mode_changed=True` if a NEW change occurred since the last read.

### Fix 2: Remove Redundant Assignments
**File:** `src/drone_autonomy/mavlink/telemetry.py`

Removed the `else` clauses that were reassigning unchanged values:

```python
# NEW CODE (FIXED)
if new_mode != self._flight_mode:
    # ... handle change ...
# Don't update if no change - preserve current value

if new_armed != self._armed:
    # ... handle change ...
# Don't update if no change - preserve current value
```

### Fix 3: Add Flattened Telemetry Accessor
**File:** `src/drone_autonomy/mavlink/telemetry.py`

Added new method `get_flattened_telemetry()` that:
- Calls `read_telemetry()` internally
- Flattens nested structures into a single-level dictionary
- Returns data in the format expected by GUI components
- **Clears change flags after reading**

### Fix 4: Update GUI to Use Flattened Data
**File:** `src/drone_autonomy/gui/main_window.py`

Changed the MAVLink telemetry update method:

```python
# OLD
telemetry = self.mavlink.read_telemetry()

# NEW
telemetry = self.mavlink.get_flattened_telemetry()
```

### Fix 5: Add Debug Logging (Optional)
**Files:** 
- `src/drone_autonomy/gui/drone_control_panel.py`
- `src/drone_autonomy/gui/telemetry_display.py`

Added debug print statements to track when state actually changes in the GUI components. This helps identify if flickering persists.

## How The Fix Works

**Before (BROKEN):**
1. Drone mode changes: STABILIZE → GUIDED
2. `_flight_mode_changed` set to `True`
3. GUI reads telemetry: sees `flight_mode_changed=True`
4. GUI reads telemetry again: STILL sees `flight_mode_changed=True` ← **BUG!**
5. GUI reads telemetry again: STILL sees `flight_mode_changed=True` ← **FLASHING!**
6. This continues forever, causing constant UI updates

**After (FIXED):**
1. Drone mode changes: STABILIZE → GUIDED
2. `_flight_mode_changed` set to `True`
3. GUI reads telemetry: sees `flight_mode_changed=True`, flag is cleared
4. GUI reads telemetry again: sees `flight_mode_changed=False` ← **STABLE!**
5. No more UI updates until next actual change

## Benefits

1. **✅ Eliminates Flashing** - Change flags are only `True` once per actual change
2. **✅ Proper Caching** - GUI components can now correctly cache previous values
3. **✅ Cleaner Code** - No redundant assignments cluttering the logic
4. **✅ Better Compatibility** - Flattened data structure matches GUI expectations
5. **✅ Event-Driven Updates** - GUI only updates when state actually changes
6. **✅ No Breaking Changes** - `read_telemetry()` still works for other use cases

## Testing Recommendations

1. Connect to MAVLink (ArduPilot SITL or real drone)
2. Launch GUI: `python launch_gui.py`
3. Watch debug console for change notifications
4. Verify telemetry display shows stable values (no flickering)
5. Change flight modes - verify clean transitions with single update
6. Arm/disarm drone - verify no flickering in status display
7. Debug output should show state changes ONLY when they actually occur

## Debug Output Expected

```
[TelemetryDisplay] Mode changed: STABILIZE → GUIDED
[DroneControl] Flight mode changed: STABILIZE → GUIDED
(then silence until next actual change)
```

## Related Files Modified

- `src/drone_autonomy/mavlink/telemetry.py` - Core telemetry logic + flag clearing
- `src/drone_autonomy/gui/main_window.py` - GUI telemetry integration
- `src/drone_autonomy/gui/drone_control_panel.py` - Debug logging
- `src/drone_autonomy/gui/telemetry_display.py` - Debug logging

## Technical Notes

- The `clear_armed_changed()` and `clear_flight_mode_changed()` methods already existed in the codebase but were never being called
- The change flags are now automatically cleared after being read, implementing a "consume on read" pattern
- This is thread-safe as long as only one thread calls `get_flattened_telemetry()`
- The debug logging can be removed once the fix is confirmed working
