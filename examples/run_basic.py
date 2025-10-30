"""Example script for running the DroneAutonomy pipeline with camera input."""

import sys
sys.path.insert(0, '/home/runner/work/DroneAutonomy/DroneAutonomy/src')

from drone_autonomy.pipeline import DronePipeline


def main():
    """Run pipeline with default camera input."""
    print("=" * 80)
    print("DroneAutonomy - Basic Camera Example")
    print("=" * 80)
    print()
    print("This example runs the full pipeline with default camera input.")
    print("Press 'q' to quit.")
    print()
    
    # Create pipeline with default configuration
    pipeline = DronePipeline()
    
    # Initialize pipeline
    if not pipeline.initialize():
        print("Failed to initialize pipeline")
        return 1
    
    # Run pipeline
    try:
        pipeline.run(display=True)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
