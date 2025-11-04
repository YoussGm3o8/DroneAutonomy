"""
Gazebo Camera Stream Integration

Provides multiple methods to capture camera feed from Gazebo simulation:
1. ROS2 Bridge (requires ROS2)
2. Direct Gazebo Transport (requires gz-transport Python bindings)
3. GStreamer UDP (works with existing VideoStream)
"""

from __future__ import annotations
import cv2
import numpy as np
import logging
from typing import Tuple, Optional, TYPE_CHECKING
import time
import threading
import queue


# Try importing ROS2 dependencies
try:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import Image
    from cv_bridge import CvBridge
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False
    Node = object  # Dummy base class
    if TYPE_CHECKING:
        from sensor_msgs.msg import Image


class GazeboCameraROS2(Node):
    """
    Subscribe to Gazebo camera topic via ROS2 bridge.
    
    Usage:
        camera = GazeboCameraROS2('/camera')
        rclpy.spin(camera)
    """
    
    def __init__(self, topic: str = '/camera', queue_size: int = 10):
        """
        Initialize Gazebo camera stream via ROS2.
        
        Args:
            topic: ROS2 camera topic name (e.g., '/camera', '/drone/camera/image_raw')
            queue_size: Frame buffer size
        """
        if not ROS2_AVAILABLE:
            raise ImportError("ROS2 not available. Install: pip install rclpy sensor-msgs cv-bridge")
        
        super().__init__('gazebo_camera_stream')
        self.logger = logging.getLogger(__name__)
        
        self.bridge = CvBridge()
        self.frame_queue = queue.Queue(maxsize=queue_size)
        self.is_running = False
        self.frame_count = 0
        self.start_time = time.time()
        
        # Subscribe to camera topic
        self.subscription = self.create_subscription(
            Image,
            topic,
            self._camera_callback,
            10
        )
        
        self.logger.info(f"✓ Subscribed to Gazebo camera topic: {topic}")
    
    def _camera_callback(self, msg):
        """Handle incoming camera images."""
        try:
            # Convert ROS Image to OpenCV format
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            
            # Add to queue (drop old frames if full)
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            
            timestamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            self.frame_queue.put((cv_image, timestamp))
            self.frame_count += 1
            
        except Exception as e:
            self.logger.error(f"Error processing camera frame: {e}")
    
    def read(self) -> Tuple[bool, Optional[np.ndarray], float]:
        """
        Read latest frame from camera.
        
        Returns:
            Tuple of (success, frame, timestamp)
        """
        try:
            frame, timestamp = self.frame_queue.get(timeout=1.0)
            return True, frame, timestamp
        except queue.Empty:
            return False, None, 0.0
    
    def start(self) -> bool:
        """Start the camera stream."""
        self.is_running = True
        self.start_time = time.time()
        self.logger.info("Gazebo ROS2 camera stream started")
        return True
    
    def stop(self):
        """Stop the camera stream."""
        self.is_running = False
        self.logger.info("Gazebo ROS2 camera stream stopped")
    
    def get_frame_info(self) -> dict:
        """Get frame information."""
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        return {
            'frame_count': self.frame_count,
            'elapsed_time': elapsed,
            'fps': fps,
            'source': 'gazebo_ros2'
        }


class VideoStreamGazeboROS2:
    """
    Gazebo camera wrapper compatible with existing VideoStream interface.
    Uses ROS2 to subscribe to Gazebo camera topics.
    """
    
    def __init__(self, config: dict):
        """
        Initialize Gazebo video stream via ROS2.
        
        Args:
            config: Video configuration with 'gazebo_topic' key
        """
        if not ROS2_AVAILABLE:
            raise ImportError("ROS2 not available. Install: pip install rclpy sensor-msgs cv-bridge")
        
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.frame_count = 0
        
        # Initialize ROS2
        if not rclpy.ok():
            rclpy.init()
        
        # Create camera stream node
        topic = config.get('gazebo_topic', '/camera')
        self.camera_node = GazeboCameraROS2(topic)
        
        # Spin in separate thread
        self.spin_thread = threading.Thread(
            target=self._spin_ros,
            daemon=True
        )
    
    def _spin_ros(self):
        """Spin ROS2 node in separate thread."""
        try:
            rclpy.spin(self.camera_node)
        except Exception as e:
            self.logger.error(f"ROS2 spin error: {e}")
    
    def start(self) -> bool:
        """Start video stream."""
        try:
            self.camera_node.start()
            self.spin_thread.start()
            self.is_running = True
            self.logger.info("✓ Gazebo ROS2 video stream started successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start Gazebo ROS2 video stream: {e}")
            return False
    
    def read(self) -> Tuple[bool, Optional[np.ndarray], float]:
        """Read frame from stream."""
        if not self.is_running:
            return False, None, 0.0
        return self.camera_node.read()
    
    def get_frame_info(self) -> dict:
        """Get frame information."""
        info = self.camera_node.get_frame_info()
        info['topic'] = self.config.get('gazebo_topic', '/camera')
        return info
    
    def stop(self):
        """Stop video stream."""
        self.camera_node.stop()
        self.is_running = False
        # Don't shutdown rclpy here as it might be used by other nodes
        self.logger.info("Gazebo ROS2 video stream stopped")


class VideoStreamGazeboUDP:
    """
    Gazebo camera stream via UDP/GStreamer.
    
    This is the simplest method and works with existing VideoStream infrastructure.
    Requires Gazebo to be configured with GStreamer video plugin.
    """
    
    def __init__(self, config: dict):
        """
        Initialize Gazebo UDP video stream.
        
        Args:
            config: Video configuration with UDP port and GStreamer pipeline
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.cap = None
        self.is_running = False
        self.frame_count = 0
        self.start_time = None
    
    def start(self) -> bool:
        """Start video stream from Gazebo via UDP."""
        try:
            # Get configuration
            port = self.config.get('udp_port', 5600)
            width = self.config.get('width', 1280)
            height = self.config.get('height', 720)
            
            # Build GStreamer pipeline for Gazebo UDP stream
            pipeline = self.config.get('gstreamer_pipeline')
            
            if not pipeline:
                # Default pipeline for H.264 over UDP
                pipeline = (
                    f'udpsrc port={port} '
                    'caps="application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264" ! '
                    'rtph264depay ! '
                    'avdec_h264 ! '
                    'videoconvert ! '
                    'appsink max-buffers=1 drop=true'
                )
            
            self.logger.info(f"Opening Gazebo UDP stream on port {port}...")
            self.logger.info(f"Pipeline: {pipeline}")
            
            # Open GStreamer pipeline
            self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            
            if not self.cap.isOpened():
                self.logger.error("Failed to open Gazebo UDP stream")
                self.logger.error("Make sure:")
                self.logger.error("  1. Gazebo is running with camera sensor")
                self.logger.error("  2. GStreamer video plugin is enabled in Gazebo")
                self.logger.error(f"  3. UDP port {port} is not blocked by firewall")
                return False
            
            self.is_running = True
            self.start_time = time.time()
            self.logger.info(f"✓ Gazebo UDP stream opened successfully on port {port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting Gazebo UDP stream: {e}", exc_info=True)
            return False
    
    def read(self) -> Tuple[bool, Optional[np.ndarray], float]:
        """
        Read a frame from the video stream.
        
        Returns:
            Tuple of (success, frame, timestamp)
        """
        if not self.is_running or self.cap is None:
            return False, None, 0.0
        
        ret, frame = self.cap.read()
        timestamp = time.time()
        
        if ret:
            self.frame_count += 1
        
        return ret, frame, timestamp
    
    def get_frame_info(self) -> dict:
        """Get current frame information."""
        if not self.is_running or self.start_time is None:
            return {}
        
        elapsed_time = time.time() - self.start_time
        fps = self.frame_count / elapsed_time if elapsed_time > 0 else 0
        
        return {
            'frame_count': self.frame_count,
            'elapsed_time': elapsed_time,
            'fps': fps,
            'width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if self.cap else 0,
            'height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if self.cap else 0,
            'source': 'gazebo_udp',
            'port': self.config.get('udp_port', 5600)
        }
    
    def stop(self):
        """Stop video stream and release resources."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.is_running = False
        self.logger.info("Gazebo UDP video stream stopped")


# Factory function to create appropriate Gazebo camera stream
def create_gazebo_stream(config: dict):
    """
    Create appropriate Gazebo camera stream based on configuration.
    
    Args:
        config: Configuration dictionary with 'gazebo_backend' key
    
    Returns:
        VideoStream instance for Gazebo camera
    """
    backend = config.get('gazebo_backend', 'udp')
    
    if backend == 'ros2':
        return VideoStreamGazeboROS2(config)
    elif backend == 'udp':
        return VideoStreamGazeboUDP(config)
    else:
        raise ValueError(f"Unknown Gazebo backend: {backend}. Use 'ros2' or 'udp'")
