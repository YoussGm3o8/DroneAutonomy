"""Example script for AirSim simulation."""

import sys
import time
sys.path.insert(0, '/home/runner/work/DroneAutonomy/DroneAutonomy/src')

from drone_autonomy.simulation.airsim_interface import AirSimInterface
from drone_autonomy.utils.logger import setup_logging


def main():
    """Test AirSim integration."""
    print("=" * 80)
    print("DroneAutonomy - AirSim Simulation Test")
    print("=" * 80)
    print()
    
    setup_logging()
    
    config = {
        'airsim_ip': '127.0.0.1',
        'airsim_port': 41451
    }
    
    print("Connecting to AirSim...")
    airsim = AirSimInterface(config)
    
    if not airsim.connect():
        print("Error: Failed to connect to AirSim")
        print("Make sure AirSim is running")
        return 1
    
    print("Connected to AirSim successfully")
    
    try:
        # Takeoff
        print("\nTaking off...")
        airsim.takeoff(timeout_sec=5.0)
        time.sleep(2)
        
        # Get camera image
        print("\nGetting camera image...")
        image = airsim.get_camera_image()
        if image is not None:
            import cv2
            cv2.imshow('AirSim Camera', image)
            cv2.waitKey(2000)
            print(f"Camera image shape: {image.shape}")
        
        # Get IMU data
        print("\nGetting IMU data...")
        imu = airsim.get_imu_data()
        if imu:
            print(f"Linear acceleration: {imu['linear_acceleration']}")
            print(f"Angular velocity: {imu['angular_velocity']}")
        
        # Get ground truth pose
        print("\nGetting ground truth pose...")
        position, orientation = airsim.get_ground_truth_pose()
        if position is not None:
            print(f"Position: {position}")
            print(f"Orientation (quat): {orientation}")
        
        # Land
        print("\nLanding...")
        airsim.land(timeout_sec=5.0)
        
        print("\nTest completed successfully")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        airsim.disconnect()
        import cv2
        cv2.destroyAllWindows()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
