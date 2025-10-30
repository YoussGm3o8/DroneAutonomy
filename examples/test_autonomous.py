"""
Test Autonomous Navigation Mode

This script tests the autonomous navigation system with a real drone or simulation.

Usage:
    # With real drone (RTSP camera + MAVLink)
    python examples/test_autonomous.py
    
    # With AirSim simulation
    python examples/test_autonomous.py --sim
    
    # With custom config
    python examples/test_autonomous.py --config config/autonomous.yaml
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from drone_autonomy.pipeline import DronePipeline


def test_autonomous_real_drone():
    """Test autonomous mode with real drone"""
    print("=" * 80)
    print("Autonomous Navigation Test - Real Drone")
    print("=" * 80)
    print()
    print("Prerequisites:")
    print("  ✓ Drone powered on and connected")
    print("  ✓ RTSP camera streaming on rtsp://192.168.1.231:8554/1")
    print("  ✓ MAVLink connected on UDP 127.0.0.1:14550")
    print("  ✓ Red circular targets placed in view")
    print()
    print("Safety:")
    print("  ⚠️  Have manual RC control ready")
    print("  ⚠️  Monitor battery level")
    print("  ⚠️  Test in safe, controlled environment")
    print()
    input("Press Enter when ready to start, or Ctrl+C to abort...")
    print()
    
    # Create pipeline with default config
    pipeline = DronePipeline('config/default_config.yaml')
    
    if not pipeline.initialize():
        print("❌ Failed to initialize pipeline")
        return 1
    
    print("✓ Pipeline initialized")
    print("✓ Autonomous mode will be enabled")
    print()
    print("Controls:")
    print("  - Press 'q' to quit")
    print("  - Press Ctrl+C for emergency stop")
    print()
    print("Logs will be saved to: logs/autonomous/")
    print("Photos will be saved to: logs/autonomous/photos/")
    print()
    
    try:
        # Run with autonomous mode
        pipeline.run(
            display=True,
            process_interval=2,  # Balanced mode (18 FPS)
            fast_mode=False,  # Keep depth for obstacle avoidance
            autonomous=True  # Enable autonomous navigation
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Emergency stop requested")
    
    print()
    print("=" * 80)
    print("Autonomous Navigation Test Complete")
    print("=" * 80)
    print()
    print("Check logs at:")
    print(f"  - logs/autonomous/targets_*.csv")
    print(f"  - logs/autonomous/photos/target_*.jpg")
    print()
    
    return 0


def test_autonomous_simulation():
    """Test autonomous mode with AirSim simulation"""
    print("=" * 80)
    print("Autonomous Navigation Test - AirSim Simulation")
    print("=" * 80)
    print()
    print("Prerequisites:")
    print("  ✓ AirSim running (pure mode, no ArduPilot)")
    print("  ✓ Simulation environment loaded")
    print("  ✓ Red circular targets placed in scene")
    print()
    input("Press Enter when ready to start, or Ctrl+C to abort...")
    print()
    
    # Create pipeline with AirSim config
    pipeline = DronePipeline('config/airsim_simulation.yaml')
    
    if not pipeline.initialize():
        print("❌ Failed to initialize pipeline")
        return 1
    
    print("✓ Pipeline initialized")
    print("✓ AirSim connected")
    print("✓ Autonomous mode will be enabled")
    print()
    print("Controls:")
    print("  - Press 'q' to quit")
    print("  - Press Ctrl+C for emergency stop")
    print()
    
    try:
        # Run with autonomous mode
        pipeline.run(
            display=True,
            process_interval=3,  # High performance (10 FPS for AirSim)
            fast_mode=False,  # Keep depth for obstacle avoidance
            autonomous=True  # Enable autonomous navigation
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Emergency stop requested")
    
    print()
    print("=" * 80)
    print("Autonomous Navigation Test Complete")
    print("=" * 80)
    
    return 0


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test autonomous navigation')
    parser.add_argument('--sim', action='store_true', help='Use AirSim simulation')
    parser.add_argument('--config', type=str, help='Custom config file')
    
    args = parser.parse_args()
    
    if args.sim:
        return test_autonomous_simulation()
    else:
        return test_autonomous_real_drone()


if __name__ == '__main__':
    sys.exit(main())
