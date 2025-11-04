"""
Gazebo Management Utilities

Automatically start and manage Gazebo Harmonic simulation with GStreamer plugin.
"""

import subprocess
import time
import os
import socket

class GazeboManager:
    """Manage Gazebo Harmonic simulation process with GStreamer camera plugin."""
    
    def __init__(self, world_path=None):
        """
        Initialize Gazebo manager.
        
        Args:
            world_path: Path to SDF world file (default: uses camera test world)
        """
        if world_path is None:
            # Default to the camera test world with GStreamer plugin
            self.world_path = "config/gazebo_models/camera_gstreamer_test.sdf"
        else:
            self.world_path = world_path
            
        self.windows_ip = self._get_windows_ip()
        
    def is_gazebo_running(self):
        """Check if a 'gz sim' process is running in WSL."""
        try:
            result = subprocess.run(
                ['wsl', 'pgrep', '-f', 'gz sim'],
                capture_output=True, text=True, timeout=5, check=False
            )
            return result.returncode == 0 and result.stdout.strip()
        except Exception as e:
            print(f"Error checking Gazebo status: {e}")
            return False
            
    def is_bridge_running(self):
        """Check if the GStreamer camera bridge is running."""
        try:
            result = subprocess.run(
                ['wsl', 'pgrep', '-f', 'gazebo_gstreamer_bridge.py'],
                capture_output=True, text=True, timeout=5, check=False
            )
            return result.returncode == 0 and result.stdout.strip()
        except Exception as e:
            print(f"Error checking bridge status: {e}")
            return False

    def start_gazebo(self, world='iris_runway', visible=True, use_nvidia_gpu=True):
        """Start Gazebo in WSL."""
        print(f"🚀 Starting Gazebo in WSL with world: {world}")
        
        env_vars = [
            'source ~/.profile',
            'export GZ_SIM_RESOURCE_PATH="$HOME/gz_ws/src/ardupilot_gazebo/models:$HOME/gz_ws/src/ardupilot_gazebo/worlds:$GZ_SIM_RESOURCE_PATH"',
            'export GZ_SIM_SYSTEM_PLUGIN_PATH="$HOME/gz_ws/src/ardupilot_gazebo/build:$GZ_SIM_SYSTEM_PLUGIN_PATH"',
            'export DISPLAY=:0'
        ]
        if use_nvidia_gpu:
            print("🎮 Forcing NVIDIA GPU rendering in WSL.")
            env_vars.extend(['export __NV_PRIME_RENDER_OFFLOAD=1', 'export __GLX_VENDOR_LIBRARY_NAME=nvidia'])
        
        gz_cmd = f'gz sim -v4 -r worlds/{world}.sdf'
        full_wsl_command = f"{' && '.join(env_vars)} && cd {self.gazebo_path} && {gz_cmd}"

        try:
            if visible:
                command_to_run = ['cmd', '/c', 'start', 'wsl.exe', 'bash', '-ic', full_wsl_command]
                subprocess.Popen(command_to_run)
                print("✓ Gazebo terminal window opened. Please wait for initialization.")
            else:
                subprocess.Popen(['wsl', 'bash', '-ic', full_wsl_command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            return True
        except Exception as e:
            print(f"✗ Error starting Gazebo: {e}")
            return False

    def start_bridge(self, port=5600, visible=True):
        """Start the GStreamer camera bridge in WSL."""
        print(f"🌉 Starting GStreamer bridge on port {port}")
        
        # This assumes the project root is mapped to C:\Users\Youssef\Documents\Code\ComputerVision\DroneAutonomy
        # The path needs to be accessible from within WSL.
        script_path_wsl = "/mnt/c/Users/Youssef/Documents/Code/ComputerVision/DroneAutonomy/scripts/gazebo_gstreamer_bridge.py"
        bridge_cmd = f"python3 {script_path_wsl} --port {port}"
        full_wsl_command = f'bash -ic "source ~/.profile && {bridge_cmd}"'

        try:
            if visible:
                command_to_run = ['cmd', '/c', 'start', 'wsl.exe', 'bash', '-ic', bridge_cmd]
                subprocess.Popen(command_to_run)
                print("✓ Bridge terminal window opened.")
            else:
                subprocess.Popen(['wsl', 'bash', '-ic', bridge_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            return True
        except Exception as e:
            print(f"✗ Error starting bridge: {e}")
            return False

    def start_gazebo_stack(self, world='iris_runway', port=5600, visible=True, use_nvidia_gpu=True):
        """Start complete Gazebo stack (simulation + GStreamer bridge)."""
        print("🚁 Starting Gazebo stack...")
        
        if not self.is_gazebo_running():
            if not self.start_gazebo(world, visible, use_nvidia_gpu):
                return False
            print("⏳ Waiting for Gazebo to initialize (15s)...")
            time.sleep(15) # Give Gazebo time to start up
        else:
            print("✓ Gazebo already running.")

        if not self.is_bridge_running():
            if not self.start_bridge(port, visible):
                return False
        else:
            print("✓ Bridge already running.")
            
        print("✓ Gazebo stack started successfully!")
        return True
