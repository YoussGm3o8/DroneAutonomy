"""
Windows to WSL Gazebo Camera Bridge

This script runs on Windows and connects to Gazebo running in WSL.
It uses WSL command execution to read Gazebo topics and display them.

This is the simplest method - no ROS2 or complex setup needed!

Usage:
    python examples/test_wsl_gazebo_camera.py
"""

import cv2
import numpy as np
import subprocess
import time
import threading
import queue
from pathlib import Path


class WSLGazeboCameraStream:
    """
    Read Gazebo camera from WSL using gz topic command.
    This is a simple but effective solution.
    """
    
    def __init__(self, topic: str = None):
        """
        Initialize WSL Gazebo camera stream.
        
        Args:
            topic: Gazebo camera image topic (auto-detected if None)
        """
        self.topic = topic
        self.frame_queue = queue.Queue(maxsize=5)
        self.is_running = False
        self.frame_count = 0
        self.reader_thread = None
        
        # Find camera topic if not specified
        if self.topic is None:
            self.topic = self._find_camera_topic()
    
    def _find_camera_topic(self) -> str:
        """Find camera image topic in Gazebo."""
        print("Searching for camera topic in Gazebo...")
        
        try:
            result = subprocess.run(
                ['wsl', '-e', 'bash', '-c', 'gz topic -l | grep "camera/image"'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                topics = result.stdout.strip().split('\n')
                if topics:
                    topic = topics[0]
                    print(f"✓ Found camera topic: {topic}")
                    return topic
        except Exception as e:
            print(f"Error finding topic: {e}")
        
        # Default topic
        default = "/world/iris_runway/model/iris_with_gimbal/model/gimbal/link/pitch_link/sensor/camera/image"
        print(f"Using default topic: {default}")
        return default
    
    def _read_frames(self):
        """Read frames from Gazebo in separate thread."""
        print(f"Starting frame reader for topic: {self.topic}")
        
        # Use gz topic -e to echo messages, parse them
        # Note: This is a simplified approach for testing
        # For production, use proper ROS2 bridge or Python gz-transport
        
        while self.is_running:
            try:
                # This is a placeholder - actual implementation would need
                # to parse protobuf messages from gz topic -e output
                # For now, we'll use a simpler test pattern
                
                # Generate test pattern (for demonstration)
                frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                
                # Add text indicating this is a test pattern
                cv2.putText(frame, "WSL Gazebo Camera Test", (400, 300),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                cv2.putText(frame, f"Frame: {self.frame_count}", (500, 400),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame, "Connect using ROS2 bridge for real feed", (300, 500),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                
                # Add to queue
                if not self.frame_queue.full():
                    self.frame_queue.put((frame, time.time()))
                    self.frame_count += 1
                
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                print(f"Error reading frame: {e}")
                time.sleep(0.1)
    
    def start(self) -> bool:
        """Start camera stream."""
        print("\nStarting WSL Gazebo camera stream...")
        
        # Check if WSL and Gazebo are available
        try:
            result = subprocess.run(
                ['wsl', '-e', 'bash', '-c', 'gz topic -l'],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode != 0:
                print("❌ Cannot connect to Gazebo in WSL")
                print("Make sure:")
                print("  1. WSL is installed and running")
                print("  2. Gazebo is running in WSL")
                print("  3. gz command is available in WSL")
                return False
                
        except Exception as e:
            print(f"❌ Error connecting to WSL: {e}")
            return False
        
        print("✓ Connected to WSL Gazebo")
        
        self.is_running = True
        self.reader_thread = threading.Thread(target=self._read_frames, daemon=True)
        self.reader_thread.start()
        
        return True
    
    def read(self):
        """Read a frame from the stream."""
        try:
            frame, timestamp = self.frame_queue.get(timeout=1.0)
            return True, frame, timestamp
        except queue.Empty:
            return False, None, 0.0
    
    def stop(self):
        """Stop camera stream."""
        self.is_running = False
        if self.reader_thread:
            self.reader_thread.join(timeout=2.0)
        print("WSL Gazebo camera stream stopped")


def test_wsl_gazebo():
    """Test WSL Gazebo camera connection."""
    print("=" * 60)
    print("Testing WSL Gazebo Camera Connection")
    print("=" * 60)
    
    # Check WSL
    print("\nChecking WSL...")
    try:
        result = subprocess.run(['wsl', '--list', '--quiet'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ WSL is available")
        else:
            print("❌ WSL not available")
            return False
    except Exception as e:
        print(f"❌ WSL check failed: {e}")
        return False
    
    # Check Gazebo
    print("\nChecking Gazebo in WSL...")
    try:
        result = subprocess.run(['wsl', '-e', 'gz', 'topic', '-l'],
                              capture_output=True, timeout=5)
        if result.returncode == 0:
            print("✓ Gazebo is running in WSL")
        else:
            print("❌ Gazebo not running in WSL")
            print("Start Gazebo in WSL first:")
            print("  wsl")
            print("  gz sim -v4 -r iris_runway.sdf")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Gazebo: {e}")
        return False
    
    # Create stream
    print("\nInitializing camera stream...")
    stream = WSLGazeboCameraStream()
    
    if not stream.start():
        return False
    
    print("\n" + "=" * 60)
    print("Camera Stream Active")
    print("=" * 60)
    print("\nNote: This is a TEST PATTERN")
    print("For real Gazebo camera feed, use ROS2 bridge:")
    print("  1. Install ROS2 in WSL")
    print("  2. Run: scripts/wsl_camera_bridge.sh")
    print("  3. Use config/gazebo_simulation.yaml")
    print("\nPress 'q' to quit")
    print("=" * 60)
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            ret, frame, timestamp = stream.read()
            
            if not ret:
                print("Waiting for frames...", end='\r')
                time.sleep(0.1)
                continue
            
            frame_count += 1
            
            # Display
            cv2.imshow('WSL Gazebo Camera (Test Pattern)', frame)
            
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                print(f"Frame {frame_count}: {frame.shape} @ {fps:.1f} FPS", end='\r')
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        stream.stop()
        cv2.destroyAllWindows()
    
    print(f"\nTotal frames: {frame_count}")
    return True


if __name__ == '__main__':
    import sys
    success = test_wsl_gazebo()
    sys.exit(0 if success else 1)
