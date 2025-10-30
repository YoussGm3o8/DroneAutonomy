#!/usr/bin/env python3
"""
Test script for AirSim + ArduPilot SITL integration.
This tests the full stack: Real flight controller + AirSim physics + Vision pipeline.

Prerequisites:
1. AirSim running (Unreal Engine)
2. ArduPilot SITL running with --model airsim-copter --out=udp:localhost:14550
3. MAVLink available on UDP 14550

Usage:
    python examples/test_airsim_sitl.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from drone_autonomy.pipeline import DronePipeline
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Test AirSim + SITL pipeline."""
    
    print("=" * 80)
    print("AirSim + ArduPilot SITL Integration Test")
    print("=" * 80)
    print()
    print("This will test:")
    print("  ✓ AirSim camera feed")
    print("  ✓ ArduPilot SITL MAVLink connection (UDP 14550)")
    print("  ✓ Vision pipeline (YOLO + Depth + Targets)")
    print("  ✓ Real flight controller telemetry")
    print()
    print("Prerequisites:")
    print("  1. AirSim running (Unreal Engine)")
    print("  2. ArduPilot SITL: arducopter --model airsim-copter --out=udp:localhost:14550")
    print("  3. Optionally: Mission Planner or QGC on UDP 14550")
    print()
    print("=" * 80)
    print()
    
    input("Press Enter to start (Ctrl+C to cancel)...")
    print()
    
    # Get config path
    config_path = Path(__file__).parent.parent / 'config' / 'airsim_sitl.yaml'
    
    # Create pipeline
    print(f"Loading config: {config_path}")
    pipeline = DronePipeline(str(config_path))
    
    # Initialize
    print("Initializing pipeline...")
    if not pipeline.initialize():
        print("ERROR: Failed to initialize pipeline")
        print()
        print("Troubleshooting:")
        print("  1. Check if AirSim is running")
        print("  2. Check if ArduPilot SITL is running: ps aux | grep arducopter")
        print("  3. Check MAVLink: netstat -an | grep 14550")
        print("  4. Check logs in logs/ directory")
        return 1
    
    print()
    print("=" * 80)
    print("Pipeline initialized successfully!")
    print("=" * 80)
    print()
    print("Starting vision processing...")
    print("  - Press 'q' in video window to quit")
    print("  - Press 's' to save a frame")
    print("  - Check console for MAVLink telemetry")
    print()
    
    # Run pipeline
    try:
        pipeline.run(
            display=True,
            max_frames=None,  # Run indefinitely
            process_interval=2,  # Every 2nd frame for 18 FPS
            fast_mode=False  # Keep depth enabled
        )
    except KeyboardInterrupt:
        print("\nStopped by user (Ctrl+C)")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print()
    print("=" * 80)
    print("Test completed successfully!")
    print("=" * 80)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
