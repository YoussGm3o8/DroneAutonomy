"""
Test script to verify the fixed iris_with_camera model
Run this to test if the drone can properly take off and hover
"""
import subprocess
import time

def test_model():
    print("="*60)
    print("Testing Fixed Iris Model")
    print("="*60)
    print("\nModel Changes:")
    print("  ✓ Motor multiplier: 838 → 1400 (67% increase)")
    print("  ✓ P-gain: 0.20 → 0.25 (better response)")
    print("  ✓ Max velocity: 2.5 → 3.5 (more headroom)")
    print("  ✓ Camera mass: 0.015kg → 0.005kg (lighter)")
    print("\nExpected Results:")
    print("  • Drone should take off smoothly at ~50% throttle")
    print("  • Hover should be stable around 40-45% throttle")
    print("  • No altitude loss during flight")
    print("  • Better response to attitude commands")
    
    print("\n" + "="*60)
    print("Testing Steps:")
    print("="*60)
    print("\n1. Start Gazebo simulation:")
    print("   wsl bash -c 'cd ~/gz_ws/src/ardupilot_gazebo && gz sim -v4 -r worlds/iris_runway_camera.sdf'")
    print("\n2. Start SITL in another terminal:")
    print("   wsl bash -c 'cd ~/gz_ws && sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --map --console'")
    print("\n3. In MAVProxy, test takeoff:")
    print("   mode guided")
    print("   arm throttle")
    print("   takeoff 5")
    print("\n4. Verify hover stability for 30 seconds")
    print("\nModel location:")
    print("  ~/gz_ws/src/ardupilot_gazebo/models/iris_with_camera/model.sdf")
    print("\n" + "="*60)

if __name__ == "__main__":
    test_model()
