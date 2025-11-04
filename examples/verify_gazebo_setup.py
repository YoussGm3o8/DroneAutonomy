"""
Quick test to verify Gazebo camera integration is ready.

This tests that all imports work and configuration is correct,
without requiring Gazebo to be running.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def test_imports():
    """Test that all required imports work."""
    print("Testing imports...")
    
    try:
        from drone_autonomy.video.gazebo_camera import (
            VideoStreamGazeboUDP,
            VideoStreamGazeboROS2,
            ROS2_AVAILABLE,
            create_gazebo_stream
        )
        print("  ✓ gazebo_camera module imported")
    except ImportError as e:
        print(f"  ✗ Failed to import gazebo_camera: {e}")
        return False
    
    try:
        from drone_autonomy.video.stream import VideoStream, GAZEBO_AVAILABLE
        print("  ✓ VideoStream with Gazebo support imported")
    except ImportError as e:
        print(f"  ✗ Failed to import VideoStream: {e}")
        return False
    
    print(f"\n  ROS2 Available: {'Yes' if ROS2_AVAILABLE else 'No (optional)'}")
    print(f"  Gazebo Available: {'Yes' if GAZEBO_AVAILABLE else 'No'}")
    
    return True


def test_configuration():
    """Test that configuration file exists and is valid."""
    print("\nTesting configuration...")
    
    config_path = Path(__file__).parent.parent / 'config' / 'gazebo_simulation.yaml'
    
    if not config_path.exists():
        print(f"  ✗ Config file not found: {config_path}")
        return False
    
    print(f"  ✓ Config file exists: {config_path}")
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if 'video' in config:
            print("  ✓ Video configuration found")
            video_config = config['video']
            
            if video_config.get('backend') == 'gazebo':
                print(f"    Backend: gazebo")
                print(f"    Method: {video_config.get('gazebo_backend', 'udp')}")
                
                if video_config.get('gazebo_backend') == 'udp':
                    print(f"    UDP Port: {video_config.get('udp_port', 5600)}")
                else:
                    print(f"    ROS2 Topic: {video_config.get('gazebo_topic', '/camera')}")
            else:
                print(f"  ⚠ Backend is set to: {video_config.get('backend')}")
        else:
            print("  ✗ No video configuration found")
            return False
        
    except ImportError:
        print("  ⚠ PyYAML not installed (pip install pyyaml)")
        return True  # Not critical
    except Exception as e:
        print(f"  ✗ Error reading config: {e}")
        return False
    
    return True


def test_model_file():
    """Test that Gazebo model file exists."""
    print("\nTesting Gazebo model...")
    
    model_path = Path(__file__).parent.parent / 'config' / 'gazebo_models' / 'iris_with_camera.sdf'
    
    if not model_path.exists():
        print(f"  ✗ Model file not found: {model_path}")
        return False
    
    print(f"  ✓ Drone model exists: {model_path}")
    return True


def test_stream_creation():
    """Test that we can create stream objects."""
    print("\nTesting stream creation...")
    
    try:
        from drone_autonomy.video.gazebo_camera import VideoStreamGazeboUDP
        
        config = {
            'gazebo_backend': 'udp',
            'udp_port': 5600,
            'width': 1280,
            'height': 720
        }
        
        stream = VideoStreamGazeboUDP(config)
        print("  ✓ VideoStreamGazeboUDP created successfully")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed to create stream: {e}")
        return False


def check_gazebo_installed():
    """Check if Gazebo is installed."""
    print("\nChecking Gazebo installation...")
    
    import subprocess
    try:
        result = subprocess.run(['gz', 'sim', '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  ✓ Gazebo installed: {version}")
            return True
    except FileNotFoundError:
        print("  ✗ Gazebo not found in PATH")
        print("    Install with: choco install gazebo-garden")
    except Exception as e:
        print(f"  ✗ Error checking Gazebo: {e}")
    
    return False


def check_gstreamer():
    """Check if GStreamer is available."""
    print("\nChecking GStreamer...")
    
    try:
        import cv2
        build_info = cv2.getBuildInformation()
        
        if 'GStreamer' in build_info and 'YES' in build_info:
            print("  ✓ OpenCV built with GStreamer support")
            return True
        else:
            print("  ✗ OpenCV not built with GStreamer")
            print("    This is required for UDP streaming")
            return False
    except Exception as e:
        print(f"  ✗ Error checking GStreamer: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Gazebo Camera Integration - Readiness Check")
    print("=" * 60)
    
    results = {
        'Imports': test_imports(),
        'Configuration': test_configuration(),
        'Model File': test_model_file(),
        'Stream Creation': test_stream_creation(),
        'Gazebo Installed': check_gazebo_installed(),
        'GStreamer Support': check_gstreamer()
    }
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:25s} {status}")
    
    print("\n" + "=" * 60)
    
    required_tests = ['Imports', 'Configuration', 'Model File', 'Stream Creation', 'GStreamer Support']
    optional_tests = ['Gazebo Installed']
    
    required_passed = all(results[t] for t in required_tests)
    
    if required_passed:
        print("✅ All required components are ready!")
        
        if not results['Gazebo Installed']:
            print("\n⚠️  Gazebo is not installed. Install with:")
            print("   choco install gazebo-garden")
        
        print("\nNext steps:")
        print("  1. Install Gazebo (if not already)")
        print("  2. Start Gazebo: gz sim -v4 -r config\\gazebo_models\\iris_with_camera.sdf")
        print("  3. Test camera: python examples\\test_gazebo_camera.py")
        print("  4. Launch pipeline: python launch_gui.py --config config\\gazebo_simulation.yaml")
    else:
        print("❌ Some required components are missing. Please fix the issues above.")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
