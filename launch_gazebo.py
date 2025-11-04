"""
Complete Gazebo diagnostic and launcher
"""
import subprocess
import time
import sys

def check_gazebo_status():
    """Check if Gazebo and bridge are running"""
    print("\n" + "="*60)
    print("Gazebo Status Check")
    print("="*60)
    
    # Check Gazebo
    result = subprocess.run(['wsl', 'pgrep', '-af', 'gz sim'], 
                          capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        print(f"✓ Gazebo running: {result.stdout.strip()}")
    else:
        print("✗ Gazebo NOT running")
    
    # Check bridge
    result = subprocess.run(['wsl', 'pgrep', '-af', 'wsl_gazebo_bridge'], 
                          capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        print(f"✓ Bridge running: {result.stdout.strip()}")
    else:
        print("✗ Bridge NOT running")
    
    # Check camera topic
    result = subprocess.run(['wsl', 'gz', 'topic', '-l'], 
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        camera_found = False
        for line in result.stdout.split('\n'):
            if 'camera/image' in line and 'iris' in line:
                print(f"✓ Camera topic: {line.strip()}")
                camera_found = True
                break
        if not camera_found:
            print("✗ Camera topic NOT found")
            print("\nAvailable topics:")
            for line in result.stdout.split('\n')[:10]:
                if line.strip():
                    print(f"  {line.strip()}")
    else:
        print("✗ Could not list Gazebo topics (Gazebo not running?)")

def launch_gazebo():
    """Launch Gazebo and bridge with visible windows"""
    print("\n" + "="*60)
    print("Launching Gazebo Stack")
    print("="*60)
    
    # Step 1: Launch Gazebo
    print("\n1. Launching Gazebo...")
    print("   Opening CMD window with Gazebo...")
    
    # Set environment explicitly for Gazebo
    env_vars = 'export GZ_SIM_RESOURCE_PATH="$HOME/gz_ws/src/ardupilot_gazebo/models:$HOME/gz_ws/src/ardupilot_gazebo/worlds" && export GZ_SIM_SYSTEM_PLUGIN_PATH="$HOME/gz_ws/src/ardupilot_gazebo/build:$GZ_SIM_SYSTEM_PLUGIN_PATH"'
    full_cmd = f'{env_vars} && cd ~/gz_ws/src/ardupilot_gazebo && gz sim -v4 -r worlds/iris_runway.sdf'
    
    subprocess.Popen(
        ['cmd', '/k', 'wsl', 'bash', '-c', full_cmd],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    print("   ✓ Gazebo CMD window opened")
    print("   ⏳ Waiting 20 seconds for Gazebo to initialize...")
    
    # Wait and check
    for i in range(20):
        time.sleep(1)
        result = subprocess.run(['wsl', 'pgrep', '-f', 'gz sim'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✓ Gazebo detected running (after {i+1}s)")
            break
        sys.stdout.write(f"\r   Waiting... {i+1}/20s")
        sys.stdout.flush()
    else:
        print("\n   ⚠ Gazebo process not detected!")
        print("   Check the CMD window for errors")
        return False
    
    # Step 2: Wait for camera topic
    print("\n\n2. Waiting for camera topic...")
    for i in range(15):
        time.sleep(1)
        result = subprocess.run(['wsl', 'gz', 'topic', '-l'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'camera/image' in line and 'iris' in line:
                    print(f"   ✓ Camera topic found: {line.strip()}")
                    break
            else:
                sys.stdout.write(f"\r   Waiting for camera... {i+1}/15s")
                sys.stdout.flush()
                continue
            break
    else:
        print("\n   ⚠ Camera topic not found!")
        print("   Gazebo may still be loading the world...")
    
    # Step 3: Launch bridge
    print("\n\n3. Launching camera bridge...")
    print("   Opening CMD window with bridge...")
    subprocess.Popen(
        ['cmd', '/k', 'wsl', 'bash', '-c',
         'cd /mnt/c/Users/Youssef/Documents/Code/ComputerVision/DroneAutonomy/scripts && python3 wsl_gazebo_bridge.py --port 8554'],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    print("   ✓ Bridge CMD window opened")
    print("   ⏳ Waiting 5 seconds for bridge to start...")
    
    for i in range(5):
        time.sleep(1)
        result = subprocess.run(['wsl', 'pgrep', '-f', 'wsl_gazebo_bridge'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✓ Bridge detected running (after {i+1}s)")
            break
    else:
        print("   ⚠ Bridge process not detected!")
    
    print("\n" + "="*60)
    print("✓ Launch complete!")
    print("="*60)
    print("\nYou should see TWO CMD windows:")
    print("  1. Gazebo window - should show 3D simulation")
    print("  2. Bridge window - should show 'Streaming... Press Ctrl+C to stop'")
    print("\nIf you see errors, read them carefully in the CMD windows")
    print("\nNext step: Launch GUI with: python launch_gui.py")
    return True

def main():
    """Main function"""
    print("Gazebo Launcher and Diagnostic Tool")
    
    # Check current status
    check_gazebo_status()
    
    # Ask to launch
    print("\n" + "="*60)
    choice = input("\nLaunch Gazebo and bridge? (y/n): ").strip().lower()
    
    if choice == 'y':
        launch_gazebo()
        print("\n" + "="*60)
        print("Checking final status...")
        time.sleep(2)
        check_gazebo_status()
    else:
        print("Cancelled.")

if __name__ == "__main__":
    main()
