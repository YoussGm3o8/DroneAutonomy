"""
Debug HEARTBEAT Messages

This script shows exactly what HEARTBEAT messages are being received,
including their system IDs, to diagnose the filtering issue.
"""

import sys
import time
from pymavlink import mavutil

print("=" * 70)
print("HEARTBEAT Message Debug Tool")
print("=" * 70)
print()
print("This will show ALL HEARTBEAT messages with their source system IDs")
print()

# Connect
print("Connecting to udp:127.0.0.1:14550...")
conn = mavutil.mavlink_connection('udp:127.0.0.1:14550', timeout=10)

print("Waiting for initial heartbeat...")
msg = conn.wait_heartbeat(timeout=10)

if not msg:
    print("❌ No heartbeat received")
    sys.exit(1)

print(f"✓ Heartbeat received")
print(f"Target system: {conn.target_system}")
print(f"Target component: {conn.target_component}")
print()
print("Monitoring ALL HEARTBEAT messages for 20 seconds...")
print("=" * 70)
print()

# ArduPilot modes
copter_modes = {
    0: "STABILIZE", 1: "ACRO", 2: "ALT_HOLD", 3: "AUTO",
    4: "GUIDED", 5: "LOITER", 6: "RTL", 7: "CIRCLE",
    9: "LAND"
}

start_time = time.time()
heartbeat_count = {}

try:
    while time.time() - start_time < 20:
        msg = conn.recv_match(type='HEARTBEAT', blocking=True, timeout=0.5)
        
        if msg:
            # Try to get system ID using pymavlink methods
            sysid = None
            compid = None
            
            try:
                sysid = msg.get_srcSystem()
                compid = msg.get_srcComponent()
            except (AttributeError, TypeError):
                # Fallback: try direct attributes
                if hasattr(msg, '_sysid'):
                    sysid = msg._sysid
                    compid = msg._compid
                elif hasattr(msg, '_header'):
                    header = msg._header
                    if hasattr(header, 'srcSystem'):
                        sysid = header.srcSystem
                        compid = header.srcComponent
            
            # Get mode
            mode_id = msg.custom_mode
            mode_name = copter_modes.get(mode_id, f"CUSTOM({mode_id})")
            armed = bool(msg.base_mode & 128)
            
            # Count by system
            key = f"sys{sysid}_comp{compid}" if sysid is not None else "unknown"
            heartbeat_count[key] = heartbeat_count.get(key, 0) + 1
            
            # Display
            elapsed = time.time() - start_time
            armed_str = "ARMED" if armed else "DISARMED"
            
            print(f"[{elapsed:5.1f}s] HEARTBEAT:")
            print(f"         System ID:   {sysid}")
            print(f"         Component:   {compid}")
            print(f"         Mode:        {mode_name}")
            print(f"         Armed:       {armed_str}")
            print(f"         Type:        {msg.type}")
            print(f"         Autopilot:   {msg.autopilot}")
            print(f"         Target sys:  {conn.target_system}")
            print(f"         Match:       {'✓ YES' if sysid == conn.target_system else '✗ NO (WOULD IGNORE)'}")
            print()

except KeyboardInterrupt:
    print("\nInterrupted by user")

print()
print("=" * 70)
print("Summary")
print("=" * 70)
print()
print("HEARTBEAT counts by system:")
for key, count in sorted(heartbeat_count.items()):
    print(f"  {key}: {count} heartbeats")
print()
print(f"Target system: {conn.target_system}")
print()

if len(heartbeat_count) > 1:
    print("⚠️  WARNING: Multiple systems detected!")
    print("   This can cause mode oscillation if not properly filtered")
else:
    print("✓ Only one system detected")

conn.close()
