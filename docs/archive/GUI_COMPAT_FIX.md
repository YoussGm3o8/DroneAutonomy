# GUI Compatibility Fix - MAVLinkTelemetry Command Logger

**Date**: November 3, 2025  
**Issue**: AttributeError - MAVLinkTelemetry missing set_command_logger method  
**Status**: ✅ FIXED

## Problem

When the GUI connects to MAVLink telemetry, it tries to register a command logger callback:

```python
self.mavlink.set_command_logger(self._log_mavlink_action)
```

This method didn't exist in the refactored MAVLinkTelemetry class, causing:
```
AttributeError: 'MAVLinkTelemetry' object has no attribute 'set_command_logger'
```

## Solution

Added command logging support to MAVLinkTelemetry class:

### 1. Added Command Logger Attribute

In `__init__`:
```python
# Command logging callback (for GUI/external logging)
self._command_logger = None  # Optional callback: Callable[[str, str], None]
```

### 2. Added set_command_logger Method

```python
def set_command_logger(self, callback):
    """
    Set a callback function for logging MAVLink commands.
    
    The callback will be invoked whenever a command is sent to the vehicle.
    Useful for GUI components that want to display command activity in logs.
    
    Args:
        callback: Function with signature callback(message: str, level: str = "INFO")
                 Set to None to disable logging.
    """
    self._command_logger = callback
```

### 3. Added Internal Logging Method

```python
def _log_command(self, message: str, level: str = "INFO"):
    """Log a command action through the registered callback."""
    if self._command_logger is not None:
        try:
            self._command_logger(message, level)
        except Exception as e:
            self.logger.warning(f"Error in command logger callback: {e}")
```

### 4. Updated Command Methods

Updated `arm()`, `disarm()`, and `set_mode()` to log commands:

```python
# In arm():
self._log_command("ARM command sent to vehicle", "SUCCESS")

# In disarm():
self._log_command("DISARM command sent to vehicle", "WARNING")

# In set_mode():
self._log_command(f"Flight mode changed to {mode}", "INFO")
```

## Usage

GUI can now register a logger callback:

```python
def _log_mavlink_action(self, message: str, level: str = "INFO"):
    """Display MAVLink command activity in the GUI logs."""
    if self.results_viewer:
        self.results_viewer.add_log(f"[MAVLINK] {message}", level)

# Register the callback
self.mavlink.set_command_logger(self._log_mavlink_action)

# Now arm/disarm/mode commands will be logged
telemetry.arm()  # → Logs "ARM command sent to vehicle" to GUI
telemetry.set_mode("GUIDED")  # → Logs "Flight mode changed to GUIDED" to GUI
```

## Features

- ✅ Backward compatible - callback is optional (None by default)
- ✅ Safe - catches exceptions in callback
- ✅ Flexible - callback can be any function with correct signature
- ✅ Informative - includes log level (SUCCESS, WARNING, INFO)
- ✅ Integrated - automatically called from command methods

## Files Modified

- `src/drone_autonomy/mavlink/telemetry.py`
  - Added `_command_logger` attribute
  - Added `set_command_logger(callback)` method
  - Added `_log_command(message, level)` method
  - Updated `arm()` to log commands
  - Updated `disarm()` to log commands
  - Updated `set_mode()` to log commands

## Validation

✅ No syntax errors  
✅ No import errors  
✅ Backward compatible with existing code  
✅ GUI can now register and receive command logs  

