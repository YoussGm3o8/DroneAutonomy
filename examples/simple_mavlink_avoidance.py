#!/usr/bin/env python3
"""
Simple MAVLink Object Avoidance Example

A minimal example demonstrating MAVLink-based obstacle avoidance.
Perfect for learning and quick testing.

Usage:
    python examples/simple_mavlink_avoidance.py
"""

import sys
import cv2
import numpy as np
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.drone_autonomy.mavlink.telemetry import MAVLinkTelemetry
from src.drone_autonomy.navigation.obstacle_avoidance import ObstacleAvoider
from src.drone_autonomy.navigation.mavlink_avoidance_controller import (
    MAVLinkAvoidanceController
)


def main():
    """Simple avoidance example"""
    print("=" * 60)
    print("Simple MAVLink Object Avoidance Example")
    print("=" * 60)

    # 1. Configure components
    mavlink_config = {
        'connection_string': 'udp:127.0.0.1:14550',
        'heartbeat_timeout': 5
    }

    avoidance_config = {
        'obstacle_distance_threshold': 5.0,
        'critical_distance': 2.0,
        'num_zones_horizontal': 5,
        'num_zones_vertical': 3,
        'show_obstacles': True,
        'show_paths': True
    }

    controller_config = {
        'max_velocity': 2.0,
        'avoidance_velocity': 1.0,
        'emergency_distance': 1.5,
        'update_rate': 10
    }

    # 2. Connect to MAVLink
    print("\n[1/3] Connecting to MAVLink...")
    mavlink = MAVLinkTelemetry(mavlink_config)

    if not mavlink.connect():
        print("✗ Failed to connect to MAVLink")
        print("Make sure ArduPilot SITL is running:")
        print("  cd ~/ardupilot/ArduCopter")
        print("  ../Tools/autotest/sim_vehicle.py --console --map")
        return 1

    print("✓ MAVLink connected")

    # 3. Setup obstacle avoider
    print("\n[2/3] Initializing obstacle avoider...")
    avoider = ObstacleAvoider(avoidance_config)
    print("✓ Avoider ready")

    # 4. Setup controller
    print("\n[3/3] Creating avoidance controller...")
    controller = MAVLinkAvoidanceController(
        mavlink=mavlink,
        avoider=avoider,
        config=controller_config
    )
    print("✓ Controller ready")

    # 5. Demonstrate MAVLink commands
    print("\n" + "=" * 60)
    print("Testing MAVLink Commands")
    print("=" * 60)

    # Read telemetry
    telemetry = mavlink.read_telemetry()
    print(f"\nFlight mode: {telemetry.get('flight_mode', 'UNKNOWN')}")
    print(f"Armed: {telemetry.get('armed', False)}")

    # Switch to GUIDED mode
    print("\nSwitching to GUIDED mode...")
    if mavlink.set_mode("GUIDED"):
        print("✓ Mode change sent")
    else:
        print("✗ Mode change failed")

    # Test velocity command
    print("\nTesting velocity command (forward 0.5 m/s for 2 seconds)...")
    import time
    mavlink.send_velocity_body(0.5, 0, 0, 0)
    time.sleep(2)
    mavlink.send_velocity_body(0, 0, 0, 0)  # Stop
    print("✓ Velocity command sent")

    # 6. Demonstrate obstacle avoidance with synthetic data
    print("\n" + "=" * 60)
    print("Simulating Obstacle Detection")
    print("=" * 60)

    # Create synthetic depth map with obstacle
    depth_map = np.ones((480, 640), dtype=np.float32) * 10.0  # 10m depth
    # Add obstacle in center (close distance)
    depth_map[200:280, 280:360] = 1.5  # 1.5m obstacle

    # Detect obstacles
    obstacles = avoider.detect_obstacles(depth_map)
    print(f"\nDetected {len(obstacles)} obstacle(s)")

    for i, obs in enumerate(obstacles):
        print(f"  Obstacle {i+1}: distance={obs.distance:.2f}m, risk={obs.risk.name}")

    # Generate paths
    frame_shape = (480, 640)
    paths = avoider.generate_path_candidates(frame_shape)
    print(f"\nGenerated {len(paths)} avoidance paths")
    print(f"Selected path: safe={avoider.selected_path.is_safe}, "
          f"clearance={avoider.selected_path.clearance:.2f}m")

    # Get avoidance command
    cmd = avoider.get_avoidance_command()
    print(f"\nAvoidance command: {cmd}")

    # 7. Visualize (synthetic frame)
    print("\n" + "=" * 60)
    print("Visualization")
    print("=" * 60)
    print("\nGenerating visualization...")

    # Create synthetic frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:, :] = (50, 50, 50)  # Gray background

    # Visualize avoidance
    viz = controller.get_visualization_frame(frame, depth_map)

    # Display
    cv2.imshow('MAVLink Avoidance - Synthetic Test', viz)
    print("Press any key in the window to continue...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # 8. Cleanup
    print("\n" + "=" * 60)
    print("Cleanup")
    print("=" * 60)

    controller.stop()
    mavlink.disconnect()
    print("✓ Disconnected")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("\nNext steps:")
    print("  - Try with real camera: examples/test_mavlink_avoidance.py")
    print("  - Read docs: docs/MAVLINK_OBJECT_AVOIDANCE.md")
    print("  - Customize config: config/mavlink_avoidance.yaml")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
