"""Video stream module for GStreamer/OpenCV video input."""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional
import time


class VideoStream:
    """
    Video stream handler for GStreamer pipeline input.
    
    Supports H.264/H.265 over UDP and other GStreamer-compatible sources.
    """
    
    def __init__(self, config: dict):
        """
        Initialize video stream.
        
        Args:
            config: Video configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.cap = None
        self.is_running = False
        self.frame_count = 0
        self.start_time = None
        
    def start(self) -> bool:
        """
        Start video stream.
        
        Returns:
            True if stream started successfully, False otherwise
        """
        try:
            backend = self.config.get('backend', 'gstreamer')
            
            if backend == 'gstreamer':
                pipeline = self.config.get('gstreamer_pipeline')
                
                # Use OpenCV's GStreamer backend
                self.logger.info(f"Opening GStreamer pipeline...")
                self.logger.info(f"Pipeline: {pipeline}")
                
                # Important: Set CAP_GSTREAMER backend explicitly
                self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
                
                if not self.cap.isOpened():
                    self.logger.error("Failed to open GStreamer pipeline with OpenCV")
                    self.logger.error("Make sure:")
                    self.logger.error("  1. OpenCV is built with GStreamer support")
                    self.logger.error("  2. GStreamer is installed and in PATH")
                    self.logger.error("  3. The RTSP stream is accessible")
                    return False
                
                # For GStreamer, don't try to set properties - they're defined in the pipeline
                self.logger.info("✓ GStreamer stream opened successfully with OpenCV backend")
                
            else:
                # Fallback to default camera
                camera_id = self.config.get('camera_id', 0)
                self.cap = cv2.VideoCapture(camera_id)
                self.logger.info(f"Initialized default camera: {camera_id}")
                
                if not self.cap.isOpened():
                    self.logger.error("Failed to open camera")
                    return False
                
                # Set video properties for regular cameras
                width = self.config.get('width', 1280)
                height = self.config.get('height', 720)
                fps = self.config.get('fps', 30)
                
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                self.cap.set(cv2.CAP_PROP_FPS, fps)
                
                self.logger.info(f"Camera properties set: {width}x{height} @ {fps}fps")
            
            self.is_running = True
            self.start_time = time.time()
            self.logger.info("Video stream started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting video stream: {e}", exc_info=True)
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
        """
        Get current frame information.
        
        Returns:
            Dictionary with frame statistics
        """
        if not self.is_running or self.start_time is None:
            return {}
        
        elapsed_time = time.time() - self.start_time
        fps = self.frame_count / elapsed_time if elapsed_time > 0 else 0
        
        return {
            'frame_count': self.frame_count,
            'elapsed_time': elapsed_time,
            'fps': fps,
            'width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if self.cap else 0,
            'height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if self.cap else 0
        }
    
    def stop(self):
        """Stop video stream and release resources."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.is_running = False
        self.logger.info("Video stream stopped")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
