#!/usr/bin/env python3
"""Quick test of GazeboManager fixes"""

from drone_autonomy.utils.gazebo_manager import GazeboManager

print("=" * 60)
print("Testing GazeboManager Fixes")
print("=" * 60)

# Test 1: Default world path
print("\n[Test 1] Default world path")
manager = GazeboManager()
print(f"  World path: {manager.world_path}")
print(f"  Expected: iris_runway_camera.sdf")
print(f"  ✓ PASS" if manager.world_path == "iris_runway_camera.sdf" else f"  ✗ FAIL")

# Test 2: Windows IP detection
print("\n[Test 2] Windows IP detection")
print(f"  Detected IP: {manager.windows_ip}")
print(f"  Expected format: xxx.xxx.xxx.xxx")
if '.' in manager.windows_ip and manager.windows_ip.count('.') == 3:
    try:
        octets = [int(x) for x in manager.windows_ip.split('.')]
        if all(0 <= o <= 255 for o in octets):
            print(f"  ✓ PASS - Valid IP format")
        else:
            print(f"  ✗ FAIL - Invalid IP octets")
    except:
        print(f"  ✗ FAIL - Not a valid IP")
else:
    print(f"  ✗ FAIL - Wrong format")

# Test 3: UDP port
print("\n[Test 3] UDP port")
print(f"  UDP port: {manager.udp_port}")
print(f"  Expected: 5600")
print(f"  ✓ PASS" if manager.udp_port == 5600 else f"  ✗ FAIL")

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)
print("\nNext: Test GUI launch with updated settings:")
print("  python launch_gui.py")
print("  Click '🎮 Gazebo Simulation'")
print("  Should launch: gz sim -v4 -r iris_runway_camera.sdf")
