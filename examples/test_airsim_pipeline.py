"""
AirSim Simulation Mode Test Script

This script tests the DroneAutonomy pipeline in AirSim simulation mode.

Prerequisites:
1. Install AirSim: pip install airsim
2. Launch AirSim simulator (Unreal Engine)
3. Ensure AirSim is running on 127.0.0.1:41451

Usage:
    python examples/test_airsim_pipeline.py [--fast] [--interval N] [--max-frames N]
"""

import sys
import os
import argparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from drone_autonomy.pipeline import DronePipeline


def main():
    parser = argparse.ArgumentParser(description='Test DroneAutonomy Pipeline with AirSim')
    parser.add_argument('--fast', action='store_true', 
                       help='Fast mode: skip depth estimation')
    parser.add_argument('--interval', type=int, default=1,
                       help='Process every Nth frame (default: 1)')
    parser.add_argument('--max-frames', type=int, default=None,
                       help='Maximum number of frames to process')
    parser.add_argument('--no-display', action='store_true',
                       help='Disable display window')
    parser.add_argument('--auto-takeoff', action='store_true',
                       help='Automatically takeoff in simulation')
    
    args = parser.parse_args()
    
    # Get config path
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'airsim_simulation.yaml')
    
    print("=" * 80)
    print("DroneAutonomy AirSim Simulation Mode Test")
    print("=" * 80)
    print()
    
    # Interactive mode selection
    if not args.fast and args.interval == 1:
        print("Choose a performance mode:")
        print()
        print("  1. Full Quality Mode (3 FPS)")
        print("     - All features: Depth + Detection + Targets")
        print("     - Every frame processed")
        print()
        print("  2. Balanced Mode (6 FPS) ⚡")
        print("     - All features: Depth + Detection + Targets")
        print("     - Every 2nd frame processed")
        print()
        print("  3. High Performance Mode (10 FPS) 🚀")
        print("     - All features: Depth + Detection + Targets")
        print("     - Every 3rd frame processed")
        print()
        print("=" * 80)
        
        while True:
            try:
                choice = input("Enter mode (1-3) [default: 2]: ").strip()
                if choice == '':
                    choice = '2'
                
                mode = int(choice)
                if mode in [1, 2, 3]:
                    break
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
            except ValueError:
                print("Invalid input. Please enter a number between 1 and 3.")
            except KeyboardInterrupt:
                print("\n\nCancelled by user")
                return 0
        
        print()
        print("=" * 80)
        
        # Apply mode settings
        if mode == 1:
            args.fast = False
            args.interval = 1
            print("Selected: Full Quality Mode (~3 FPS)")
        elif mode == 2:
            args.fast = False
            args.interval = 2
            print("Selected: Balanced Mode (~6 FPS)")
        elif mode == 3:
            args.fast = False
            args.interval = 3
            print("Selected: High Performance Mode (~10 FPS)")
    
    print("=" * 80)
    print(f"Config: {config_path}")
    print(f"Fast mode: {args.fast}")
    print(f"Frame interval: {args.interval}")
    print(f"Auto takeoff: {args.auto_takeoff}")
    print("=" * 80)
    print()
    print("IMPORTANT:")
    print("1. Make sure AirSim simulator is running")
    print("2. AirSim should be accessible at 127.0.0.1:41451")
    print("3. Press 'q' in the display window to quit")
    print()
    
    # If auto-takeoff requested, modify config temporarily
    if args.auto_takeoff:
        print("Note: Auto-takeoff will be performed after initialization")
        print()
    
    try:
        # Create pipeline
        pipeline = DronePipeline(config_path)
        
        # Initialize
        print("Initializing pipeline...")
        if not pipeline.initialize():
            print("\nERROR: Failed to initialize pipeline")
            print("\nTroubleshooting:")
            print("1. Is AirSim running?")
            print("2. Check that AirSim is on port 41451")
            print("3. Try running AirSim with admin privileges")
            return 1
        
        print("\nPipeline initialized successfully!")
        print("Starting main processing loop...\n")
        
        # Run pipeline
        pipeline.run(
            display=not args.no_display,
            max_frames=args.max_frames,
            process_interval=args.interval,
            fast_mode=args.fast
        )
        
        print("\nTest completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 0
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
