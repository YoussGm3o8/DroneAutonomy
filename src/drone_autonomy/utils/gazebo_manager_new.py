"""
Gazebo Harmonic Management Utilities

Automatically start and manage Gazebo Harmonic simulation with GStreamer camera plugin.
"""

import subprocess
import time
import os
import sys
from pathlib import Path

class GazeboManager:
    """Manage Gazebo Harmonic simulation process with GStreamer camera plugin."""
    
    def __init__(self, world_path=None, udp_port=5600):
        """
        Initialize Gazebo manager.
        
        Args:
            world_path: Path to SDF world file (default: uses camera test world)
            udp_port: UDP port for GStreamer (default: 5600)
        """
        if world_path is None:
            # Default to the camera test world with GStreamer plugin
            self.world_path = "config/gazebo_models/camera_gstreamer_test.sdf"
        else:
            self.world_path = world_path
            
        self.udp_port = udp_port
        self.windows_ip = self._get_windows_ip()
        
    def _get_windows_ip(self):
        """Get Windows host IP address from WSL perspective."""
        try:
            result = subprocess.run(
                ['wsl', 'bash', '-c', "ip route show | grep -i default | awk '{ print $3}'"],
                capture_output=True, text=True, timeout=5, check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                ip = result.stdout.strip()
                print(f"✓ Detected Windows IP from WSL: {ip}")
                return ip
        except Exception as e:
            print(f"Warning: Could not detect Windows IP: {e}")
        
        return "127.0.0.1"  # Fallback to localhost
        
    def is_gazebo_running(self):
        """Check if Gazebo Harmonic is running in WSL."""
        try:
            result = subprocess.run(
                ['wsl', 'bash', '-c', 'pgrep -f "gz sim"'],
                capture_output=True, text=True, timeout=5, check=False
            )
            return result.returncode == 0 and result.stdout.strip()
        except Exception as e:
            print(f"Error checking Gazebo status: {e}")
            return False
    
    def _get_windows_path_for_wsl(self, windows_path):
        """Convert Windows path to WSL path."""
        # Convert backslashes to forward slashes
        path = windows_path.replace('\\', '/')
        
        # Extract drive letter and path
        if ':' in path:
            drive = path[0].lower()
            rest = path[3:]  # Skip "C:/"
            return f"/mnt/{drive}/{rest}"
        
        return path
    
    def start_gazebo(self, visible=True, use_nvidia_gpu=False):
        """
        Start Gazebo Harmonic in WSL with GStreamer camera plugin.
        
        Args:
            visible: Open terminal window (True) or run in background (False)
            use_nvidia_gpu: Use NVIDIA GPU for rendering (default: False for WSL)
        
        Returns:
            bool: True if started successfully
        """
        print(f"🚀 Starting Gazebo Harmonic with GStreamer camera...")
        print(f"📁 World file: {self.world_path}")
        print(f"🌐 Streaming to: {self.windows_ip}:{self.udp_port}")
        
        # Convert Windows path to WSL path
        windows_abs_path = str(Path(self.world_path).resolve())
        wsl_world_path = self._get_windows_path_for_wsl(windows_abs_path)
        
        print(f"📍 WSL path: {wsl_world_path}")
        
        # Set up environment
        env_vars = [
            'source ~/.bashrc'  # Load GStreamer plugin path
        ]
        
        # Add plugin path explicitly
        env_vars.append('export GZ_SIM_SYSTEM_PLUGIN_PATH=$GZ_SIM_SYSTEM_PLUGIN_PATH:$HOME/gazebo_gst_plugin/build')
        env_vars.append('export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/gazebo_gst_plugin/build')
        
        if use_nvidia_gpu:
            print("🎮 Using NVIDIA GPU rendering")
            env_vars.extend([
                'export __NV_PRIME_RENDER_OFFLOAD=1',
                'export __GLX_VENDOR_LIBRARY_NAME=nvidia'
            ])
        
        # Gazebo command
        gz_cmd = f'gz sim -r "{wsl_world_path}"'
        
        # Full command
        full_wsl_command = ' && '.join(env_vars + [gz_cmd])
        
        try:
            if visible:
                # Open in new terminal window
                command_to_run = ['cmd', '/c', 'start', 'wsl.exe', 'bash', '-c', full_wsl_command]
                subprocess.Popen(command_to_run)
                print("✓ Gazebo terminal window opened")
                print("⏳ Waiting for Gazebo to initialize...")
                time.sleep(3)  # Give Gazebo time to start
            else:
                # Run in background
                subprocess.Popen(
                    ['wsl', 'bash', '-c', full_wsl_command],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("✓ Gazebo started in background")
                time.sleep(3)
            
            return True
        except Exception as e:
            print(f"✗ Error starting Gazebo: {e}")
            return False
    
    def stop_gazebo(self):
        """Stop Gazebo simulation."""
        try:
            print("🛑 Stopping Gazebo...")
            subprocess.run(
                ['wsl', 'bash', '-c', 'pkill -f "gz sim"'],
                timeout=5, check=False
            )
            time.sleep(1)
            print("✓ Gazebo stopped")
            return True
        except Exception as e:
            print(f"Error stopping Gazebo: {e}")
            return False
    
    def wait_for_stream(self, timeout=10):
        """
        Wait for GStreamer video stream to become available.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if stream is available
        """
        import socket
        
        print(f"🎥 Waiting for video stream on port {self.udp_port}...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try to bind to the port to check if it's available
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1)
                sock.bind(('0.0.0.0', self.udp_port))
                sock.close()
                
                # Port is free, wait a bit more
                time.sleep(1)
            except OSError:
                # Port is in use, stream might be available
                print(f"✓ Stream detected on port {self.udp_port}")
                return True
        
        print(f"⚠ Stream not detected after {timeout}s")
        return False
    
    def get_gstreamer_pipeline(self):
        """
        Get the GStreamer pipeline string for receiving the video stream.
        
        Returns:
            str: GStreamer pipeline for OpenCV VideoCapture
        """
        pipeline = (
            f"udpsrc address=0.0.0.0 port={self.udp_port} "
            f"caps=\"application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264\" ! "
            f"rtpjitterbuffer ! "
            f"rtph264depay ! "
            f"h264parse ! "
            f"avdec_h264 ! "
            f"videoconvert ! "
            f"video/x-raw,format=BGR ! "
            f"appsink drop=true max-buffers=1 sync=false"
        )
        return pipeline
    
    def test_gstreamer_connection(self):
        """
        Test if GStreamer can connect to the video stream.
        
        Returns:
            bool: True if connection successful
        """
        try:
            import cv2
            
            print("🧪 Testing GStreamer connection...")
            pipeline = self.get_gstreamer_pipeline()
            
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                
                if ret and frame is not None:
                    print(f"✓ GStreamer connection successful! Frame size: {frame.shape}")
                    return True
                else:
                    print("✗ Could not read frame from stream")
                    return False
            else:
                print("✗ Could not open GStreamer pipeline")
                return False
                
        except Exception as e:
            print(f"✗ GStreamer connection test failed: {e}")
            return False


def main():
    """Test Gazebo manager functionality."""
    print("Gazebo Harmonic Manager Test")
    print("=" * 50)
    
    manager = GazeboManager()
    
    print("\n1. Checking if Gazebo is running...")
    if manager.is_gazebo_running():
        print("   ✓ Gazebo is already running")
    else:
        print("   ℹ Gazebo is not running")
        print("\n2. Starting Gazebo...")
        if manager.start_gazebo(visible=True):
            print("   ✓ Gazebo started successfully")
            
            print("\n3. Waiting for video stream...")
            if manager.wait_for_stream(timeout=15):
                print("   ✓ Video stream available")
                
                print("\n4. Testing GStreamer connection...")
                if manager.test_gstreamer_connection():
                    print("   ✓ All tests passed!")
                else:
                    print("   ✗ GStreamer connection failed")
            else:
                print("   ⚠ Video stream not detected")
        else:
            print("   ✗ Failed to start Gazebo")
    
    print("\nGStreamer pipeline:")
    print(manager.get_gstreamer_pipeline())


if __name__ == "__main__":
    main()
