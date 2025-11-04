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
    
    def __init__(self, world_path=None, udp_port=5600, auto_start_sitl=True):
        """
        Initialize Gazebo manager.
        
        Args:
            world_path: Path to SDF world file (default: uses sonoma_raceway.sdf with iris_with_camera)
            udp_port: UDP port for GStreamer (default: 5600)
            auto_start_sitl: Automatically start ArduPilot SITL (default: True)
        """
        if world_path is None:
            # Default to Sonoma Raceway (built into Gazebo with Prius, we add iris_with_camera)
            self.world_path = "~/gz_ws/src/ardupilot_gazebo/worlds/sonoma_raceway_with_drone.sdf"
        else:
            self.world_path = world_path
            
        self.udp_port = udp_port
        self.auto_start_sitl = auto_start_sitl
        self.windows_ip = self._get_windows_ip()
        self.sitl_process = None
        
    def _get_windows_ip(self):
        """Get Windows host IP address from WSL perspective."""
        try:
            result = subprocess.run(
                ['wsl', 'bash', '-c', "ip route show | grep -i default | awk '{print $3}'"],
                capture_output=True, text=True, timeout=5, check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                # Extract just the IP address (first line, trimmed)
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    # Look for IP pattern
                    parts = line.split()
                    for part in parts:
                        if '.' in part and part.count('.') == 3:
                            # Validate it's an IP
                            try:
                                octets = part.split('.')
                                if all(0 <= int(o) <= 255 for o in octets):
                                    print(f"✓ Detected Windows IP from WSL: {part}")
                                    return part
                            except:
                                continue
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
    
    def is_sitl_running(self):
        """Check if ArduPilot SITL is running in WSL."""
        try:
            result = subprocess.run(
                ['wsl', 'bash', '-c', 'pgrep -f "sim_vehicle.py"'],
                capture_output=True, text=True, timeout=5, check=False
            )
            return result.returncode == 0 and result.stdout.strip()
        except Exception as e:
            print(f"Error checking SITL status: {e}")
            return False
    
    def start_sitl(self):
        """
        Start ArduPilot SITL in background.
        
        Returns:
            bool: True if started successfully
        """
        # Check if already running
        if self.is_sitl_running():
            print("✓ ArduPilot SITL already running")
            return True
        
        # Check if ArduPilot is installed
        try:
            check_result = subprocess.run(
                ['wsl', 'bash', '-c', 'test -d ~/ardupilot && echo "exists"'],
                capture_output=True, text=True, timeout=5, check=False
            )
            if "exists" not in check_result.stdout:
                print("⚠ ArduPilot not found at ~/ardupilot - skipping SITL")
                return False
        except Exception as e:
            print(f"⚠ Could not check for ArduPilot: {e}")
            return False
        
        print("🚁 Starting ArduPilot SITL...")
        
        try:
            # FIXED: Simplified approach using batch script
            # This is the most reliable method for Windows + WSL
            
            # Get the project root directory
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            
            # Create scripts directory if it doesn't exist
            scripts_dir = os.path.join(project_root, 'scripts')
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Create batch script dynamically
            batch_script = os.path.join(scripts_dir, 'start_sitl_auto.bat')
            with open(batch_script, 'w') as f:
                f.write('@echo off\n')
                f.write('title ArduPilot SITL\n')
                f.write('echo ========================================\n')
                f.write('echo   ArduPilot SITL Starting...\n')
                f.write('echo ========================================\n')
                f.write('echo.\n')
                # FIXED: Export PATH to include .local/bin where mavproxy.py is installed
                # Removed --map --console flags to avoid NumPy/matplotlib GUI issues
                f.write('wsl bash -c "export PATH=\\"$HOME/.local/bin:$PATH\\" && cd ~/ardupilot && Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON -I0"\n')
                f.write('echo.\n')
                f.write('echo SITL terminated.\n')
                f.write('pause\n')
            
            print(f"✓ Created launcher: {batch_script}")
            
            # Launch the batch script in a new window
            # This method is reliable because:
            # 1. Batch script handles all the WSL command passing
            # 2. cmd /c start creates a new window that persists
            # 3. /k keeps the window open so you can see errors
            
            # Note: Using 'start' command which creates its own window
            # No need for CREATE_NEW_CONSOLE flag when using 'start'
            self.sitl_process = subprocess.Popen(
                ['cmd', '/c', 'start', 'cmd', '/k', batch_script],
                shell=False
            )
            
            print("✓ ArduPilot SITL terminal launched")
            print("   A new window should have appeared")
            print("⏳ Waiting 15 seconds for SITL to initialize...")
            time.sleep(15)
            
            # Verify it started
            if self.is_sitl_running():
                print("✓ ArduPilot SITL confirmed running")
                return True
            else:
                print("⚠ SITL process not detected yet")
                print("💡 Check the SITL window - it may still be compiling")
                print("💡 First run can take 30-60 seconds to compile")
                print("💡 If the window closed immediately, check:")
                print("   1. ArduPilot is installed: wsl ls ~/ardupilot")
                print("   2. sim_vehicle.py exists: wsl ls ~/ardupilot/Tools/autotest/sim_vehicle.py")
                # Return True anyway since window opened
                return True
                
        except Exception as e:
            print(f"✗ Error starting SITL: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stop_sitl(self):
        """Stop ArduPilot SITL."""
        try:
            print("🛑 Stopping ArduPilot SITL...")
            subprocess.run(
                ['wsl', 'bash', '-c', 'pkill -f "sim_vehicle.py"'],
                timeout=5, check=False
            )
            time.sleep(1)
            print("✓ SITL stopped")
            return True
        except Exception as e:
            print(f"Error stopping SITL: {e}")
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
    
    def _update_sdf_with_ip(self, sdf_path, windows_ip, udp_port):
        """Update SDF file with correct Windows IP and UDP port."""
        try:
            with open(sdf_path, 'r') as f:
                content = f.read()
            
            # Replace udp_host with Windows IP
            import re
            content = re.sub(
                r'<udp_host>[^<]+</udp_host>',
                f'<udp_host>{windows_ip}</udp_host>',
                content
            )
            content = re.sub(
                r'<udp_port>[^<]+</udp_port>',
                f'<udp_port>{udp_port}</udp_port>',
                content
            )
            
            with open(sdf_path, 'w') as f:
                f.write(content)
            
            print(f"✓ Updated SDF with IP: {windows_ip}:{udp_port}")
            return True
        except Exception as e:
            print(f"⚠ Could not update SDF file: {e}")
            return False
    
    def start_gazebo(self, visible=True, use_nvidia_gpu=False):
        """
        Start Gazebo Harmonic in WSL with GStreamer camera plugin.
        Uses 'gz sim -v4 -r world.sdf' as per ArduPilot documentation.
        Optionally starts ArduPilot SITL if auto_start_sitl is True.
        
        Args:
            visible: Open terminal window (True) or run in background (False)
            use_nvidia_gpu: Use NVIDIA GPU for rendering (default: False for WSL)
        
        Returns:
            bool: True if started successfully
        """
        print(f"🚀 Starting Gazebo Harmonic with ArduPilot...")
        print(f"📁 World file: {self.world_path}")
        print(f"🌐 Streaming to: {self.windows_ip}:{self.udp_port}")
        
        # Start ArduPilot SITL first if enabled and not already running
        if self.auto_start_sitl:
            if not self.is_sitl_running():
                print("\n🚁 Auto-starting ArduPilot SITL...")
                self.start_sitl()
            else:
                print("✓ ArduPilot SITL already running")
        
        # Set environment for ArduPilot models and plugins (per ArduPilot documentation)
        gz_env = (
            'export GZ_SIM_SYSTEM_PLUGIN_PATH=$HOME/gz_ws/src/ardupilot_gazebo/build:~/.gz/sim/plugins:$GZ_SIM_SYSTEM_PLUGIN_PATH && '
            'export GZ_SIM_RESOURCE_PATH=$HOME/gz_ws/src/ardupilot_gazebo/models:$HOME/gz_ws/src/ardupilot_gazebo/worlds:$GZ_SIM_RESOURCE_PATH && '
        )
        
        # Expand tilde in path
        world_path_expanded = self.world_path.replace('~', '$HOME')
        
        # Command: gz sim -v4 -r world.sdf
        gz_command = f"{gz_env}gz sim -v4 -r {world_path_expanded}"
        print(f"📜 Command: gz sim -v4 -r {self.world_path}")
        
        try:
            if visible:
                # Open in new terminal window
                command_to_run = [
                    'cmd', '/c', 'start', 'wsl.exe', 'bash', '-c',
                    gz_command
                ]
                subprocess.Popen(command_to_run)
                print("✓ Gazebo terminal window opened")
                print("⏳ Waiting for Gazebo to initialize...")
                time.sleep(10)  # ArduPilot worlds take longer to load
            else:
                # Run in background
                subprocess.Popen(
                    ['wsl', 'bash', '-c', gz_command],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("✓ Gazebo started in background")
                time.sleep(10)
            
            return True
        except Exception as e:
            print(f"✗ Error starting Gazebo: {e}")
            return False
    
    def stop_gazebo(self):
        """Stop Gazebo simulation and optionally stop SITL."""
        try:
            print("🛑 Stopping Gazebo...")
            subprocess.run(
                ['wsl', 'bash', '-c', 'pkill -f "gz sim"'],
                timeout=5, check=False
            )
            time.sleep(1)
            print("✓ Gazebo stopped")
            
            # Also stop SITL if auto_start_sitl is enabled
            if self.auto_start_sitl:
                print("🛑 Stopping ArduPilot SITL...")
                self.stop_sitl()
            
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
