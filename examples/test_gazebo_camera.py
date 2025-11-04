"""
Test Gazebo camera stream integration.

This script tests the connection to Gazebo simulation camera and displays the video feed.
Supports both UDP and ROS2 methods.

Usage:
    python examples/test_gazebo_camera.py [--method udp|ros2] [--port 5600]
"""

import cv2
import numpy as np
import time
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from drone_autonomy.video.gazebo_camera import (
    VideoStreamGazeboUDP,
    VideoStreamGazeboROS2,
    ROS2_AVAILABLE
)


def test_gazebo_udp(port: int = 5600, duration: int = 30):
    """
    Test Gazebo camera via UDP/GStreamer.
    
    Args:
        port: UDP port for video stream
        duration: Test duration in seconds
    """
    print("=" * 60)
    print("Testing Gazebo Camera - UDP Method")
    print("=" * 60)
    print(f"\nPort: {port}")
    print("\nMake sure:")
    print("  1. Gazebo is running with camera-equipped drone model")
    print("  2. Camera sensor has GStreamer video plugin configured")
    print(f"  3. Video is streaming on UDP port {port}")
    print("\nStarting in 3 seconds...")
    time.sleep(3)
    
    # Configuration
    config = {
        'gazebo_backend': 'udp',
        'udp_port': port,
        'width': 1280,
        'height': 720
    }
    
    # Create stream
    stream = VideoStreamGazeboUDP(config)
    
    # Start stream
    print("\n📹 Starting video stream...")
    if not stream.start():
        print("\n❌ Failed to start video stream")
        print("\nTroubleshooting:")
        print("  1. Check if Gazebo is running: gz sim --version")
        print("  2. List Gazebo topics: gz topic -l")
        print("  3. Check camera topic: gz topic -e -t /camera")
        print(f"  4. Verify UDP port {port} is not blocked")
        return False
    
    print("✓ Video stream started\n")
    
    # Read and display frames
    frame_count = 0
    start_time = time.time()
    fps_update_time = start_time
    fps_frame_count = 0
    current_fps = 0.0
    
    print("Controls:")
    print("  q - Quit")
    print("  s - Save screenshot")
    print("  SPACE - Pause/Resume")
    print()
    
    paused = False
    
    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed > duration:
                print(f"\n⏱ Test duration ({duration}s) reached")
                break
            
            if not paused:
                # Read frame
                ret, frame, timestamp = stream.read()
                
                if not ret:
                    print("⚠ No frame received (waiting...)", end='\r')
                    time.sleep(0.1)
                    continue
                
                frame_count += 1
                fps_frame_count += 1
                
                # Calculate FPS every second
                if time.time() - fps_update_time >= 1.0:
                    current_fps = fps_frame_count / (time.time() - fps_update_time)
                    fps_update_time = time.time()
                    fps_frame_count = 0
                
                # Add info overlay
                info_frame = frame.copy()
                h, w = frame.shape[:2]
                
                # Add semi-transparent overlay for text
                overlay = info_frame.copy()
                cv2.rectangle(overlay, (0, 0), (w, 80), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.5, info_frame, 0.5, 0, info_frame)
                
                # Add text
                cv2.putText(info_frame, f"Gazebo Camera - UDP:{port}", (10, 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(info_frame, f"Frame: {frame_count} | FPS: {current_fps:.1f}", (10, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(info_frame, f"Size: {w}x{h} | Time: {elapsed:.1f}s", (10, 75),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                
                # Display frame
                cv2.imshow('Gazebo Camera Test', info_frame)
                
                # Show frame info every 30 frames
                if frame_count % 30 == 0:
                    print(f"Frame {frame_count:4d}: {w}x{h} @ {current_fps:.1f} FPS | Time: {elapsed:.1f}s", end='\r')
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("\n\n👋 Quit by user")
                break
            elif key == ord('s'):
                filename = f"gazebo_screenshot_{int(time.time())}.png"
                cv2.imwrite(filename, frame)
                print(f"\n📸 Screenshot saved: {filename}")
            elif key == ord(' '):
                paused = not paused
                print(f"\n{'⏸ Paused' if paused else '▶ Resumed'}")
        
        # Final statistics
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0
        
        print("\n\n" + "=" * 60)
        print("Test Results")
        print("=" * 60)
        print(f"Total frames:  {frame_count}")
        print(f"Duration:      {total_time:.2f} seconds")
        print(f"Average FPS:   {avg_fps:.2f}")
        print(f"Final FPS:     {current_fps:.2f}")
        
        frame_info = stream.get_frame_info()
        print(f"\nStream Info:")
        print(f"  Resolution:  {frame_info.get('width', 0)}x{frame_info.get('height', 0)}")
        print(f"  Source:      {frame_info.get('source', 'unknown')}")
        print(f"  Port:        {frame_info.get('port', port)}")
        
        if frame_count > 0:
            print("\n✅ SUCCESS: Gazebo camera stream working!")
            return True
        else:
            print("\n❌ FAILED: No frames received")
            return False
        
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrupted by user")
        return False
        
    finally:
        stream.stop()
        cv2.destroyAllWindows()


def test_gazebo_ros2(topic: str = '/camera', duration: int = 30):
    """
    Test Gazebo camera via ROS2.
    
    Args:
        topic: ROS2 camera topic name
        duration: Test duration in seconds
    """
    if not ROS2_AVAILABLE:
        print("❌ ROS2 not available")
        print("Install with: pip install rclpy sensor-msgs cv-bridge")
        return False
    
    print("=" * 60)
    print("Testing Gazebo Camera - ROS2 Method")
    print("=" * 60)
    print(f"\nTopic: {topic}")
    print("\nMake sure:")
    print("  1. Gazebo is running with camera-equipped drone model")
    print("  2. ROS2 bridge is running (ros2 run ros_gz_bridge parameter_bridge)")
    print(f"  3. Camera topic exists: ros2 topic list | grep camera")
    print("\nStarting in 3 seconds...")
    time.sleep(3)
    
    # Configuration
    config = {
        'gazebo_backend': 'ros2',
        'gazebo_topic': topic
    }
    
    # Create stream
    stream = VideoStreamGazeboROS2(config)
    
    # Start stream
    print("\n📹 Starting video stream...")
    if not stream.start():
        print("\n❌ Failed to start video stream")
        return False
    
    print("✓ Video stream started\n")
    
    # Read and display frames
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed > duration:
                print(f"\n⏱ Test duration ({duration}s) reached")
                break
            
            ret, frame, timestamp = stream.read()
            
            if not ret:
                print("⚠ Waiting for frames...", end='\r')
                time.sleep(0.1)
                continue
            
            frame_count += 1
            
            # Display frame
            cv2.imshow('Gazebo Camera (ROS2)', frame)
            
            if frame_count % 30 == 0:
                info = stream.get_frame_info()
                print(f"Frame {frame_count}: {frame.shape} @ {info['fps']:.1f} FPS")
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        print(f"\n✅ Successfully received {frame_count} frames")
        return frame_count > 0
        
    except KeyboardInterrupt:
        print("\n⚠ Test interrupted by user")
        return False
        
    finally:
        stream.stop()
        cv2.destroyAllWindows()


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description='Test Gazebo camera stream')
    parser.add_argument('--method', choices=['udp', 'ros2'], default='udp',
                       help='Stream method (default: udp)')
    parser.add_argument('--port', type=int, default=5600,
                       help='UDP port (default: 5600)')
    parser.add_argument('--topic', type=str, default='/camera',
                       help='ROS2 topic (default: /camera)')
    parser.add_argument('--duration', type=int, default=30,
                       help='Test duration in seconds (default: 30)')
    
    args = parser.parse_args()
    
    print("\n🚁 Gazebo Camera Stream Test\n")
    
    if args.method == 'udp':
        success = test_gazebo_udp(args.port, args.duration)
    else:
        success = test_gazebo_ros2(args.topic, args.duration)
    
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
