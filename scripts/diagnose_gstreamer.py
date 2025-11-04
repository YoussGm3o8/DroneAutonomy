"""
GStreamer Diagnostics and Testing Utility

Run this script to diagnose GStreamer and NVIDIA GPU issues with Gazebo video streaming.
"""

import subprocess
import sys
import cv2


def run_cmd(cmd, shell=True, timeout=10):
    """Run command and return output"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def check_opencv_gstreamer():
    """Check if OpenCV has GStreamer support"""
    print("=" * 60)
    print("OpenCV GStreamer Support Check")
    print("=" * 60)
    
    build_info = cv2.getBuildInformation()
    
    # Check for GStreamer in build info
    has_gstreamer = "GStreamer" in build_info and "YES" in build_info
    
    print(f"OpenCV Version: {cv2.__version__}")
    
    if has_gstreamer:
        print("✓ OpenCV compiled with GStreamer support")
        
        # Extract GStreamer version from build info
        for line in build_info.split('\n'):
            if 'GStreamer' in line:
                print(f"  {line.strip()}")
    else:
        print("✗ OpenCV NOT compiled with GStreamer support")
        print("  You need to install opencv-python with GStreamer support")
        print("  Try: pip uninstall opencv-python opencv-contrib-python")
        print("       pip install opencv-contrib-python")
    
    print()
    return has_gstreamer


def check_wsl_gstreamer():
    """Check GStreamer installation in WSL"""
    print("=" * 60)
    print("WSL GStreamer Installation Check")
    print("=" * 60)
    
    # Check gst-inspect-1.0
    ret, stdout, stderr = run_cmd("wsl gst-inspect-1.0 --version")
    
    if ret == 0:
        print("✓ GStreamer installed in WSL")
        version_line = stdout.split('\n')[0] if stdout else "Unknown version"
        print(f"  {version_line}")
    else:
        print("✗ GStreamer not found in WSL")
        print(f"  Error: {stderr}")
        return False
    
    print()
    
    # Check critical plugins
    print("Checking GStreamer plugins:")
    plugins = [
        "coreelements",
        "videoconvert",
        "x264",
        "rtph264pay",
        "rtph264depay",
        "udpsink",
        "udpsrc",
        "appsrc",
        "appsink",
    ]
    
    missing_plugins = []
    
    for plugin in plugins:
        ret, stdout, stderr = run_cmd(f"wsl gst-inspect-1.0 {plugin}", timeout=5)
        if ret == 0:
            print(f"  ✓ {plugin}")
        else:
            print(f"  ✗ {plugin} (MISSING)")
            missing_plugins.append(plugin)
    
    print()
    
    # Check NVIDIA hardware acceleration plugins
    print("Checking NVIDIA hardware acceleration:")
    hw_plugins = ["nvh264dec", "nvh264enc"]
    
    has_hw_accel = True
    for plugin in hw_plugins:
        ret, stdout, stderr = run_cmd(f"wsl gst-inspect-1.0 {plugin}", timeout=5)
        if ret == 0:
            print(f"  ✓ {plugin} (available)")
        else:
            print(f"  ✗ {plugin} (not available)")
            has_hw_accel = False
    
    if not has_hw_accel:
        print("  ℹ Hardware acceleration not available - will use software encoding")
        print("  To enable, install: gstreamer1.0-plugins-nvcodec")
    
    print()
    
    return len(missing_plugins) == 0


def check_nvidia_gpu():
    """Check NVIDIA GPU availability"""
    print("=" * 60)
    print("NVIDIA GPU Check")
    print("=" * 60)
    
    ret, stdout, stderr = run_cmd("wsl nvidia-smi --query-gpu=name,driver_version --format=csv,noheader")
    
    if ret == 0 and stdout:
        print("✓ NVIDIA GPU detected in WSL")
        print(f"  {stdout.strip()}")
        
        # Check if GPU is being used
        ret2, stdout2, stderr2 = run_cmd("wsl glxinfo | grep 'OpenGL renderer'")
        if ret2 == 0:
            print(f"  OpenGL Renderer: {stdout2.strip()}")
    else:
        print("✗ NVIDIA GPU not detected in WSL")
        print("  Make sure NVIDIA drivers are installed in WSL2")
    
    print()


def test_rtp_pipeline():
    """Test RTP/H264 GStreamer pipeline"""
    print("=" * 60)
    print("Testing RTP/H264 Receiver Pipeline")
    print("=" * 60)
    
    pipeline = (
        'udpsrc port=5600 '
        'caps="application/x-rtp,media=(string)video,clock-rate=(int)90000,encoding-name=(string)H264,payload=(int)96" ! '
        'rtpjitterbuffer latency=50 drop-on-latency=true ! '
        'rtph264depay ! '
        'h264parse ! '
        'avdec_h264 ! '
        'videoconvert ! '
        'video/x-raw,format=BGR ! '
        'appsink drop=true max-buffers=2 sync=false'
    )
    
    print(f"Pipeline: {pipeline}")
    print()
    
    try:
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        
        if cap.isOpened():
            print("✓ Pipeline opened successfully")
            print("  Waiting for frames (5 seconds)...")
            
            import time
            start_time = time.time()
            frame_count = 0
            
            while time.time() - start_time < 5:
                ret, frame = cap.read()
                if ret:
                    frame_count += 1
                time.sleep(0.1)
            
            cap.release()
            
            if frame_count > 0:
                print(f"✓ Received {frame_count} frames")
            else:
                print("⚠ Pipeline opened but no frames received")
                print("  Make sure Gazebo GStreamer bridge is running and streaming")
        else:
            print("✗ Failed to open pipeline")
            print("  Check:")
            print("  1. OpenCV has GStreamer support")
            print("  2. All GStreamer plugins are installed")
            print("  3. Gazebo bridge is running and streaming to port 5600")
    
    except Exception as e:
        print(f"✗ Error testing pipeline: {e}")
    
    print()


def print_recommendations():
    """Print recommendations for fixing issues"""
    print("=" * 60)
    print("Recommendations")
    print("=" * 60)
    print()
    print("If you see errors above, try these fixes:")
    print()
    print("1. Install GStreamer in WSL:")
    print("   wsl bash -c 'cd /mnt/c/Users/Youssef/Documents/Code/ComputerVision/DroneAutonomy/scripts && bash setup_wsl_gstreamer.sh'")
    print()
    print("2. Ensure Gazebo is using NVIDIA GPU:")
    print("   The GazeboManager now automatically forces NVIDIA GPU rendering")
    print()
    print("3. Test GStreamer in WSL directly:")
    print("   wsl gst-launch-1.0 videotestsrc ! x264enc ! rtph264pay ! udpsink host=10.255.255.254 port=5600")
    print()
    print("4. Check firewall (allow UDP port 5600):")
    print("   Windows Firewall -> Allow an app -> Add port 5600 UDP")
    print()
    print("5. Force NVIDIA GPU in WSL:")
    print("   wsl source ~/enable_nvidia_gpu.sh")
    print()


def main():
    print("\n" + "=" * 60)
    print("GStreamer & Gazebo Video Diagnostics")
    print("=" * 60)
    print()
    
    # Run all checks
    opencv_ok = check_opencv_gstreamer()
    wsl_ok = check_wsl_gstreamer()
    check_nvidia_gpu()
    
    if opencv_ok and wsl_ok:
        test_rtp_pipeline()
    
    print_recommendations()
    
    print("=" * 60)
    print("Diagnostics Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
