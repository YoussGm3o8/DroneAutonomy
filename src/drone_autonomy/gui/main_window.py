"""
Main Window for Drone Autonomy GUI

Integrates all components:
- Video display with overlays
- Task control panel
- Media gallery
- Results viewer
- Telemetry display
- Configuration management
"""

import sys
import os
import cv2
import numpy as np
import time
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QDockWidget, QMenuBar, QMenu, QToolBar, QStatusBar,
                             QMessageBox, QFileDialog, QSplitter, QTabWidget, QLabel, QApplication)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QIcon, QKeySequence

from .video_widget import VideoWidget
from .media_gallery import MediaGallery
from .results_viewer import ResultsViewer
from .telemetry_display import TelemetryDisplay
from .drone_control_panel import DroneControlPanel
from .settings_dialog import SettingsDialog
from .settings_manager import SettingsManager

# Import depth and detection modules
try:
    from drone_autonomy.depth import DepthEstimator
    from drone_autonomy.detection import YOLODetector
    from drone_autonomy.navigation import ObstacleAvoider
    DEPTH_AVAILABLE = True
except ImportError:
    DEPTH_AVAILABLE = False
    print("⚠ Warning: Depth/Detection/Navigation modules not available")

# Import MAVLink telemetry and avoidance controller
try:
    from drone_autonomy.mavlink.telemetry import MAVLinkTelemetry
    from drone_autonomy.navigation.mavlink_avoidance_controller import MAVLinkAvoidanceController
    MAVLINK_AVAILABLE = True
except ImportError:
    MAVLINK_AVAILABLE = False
    print("⚠ Warning: MAVLink telemetry/avoidance not available")


class VideoProcessingThread(QThread):
    """
    Background thread for video processing to keep GUI responsive
    """
    frame_ready = pyqtSignal(np.ndarray, np.ndarray, list, dict, str)  # frame, depth, detections, telemetry, state
    error_occurred = pyqtSignal(str)  # error message
    video_failsafe_triggered = pyqtSignal(str)  # failsafe status: "reconnecting", "landing", "recovered"
    
    def __init__(self):
        super().__init__()
        
        self.running = False
        self.pipeline = None
        self.video_source = None
        self.capture = None
        self.mavlink = None  # Reference to MAVLink telemetry for failsafe commands
        
        # MAVLink Avoidance Controller
        self.mavlink_avoidance_controller = None  # Will be initialized when MAVLink connects
        
        # Obstacle avoidance control
        self.obstacle_avoidance_enabled = False  # User must enable via GUI
        
        # Performance settings
        self.enable_depth = True  # Enable depth estimation
        self.enable_detection = True  # Enable object detection
        
        # Video failsafe state
        self.failsafe_active = False
        self.failsafe_start_time = None
        self.failsafe_reconnect_timeout = 10.0  # 10 seconds
        self.original_video_source_type = None
        self.original_video_source_path = None
        self.original_camera_idx = 0
        
        # Video recording
        self.is_recording = False
        self.video_writer = None
        self.recording_filename = None
        
        # Initialize depth estimator and detector for webcam mode
        self.depth_estimator = None
        self.detector = None
        self.obstacle_avoider = None
        if DEPTH_AVAILABLE:
            try:
                import torch
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                
                # Configure depth estimator (use saved settings or defaults)
                # Settings will be provided by MainWindow after initialization
                depth_config = {
                    'model': 'depth_anything_v2_vits_tensorrt_fp16',
                    'device': device,
                    'output_width': 518,  # Native resolution
                    'output_height': 518,
                    'use_metric_calibration': False
                }
                self.depth_estimator = DepthEstimator(depth_config)
                if self.depth_estimator.load_model():
                    print(f"✓ Depth estimator loaded ({device})")
                else:
                    print("⚠ Warning: Could not load depth estimator")
                    self.depth_estimator = None
                
                # Configure YOLO detector
                detector_config = {
                    'device': device,
                    'confidence_threshold': 0.5,
                    'nms_threshold': 0.4,
                    'classes': None,  # All classes
                    'imgsz': 640,
                    'model_path': 'yolov8n.pt'
                }
                self.detector = YOLODetector(detector_config)
                if self.detector.load_model():
                    print(f"✓ YOLO detector loaded ({device})")
                else:
                    print("⚠ Warning: Could not load YOLO detector")
                    self.detector = None
                
                # Configure obstacle avoider
                import logging
                avoider_config = {
                    'obstacle_distance_threshold': 3.0,
                    'critical_distance': 1.5,
                    'warning_distance': 2.5,
                    'min_clearance': 1.0,
                    'safety_margin': 0.5,
                    'num_zones_horizontal': 5,
                    'num_zones_vertical': 3,
                    'num_path_candidates': 7,
                    'path_horizon': 80,
                    'path_lateral_range': 150,
                    'show_zones': True,
                    'show_paths': True,
                    'show_obstacles': True,
                    'path_alpha': 0.65,
                    'target_priority': True,
                    'target_override_distance': 5.0
                }
                avoider_logger = logging.getLogger('obstacle_avoidance')
                self.obstacle_avoider = ObstacleAvoider(avoider_config, avoider_logger)
                print(f"✓ Obstacle avoider initialized")
                # Feature starts disabled until explicitly enabled via GUI toggle
                self.obstacle_avoider.set_feature_enabled(False)
                    
            except Exception as e:
                print(f"⚠ Warning: Could not initialize CV modules: {e}")
                import traceback
                traceback.print_exc()
                self.depth_estimator = None
                self.detector = None
                self.obstacle_avoider = None
        
    def set_pipeline(self, pipeline):
        """Set the processing pipeline"""
        self.pipeline = pipeline
    
    def set_mavlink(self, mavlink):
        """Set MAVLink telemetry reference for failsafe commands"""
        self.mavlink = mavlink
        
        # Initialize MAVLink Avoidance Controller if all components are ready
        if (mavlink and self.obstacle_avoider and 
            MAVLINK_AVAILABLE and hasattr(sys.modules[__name__], 'MAVLinkAvoidanceController')):
            try:
                import logging
                # Create avoidance controller config
                avoidance_config = {
                    'max_velocity': 2.0,  # m/s
                    'avoidance_velocity': 1.0,  # m/s
                    'emergency_distance': 1.0,  # m
                    'update_rate': 10,  # Hz
                    'lateral_gain': 1.5,
                    'enable_emergency_stop': True,
                    'min_altitude': 1.0,  # m
                    'max_altitude': 50.0  # m
                }
                
                avoider_logger = logging.getLogger('mavlink_avoidance_controller')
                self.mavlink_avoidance_controller = MAVLinkAvoidanceController(
                    mavlink, 
                    self.obstacle_avoider, 
                    avoidance_config,
                    avoider_logger
                )
                print("✓ MAVLink Avoidance Controller initialized")
            except Exception as e:
                print(f"⚠ Warning: Could not initialize MAVLink Avoidance Controller: {e}")
                import traceback
                traceback.print_exc()
                self.mavlink_avoidance_controller = None
    
    def set_performance_settings(self, enable_depth: bool, enable_detection: bool):
        """Update performance settings for depth estimation and detection"""
        self.enable_depth = enable_depth
        self.enable_detection = enable_detection
        print(f"Performance settings: depth={'ON' if enable_depth else 'OFF'}, detection={'ON' if enable_detection else 'OFF'}")
    
    def set_obstacle_avoidance_enabled(self, enabled: bool):
        """Enable or disable obstacle avoidance control"""
        self.obstacle_avoidance_enabled = enabled
        if self.obstacle_avoider:
            self.obstacle_avoider.set_feature_enabled(enabled)
        
        # Start or stop the MAVLink avoidance controller
        if self.mavlink_avoidance_controller:
            if enabled:
                if self.mavlink and self.mavlink.is_connected:
                    success = self.mavlink_avoidance_controller.start()
                    if success:
                        print("✓ MAVLink Avoidance Controller started")
                    else:
                        print("⚠ Failed to start MAVLink Avoidance Controller")
                else:
                    print("⚠ Cannot start avoidance: MAVLink not connected")
            else:
                self.mavlink_avoidance_controller.stop()
                print("✗ MAVLink Avoidance Controller stopped")
        
        print(f"{'✓ Enabled' if enabled else '✗ Disabled'} obstacle avoidance active control")
        
    def set_video_source(self, source_type: str, source_path: str = "", camera_idx: int = 0):
        """
        Set video source
        
        Args:
            source_type: 'webcam', 'rtsp', 'file', 'gazebo'
            source_path: Path or URL for rtsp/file/gazebo sources
            camera_idx: Camera index for webcam (default: 0)
        """
        import os
        import yaml
        
        # Store original source for failsafe reconnection
        self.original_video_source_type = source_type
        self.original_video_source_path = source_path
        self.original_camera_idx = camera_idx
        
        # Close existing capture
        if self.capture is not None:
            self.capture.release()
            self.capture = None
            
        try:
            if source_type == "webcam":
                # Use specified camera index
                self.capture = cv2.VideoCapture(camera_idx)
                if self.capture.isOpened():
                    print(f"✓ Webcam opened at index {camera_idx}")
                else:
                    raise RuntimeError(f"Failed to open camera at index {camera_idx}")
                    
            elif source_type == "rtsp":
                self.capture = cv2.VideoCapture(source_path, cv2.CAP_GSTREAMER)
                if not self.capture.isOpened():
                    raise RuntimeError(f"Failed to open RTSP stream: {source_path}")
                print(f"✓ RTSP stream opened: {source_path}")
                
            elif source_type == "file":
                self.capture = cv2.VideoCapture(source_path)
                if not self.capture.isOpened():
                    raise RuntimeError(f"Failed to open video file: {source_path}")
                print(f"✓ Video file opened: {source_path}")
                
            elif source_type == "gazebo":
                # Gazebo uses a GStreamer pipeline defined in its config file.
                # source_path is expected to be the path to gazebo_simulation.yaml
                if not (source_path and os.path.exists(source_path)):
                    raise RuntimeError(f"Gazebo config file not found: {source_path}")
                
                with open(source_path, 'r') as f:
                    gazebo_config = yaml.safe_load(f)
                
                video_config = gazebo_config.get('video', {})
                pipeline = video_config.get('gstreamer_pipeline')
                
                if not pipeline:
                    raise RuntimeError("gstreamer_pipeline not found in Gazebo config.")
                    
                print(f"✓ Using GStreamer pipeline from {source_path}")
                print(f"  Pipeline: {pipeline}")
                
                self.capture = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
                if not self.capture.isOpened():
                    raise RuntimeError("Failed to open GStreamer pipeline for Gazebo.")
                print("✓ Gazebo camera stream opened via GStreamer.")

            self.video_source = source_type
            
        except Exception as e:
            error_msg = f"Video source error: {e}"
            print(error_msg)
            self.error_occurred.emit(error_msg)
            self.capture = None
            
    def run(self):
        """Run video processing loop"""
        self.running = True
        
        while self.running:
            try:
                # Get frame from capture or pipeline
                if self.capture is not None:
                    ret, frame = self.capture.read()
                    if not ret:
                        # VIDEO FEED LOST - BUT DON'T IMMEDIATELY TRIGGER FAILSAFE
                        # Webcams can occasionally drop frames - need debouncing
                        print("⚠ Failed to read frame from video source")
                        
                        # Only trigger failsafe for REAL video sources (RTSP, file playback)
                        # NOT for webcams which naturally drop frames occasionally
                        if self.original_video_source_type and self.original_video_source_type != 'webcam':
                            # Handle video loss with reconnection attempts
                            reconnected = self._handle_video_loss_failsafe()
                            
                            if not reconnected:
                                # Still no video, sleep and retry
                                self.msleep(500)  # Wait 500ms before next attempt
                                continue
                            else:
                                # Reconnected successfully, continue processing
                                continue
                        else:
                            # Webcam frame drop - just skip this frame and continue
                            self.msleep(30)  # Normal frame rate
                            continue
                    
                    # Video frame received successfully
                    # If failsafe was active and we got a frame, consider it recovered
                    if self.failsafe_active:
                        print("✓ Video feed recovered")
                        self.failsafe_active = False
                        self.failsafe_start_time = None
                        self.video_failsafe_triggered.emit("recovered")
                    
                    # Convert BGR to RGB
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Process with pipeline if available
                    if self.pipeline:
                        depth_map, detections = self.pipeline.process_frame(frame)
                        telemetry = self.pipeline.get_telemetry() if hasattr(self.pipeline, 'get_telemetry') else {}
                        state_info = self.pipeline.get_state() if hasattr(self.pipeline, 'get_state') else ""
                    else:
                        # No pipeline - use standalone depth estimator and detector
                        h, w = frame.shape[:2]
                        
                        # Run depth estimation
                        if self.depth_estimator:
                            try:
                                depth_map, inference_time = self.depth_estimator.estimate_depth(frame)
                                if depth_map is None:
                                    h, w = frame.shape[:2]
                                    depth_map = np.zeros((h, w), dtype=np.float32)
                            except Exception as e:
                                print(f"Depth estimation error: {e}")
                                h, w = frame.shape[:2]
                                depth_map = np.zeros((h, w), dtype=np.float32)
                        else:
                            h, w = frame.shape[:2]
                            depth_map = np.zeros((h, w), dtype=np.float32)
                        
                        # Run obstacle detection if depth map available
                        if self.obstacle_avoider and depth_map is not None and depth_map.size > 0:
                            try:
                                # Use MAVLink Avoidance Controller if available and enabled
                                if (self.mavlink_avoidance_controller and 
                                    self.obstacle_avoidance_enabled and
                                    self.mavlink and self.mavlink.is_connected):
                                    
                                    # Update MAVLink avoidance controller with depth map
                                    # The controller handles obstacle detection, path planning,
                                    # and MAVLink command execution automatically
                                    avoidance_status = self.mavlink_avoidance_controller.update(
                                        depth_map=depth_map,
                                        target_position=(w//2, h - 20)  # Default: center bottom
                                    )
                                    
                                    # Log significant events
                                    if avoidance_status.get('avoiding', False):
                                        num_obstacles = avoidance_status.get('num_obstacles', 0)
                                        print(f"🛡️ Avoiding {num_obstacles} obstacle(s)")
                                    
                                    if avoidance_status.get('emergency', False):
                                        obstacle_dist = avoidance_status.get('obstacle_distance', 0)
                                        print(f"🚨 EMERGENCY STOP: Critical obstacle at {obstacle_dist:.2f}m")
                                        
                                else:
                                    # Fallback: Basic obstacle detection for visualization only
                                    # (no MAVLink commands sent)
                                    obstacles = self.obstacle_avoider.detect_obstacles(depth_map)
                                    
                                    # Generate path candidates for visualization
                                    if obstacles:
                                        paths = self.obstacle_avoider.generate_path_candidates(
                                            frame_shape=(h, w),
                                            current_target=(w//2, h - 20)  # Default: center bottom
                                        )
                                        
                            except Exception as e:
                                print(f"Obstacle avoidance error: {e}")
                                import traceback
                                traceback.print_exc()
                        
                        # Run object detection (only if enabled in settings)
                        detections = []
                        if self.enable_detection and self.detector:
                            try:
                                detections = self.detector.detect(frame)
                                if detections is None:
                                    detections = []
                            except Exception as e:
                                print(f"Detection error: {e}")
                                detections = []
                        
                        telemetry = {}
                        state_info = ""
                        
                    # Emit processed frame
                    self.frame_ready.emit(frame, depth_map, detections, telemetry, state_info)
                    
                    # Write frame to video if recording
                    if self.is_recording and self.video_writer is not None:
                        # Convert RGB back to BGR for video writer
                        bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        self.video_writer.write(bgr_frame)
                    
                elif self.pipeline:
                    # Use pipeline's own frame source
                    frame, depth_map, detections = self.pipeline.process_frame()
                    telemetry = self.pipeline.get_telemetry() if hasattr(self.pipeline, 'get_telemetry') else {}
                    state_info = self.pipeline.get_state() if hasattr(self.pipeline, 'get_state') else ""
                    self.frame_ready.emit(frame, depth_map, detections, telemetry, state_info)
                    
            except Exception as e:
                error_msg = f"Video processing error: {e}"
                print(error_msg)
                self.error_occurred.emit(error_msg)
                
            # No sleep - run at maximum speed for depth estimation
            # The depth estimator inference time (23-38ms) naturally limits FPS to 25-42 fps
    
    def start_recording(self, filename: str, frame_size: tuple, fps: float = 30.0):
        """Start video recording"""
        try:
            import os
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(filename, fourcc, fps, frame_size)
            
            if self.video_writer.isOpened():
                self.is_recording = True
                self.recording_filename = filename
                print(f"✓ Recording started: {filename}")
                return True
            else:
                print(f"✗ Failed to open video writer: {filename}")
                return False
                
        except Exception as e:
            print(f"✗ Recording start error: {e}")
            return False
    
    def stop_recording(self):
        """Stop video recording"""
        try:
            if self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None
                self.is_recording = False
                filename = self.recording_filename
                self.recording_filename = None
                print(f"✓ Recording stopped: {filename}")
                return filename
            return None
        except Exception as e:
            print(f"✗ Recording stop error: {e}")
            return None
    
    def _attempt_video_reconnect(self) -> bool:
        """
        Attempt to reconnect to the video source.
        
        Returns:
            True if reconnection successful, False otherwise
        """
        if self.original_video_source_type is None:
            return False
        
        try:
            print(f"🔄 Attempting to reconnect to {self.original_video_source_type}...")
            
            # Close existing capture
            if self.capture is not None:
                self.capture.release()
                self.capture = None
            
            # Attempt to reopen
            if self.original_video_source_type == "webcam":
                self.capture = cv2.VideoCapture(self.original_camera_idx)
            elif self.original_video_source_type == "rtsp":
                self.capture = cv2.VideoCapture(self.original_video_source_path, cv2.CAP_GSTREAMER)
            elif self.original_video_source_type == "file":
                self.capture = cv2.VideoCapture(self.original_video_source_path)
            elif self.original_video_source_type == "gazebo":
                self.set_video_source("gazebo", self.original_video_source_path)
                # set_video_source will create the capture object
            
            # Test if capture opened and can read a frame
            if self.capture and self.capture.isOpened():
                ret, test_frame = self.capture.read()
                if ret and test_frame is not None:
                    print(f"✓ Video reconnection successful!")
                    return True
                else:
                    print(f"✗ Capture opened but cannot read frames")
                    if self.capture:
                        self.capture.release()
                        self.capture = None
                    return False
            else:
                print(f"✗ Failed to reopen video source")
                return False
                
        except Exception as e:
            print(f"✗ Reconnection error: {e}")
            if self.capture:
                self.capture.release()
                self.capture = None
            return False
    
    def _handle_video_loss_failsafe(self):
        """
        Handle video loss with safety protocol:
        1. Enter LOITER mode (pause movement)
        2. Attempt reconnection for 10 seconds
        3. If unsuccessful, command AUTO LAND
        """
        import time
        
        if not self.failsafe_active:
            # First detection of video loss
            self.failsafe_active = True
            self.failsafe_start_time = time.time()
            print("🚨 VIDEO FEED LOST - Activating failsafe protocol")
            self.video_failsafe_triggered.emit("reconnecting")
            
            # Command drone to LOITER mode (pause movement)
            if self.mavlink and self.mavlink.is_connected:
                try:
                    # Send MAVLink command to change mode to LOITER (mode 5)
                    self.mavlink.connection.mav.command_long_send(
                        self.mavlink.connection.target_system,
                        self.mavlink.connection.target_component,
                        400,  # MAV_CMD_DO_SET_MODE
                        0,    # confirmation
                        1,    # MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
                        5,    # LOITER mode
                        0, 0, 0, 0, 0  # unused parameters
                    )
                    print("🔄 Drone commanded to LOITER mode")
                except Exception as e:
                    print(f"⚠ Failed to send LOITER command: {e}")
        
        # Check if still in failsafe
        elapsed = time.time() - self.failsafe_start_time
        
        if elapsed < self.failsafe_reconnect_timeout:
            # Still within reconnection window - attempt reconnect
            if self._attempt_video_reconnect():
                # Reconnection successful!
                print(f"✓ Video feed recovered after {elapsed:.1f}s")
                self.failsafe_active = False
                self.failsafe_start_time = None
                self.failsafe_land_commanded = False  # Reset land command flag
                self.video_failsafe_triggered.emit("recovered")
                return True
            else:
                # Still no video, keep waiting
                remaining = self.failsafe_reconnect_timeout - elapsed
                print(f"⏳ Video reconnection in progress... {remaining:.1f}s remaining")
                return False
        else:
            # Timeout reached - initiate auto land (only once)
            if not hasattr(self, 'failsafe_land_commanded') or not self.failsafe_land_commanded:
                print("🚨 VIDEO RECONNECTION FAILED - Commanding AUTO LAND")
                self.video_failsafe_triggered.emit("landing")
                
                # Command drone to LAND mode
                if self.mavlink and self.mavlink.is_connected:
                    try:
                        self.mavlink.connection.mav.command_long_send(
                            self.mavlink.connection.target_system,
                            self.mavlink.connection.target_component,
                            400,  # MAV_CMD_DO_SET_MODE
                            0,    # confirmation
                            1,    # MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
                            9,    # LAND mode
                            0, 0, 0, 0, 0  # unused parameters
                        )
                        print("🛬 Drone commanded to AUTO LAND")
                    except Exception as e:
                        print(f"⚠ Failed to send LAND command: {e}")
                
                # Mark that we've commanded landing to avoid repeated commands
                self.failsafe_land_commanded = True
            
            # Keep failsafe active (don't reset)
            return False
            
    def stop(self):
        """Stop video processing"""
        # Stop recording if active
        if self.is_recording:
            self.stop_recording()
            
        self.running = False
        if self.capture is not None:
            self.capture.release()
        self.wait()


class MainWindow(QMainWindow):
    """
    Main application window
    """
    
    def __init__(self):
        super().__init__()
        
        self.pipeline = None
        self.task_manager = None
        self.video_thread = VideoProcessingThread()
        self.mavlink = None  # MAVLink telemetry connection
        self.connection_thread = None  # Track MAVLink connection thread
        self.settings_manager = SettingsManager()  # Persistent settings manager
        
        # Load saved settings
        self.saved_settings = self.settings_manager.load_settings()
        
        self.init_ui()
        self.create_menus()
        self.create_toolbar()
        self.create_statusbar()
        
        # Connect signals
        self.video_thread.frame_ready.connect(self._on_frame_ready)
        self.video_thread.error_occurred.connect(self._on_video_error)
        self.video_thread.video_failsafe_triggered.connect(self._on_video_failsafe)
        
        # Create MAVLink telemetry polling timer
        self.mavlink_timer = QTimer()
        self.mavlink_timer.timeout.connect(self._update_mavlink_telemetry)
        self.mavlink_timer.setInterval(100)  # Poll at 10Hz
        
        self.setWindowTitle("Drone Autonomy Control System")
        
        # Restore window geometry from settings
        window_settings = self.saved_settings.get('window', {})
        self.setGeometry(
            window_settings.get('x', 100),
            window_settings.get('y', 100),
            window_settings.get('width', 1600),
            window_settings.get('height', 900)
        )
        
        # Apply saved depth settings to video thread
        self._apply_saved_depth_settings()
        
        # Apply saved performance settings
        self._apply_saved_performance_settings()
        
    def _apply_saved_depth_settings(self):
        """Apply saved depth estimator settings after initialization"""
        if 'depth' in self.saved_settings and DEPTH_AVAILABLE:
            depth_config = self.saved_settings['depth']
            
            # Check if we need to reload with different model
            if self.video_thread.depth_estimator:
                saved_model = depth_config.get('model', 'depth_anything_v2_vits_tensorrt_fp16')
                current_model = self.video_thread.depth_estimator.model_type
                
                # Extract model type from saved model name
                saved_model_type = 'vitb' if 'vitb' in saved_model else 'vits'
                
                if current_model != saved_model_type:
                    # Need to reload with different model
                    print(f"Loading saved depth model: {saved_model}")
                    import torch
                    new_config = {
                        'model': saved_model,
                        'device': depth_config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu'),
                        'output_width': depth_config.get('output_width', 518),
                        'output_height': depth_config.get('output_height', 518),
                        'use_metric_calibration': False
                    }
                    new_estimator = DepthEstimator(new_config)
                    if new_estimator.load_model():
                        self.video_thread.depth_estimator = new_estimator
                        print(f"✓ Depth model loaded from settings: {saved_model_type}")
                else:
                    # Same model, just update output resolution
                    output_width = depth_config.get('output_width', 518)
                    output_height = depth_config.get('output_height', 518)
                    if hasattr(self.video_thread.depth_estimator.model, 'output_width'):
                        self.video_thread.depth_estimator.model.output_width = output_width
                        self.video_thread.depth_estimator.model.output_height = output_height
                        print(f"✓ Depth output resolution from settings: {output_width}×{output_height}")
    
    def _apply_saved_performance_settings(self):
        """Apply saved performance settings to video thread"""
        if 'performance' in self.saved_settings:
            perf_config = self.saved_settings['performance']
            enable_depth = perf_config.get('enable_depth', True)
            enable_detection = perf_config.get('enable_detection', True)
            self.video_thread.set_performance_settings(enable_depth, enable_detection)
            print(f"✓ Applied performance settings: depth={enable_depth}, detection={enable_detection}")
        
    def init_ui(self):
        """Initialize UI components with resizable and collapsible panels"""
        from PyQt6.QtWidgets import QScrollArea
        
        # Central widget with main layout
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create main horizontal splitter for resizable panels
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setChildrenCollapsible(False)  # Prevent complete collapse
        
        # Left panel: Video and task control
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(2, 2, 2, 2)
        
        # Create vertical splitter for video and tabs (resizable)
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        left_splitter.setChildrenCollapsible(False)
        
        # Video widget
        self.video_widget = VideoWidget()
        self.video_widget.setMinimumHeight(200)  # Minimum height when resized
        
        # Connect obstacle avoider to video widget for visualization
        if self.video_thread.obstacle_avoider is not None:
            self.video_widget.obstacle_avoider = self.video_thread.obstacle_avoider
            print("✓ Obstacle avoider connected to video widget")
        
        left_splitter.addWidget(self.video_widget)
        
        # Control tabs with scroll area
        task_tabs = QTabWidget()
        task_tabs.setMinimumHeight(150)  # Minimum height when resized
        
        # Drone control panel in scroll area
        drone_control_scroll = QScrollArea()
        drone_control_scroll.setWidgetResizable(True)
        drone_control_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        drone_control_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.drone_control = DroneControlPanel()
        self.drone_control.obstacle_avoidance_toggled.connect(self._on_obstacle_avoidance_toggled)
        drone_control_scroll.setWidget(self.drone_control)
        task_tabs.addTab(drone_control_scroll, "🎮 Drone Controls")
        
        # Media gallery in scroll area
        media_gallery_scroll = QScrollArea()
        media_gallery_scroll.setWidgetResizable(True)
        media_gallery_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        media_gallery_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.media_gallery = MediaGallery()
        self.media_gallery.video_play_requested.connect(self._on_video_play)
        
        media_gallery_scroll.setWidget(self.media_gallery)
        task_tabs.addTab(media_gallery_scroll, "📁 Media")
        
        left_splitter.addWidget(task_tabs)
        
        # Set initial sizes for left splitter (60% video, 40% tabs)
        left_splitter.setSizes([600, 400])
        left_splitter.setStretchFactor(0, 3)
        left_splitter.setStretchFactor(1, 2)
        
        left_layout.addWidget(left_splitter)
        left_panel.setLayout(left_layout)
        
        # Add left panel to main splitter
        main_splitter.addWidget(left_panel)
        
        # Right panel: Results and telemetry with scroll areas
        right_panel = QWidget()
        right_panel.setMinimumWidth(250)  # Minimum width when resized
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(2, 2, 2, 2)
        
        # Create vertical splitter for results and telemetry (resizable)
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setChildrenCollapsible(False)
        
        # Results viewer in scroll area
        results_scroll = QScrollArea()
        results_scroll.setWidgetResizable(True)
        results_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        results_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        results_scroll.setMinimumHeight(150)
        
        self.results_viewer = ResultsViewer()
        results_scroll.setWidget(self.results_viewer)
        right_splitter.addWidget(results_scroll)
        
        # Telemetry display in scroll area
        telemetry_scroll = QScrollArea()
        telemetry_scroll.setWidgetResizable(True)
        telemetry_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        telemetry_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        telemetry_scroll.setMinimumHeight(150)
        
        self.telemetry_display = TelemetryDisplay()
        telemetry_scroll.setWidget(self.telemetry_display)
        right_splitter.addWidget(telemetry_scroll)
        
        # Set initial sizes for right splitter (60% results, 40% telemetry)
        right_splitter.setSizes([600, 400])
        right_splitter.setStretchFactor(0, 2)
        right_splitter.setStretchFactor(1, 1)
        
        right_layout.addWidget(right_splitter)
        right_panel.setLayout(right_layout)
        
        # Add right panel to main splitter
        main_splitter.addWidget(right_panel)
        
        # Set initial sizes for main splitter (70% left, 30% right)
        main_splitter.setSizes([1100, 500])
        main_splitter.setStretchFactor(0, 7)
        main_splitter.setStretchFactor(1, 3)
        
        # Store splitter references for save/restore
        self.main_splitter = main_splitter
        self.left_splitter = left_splitter
        self.right_splitter = right_splitter
        
        main_layout.addWidget(main_splitter)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Apply saved display settings and splitter states
        self._apply_saved_display_settings()
    
    def _apply_saved_display_settings(self):
        """Apply saved display settings on startup"""
        display_settings = self.saved_settings.get('display', {})
        
        # Apply FPS counter setting
        show_fps = display_settings.get('show_fps', False)
        self.video_widget.set_fps_display(show_fps)
        
        # Apply default view mode
        default_view = display_settings.get('default_view', 'Full Overlay')
        if hasattr(self.video_widget, 'viz_mode_combo'):
            index = self.video_widget.viz_mode_combo.findText(default_view)
            if index >= 0:
                self.video_widget.viz_mode_combo.setCurrentIndex(index)
        
        # Apply depth opacity
        depth_opacity = display_settings.get('depth_opacity', 50)
        if hasattr(self.video_widget, 'depth_opacity_slider'):
            self.video_widget.depth_opacity_slider.setValue(depth_opacity)
        
        # Restore splitter states
        splitter_settings = self.saved_settings.get('splitters', {})
        if 'main' in splitter_settings:
            self.main_splitter.restoreState(bytes.fromhex(splitter_settings['main']))
        if 'left' in splitter_settings:
            self.left_splitter.restoreState(bytes.fromhex(splitter_settings['left']))
        if 'right' in splitter_settings:
            self.right_splitter.restoreState(bytes.fromhex(splitter_settings['right']))
        
    def create_menus(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        open_config_action = QAction("&Open Configuration...", self)
        open_config_action.setShortcut(QKeySequence.StandardKey.Open)
        open_config_action.triggered.connect(self._open_configuration)
        file_menu.addAction(open_config_action)
        
        save_config_action = QAction("&Save Configuration...", self)
        save_config_action.setShortcut(QKeySequence.StandardKey.Save)
        save_config_action.triggered.connect(self._save_configuration)
        file_menu.addAction(save_config_action)
        
        file_menu.addSeparator()
        
        export_results_action = QAction("&Export Results...", self)
        export_results_action.triggered.connect(self._export_results)
        file_menu.addAction(export_results_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        fullscreen_action = QAction("&Fullscreen", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.setCheckable(True)
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
        view_menu.addSeparator()
        
        # Panel visibility toggles
        self.toggle_tasks_action = QAction("Show &Task Panel", self)
        self.toggle_tasks_action.setCheckable(True)
        self.toggle_tasks_action.setChecked(True)
        self.toggle_tasks_action.setShortcut("Ctrl+1")
        self.toggle_tasks_action.triggered.connect(self._toggle_tasks_panel)
        view_menu.addAction(self.toggle_tasks_action)
        
        self.toggle_results_action = QAction("Show &Results Panel", self)
        self.toggle_results_action.setCheckable(True)
        self.toggle_results_action.setChecked(True)
        self.toggle_results_action.setShortcut("Ctrl+2")
        self.toggle_results_action.triggered.connect(self._toggle_results_panel)
        view_menu.addAction(self.toggle_results_action)
        
        self.toggle_telemetry_action = QAction("Show Tele&metry Panel", self)
        self.toggle_telemetry_action.setCheckable(True)
        self.toggle_telemetry_action.setChecked(True)
        self.toggle_telemetry_action.setShortcut("Ctrl+3")
        self.toggle_telemetry_action.triggered.connect(self._toggle_telemetry_panel)
        view_menu.addAction(self.toggle_telemetry_action)
        
        view_menu.addSeparator()
        
        # Quick layout presets
        focus_video_action = QAction("&Focus Video (Hide Panels)", self)
        focus_video_action.setShortcut("F")
        focus_video_action.triggered.connect(self._focus_video_mode)
        view_menu.addAction(focus_video_action)
        
        restore_layout_action = QAction("&Restore Default Layout", self)
        restore_layout_action.setShortcut("Ctrl+R")
        restore_layout_action.triggered.connect(self._restore_default_layout)
        view_menu.addAction(restore_layout_action)
        
        view_menu.addSeparator()
        
        refresh_gallery_action = QAction("Re&fresh Media Gallery", self)
        refresh_gallery_action.setShortcut("F5")
        refresh_gallery_action.triggered.connect(self.media_gallery.refresh_gallery)
        view_menu.addAction(refresh_gallery_action)
        
        clear_results_action = QAction("&Clear Results", self)
        clear_results_action.triggered.connect(self.results_viewer.clear_all)
        view_menu.addAction(clear_results_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        settings_action = QAction("⚙️ &Settings...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._open_settings)
        tools_menu.addAction(settings_action)
        
        tools_menu.addSeparator()
        
        # Obstacle avoidance control
        self.obstacle_avoidance_action = QAction("🛡️ Enable &Obstacle Avoidance", self)
        self.obstacle_avoidance_action.setCheckable(True)
        self.obstacle_avoidance_action.setChecked(False)
        self.obstacle_avoidance_action.setStatusTip("Enable active obstacle avoidance control (GUIDED mode only)")
        self.obstacle_avoidance_action.triggered.connect(self._toggle_obstacle_avoidance)
        tools_menu.addAction(self.obstacle_avoidance_action)
        
        tools_menu.addSeparator()
        
        camera_calibration_action = QAction("&Camera Calibration...", self)
        camera_calibration_action.triggered.connect(self._open_camera_calibration)
        tools_menu.addAction(camera_calibration_action)
        
        diagnostics_action = QAction("&Run Diagnostics", self)
        diagnostics_action.triggered.connect(self._run_diagnostics)
        tools_menu.addAction(diagnostics_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        documentation_action = QAction("&Documentation", self)
        documentation_action.setShortcut("F1")
        documentation_action.triggered.connect(self._open_documentation)
        help_menu.addAction(documentation_action)
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
    def create_toolbar(self):
        """Create toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Video source actions
        webcam_action = QAction("📷 Webcam", self)
        webcam_action.triggered.connect(lambda: self._set_video_source("webcam"))
        toolbar.addAction(webcam_action)
        
        rtsp_action = QAction("📡 RTSP Stream", self)
        rtsp_action.triggered.connect(lambda: self._set_video_source("rtsp"))
        toolbar.addAction(rtsp_action)
        
        file_action = QAction("📁 Video File", self)
        file_action.triggered.connect(lambda: self._set_video_source("file"))
        toolbar.addAction(file_action)
        
        # Gazebo simulation action
        gazebo_action = QAction("🎮 Gazebo Simulation", self)
        gazebo_action.setToolTip("Connect to Gazebo simulation camera (WSL or local)")
        gazebo_action.triggered.connect(lambda: self._set_video_source("gazebo"))
        toolbar.addAction(gazebo_action)
        
        toolbar.addSeparator()
        
        # Recording actions
        self.record_action = QAction("⏺ Record", self)
        self.record_action.setCheckable(True)
        self.record_action.triggered.connect(self._toggle_recording)
        toolbar.addAction(self.record_action)
        
        screenshot_action = QAction("📸 Screenshot", self)
        screenshot_action.setShortcut("Ctrl+S")
        screenshot_action.triggered.connect(self.video_widget._capture_screenshot)
        toolbar.addAction(screenshot_action)
        
        toolbar.addSeparator()
        
        # Connection actions
        self.connect_action = QAction("🔌 Connect", self)
        self.connect_action.triggered.connect(self._connect_to_drone)
        toolbar.addAction(self.connect_action)
        
    def create_statusbar(self):
        """Create status bar"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Status labels
        self.status_label = QLabel("Ready")
        self.statusbar.addWidget(self.status_label)
        
        self.statusbar.addPermanentWidget(QLabel("FPS:"))
        self.fps_label = QLabel("0")
        self.statusbar.addPermanentWidget(self.fps_label)
        
        self.statusbar.addPermanentWidget(QLabel("Latency:"))
        self.latency_label = QLabel("0 ms")
        self.statusbar.addPermanentWidget(self.latency_label)
        
    def _on_frame_ready(self, frame, depth_map, detections, telemetry, state_info):
        """Handle processed frame from video thread"""
        # Update video widget
        self.video_widget.update_frame(frame, depth_map, detections, telemetry, state_info)
        
        # DO NOT update telemetry display here - it's handled by _update_mavlink_telemetry timer
        # This prevents flickering from dual update sources
        
        # Calculate FPS (simple estimate)
        # In production, implement proper FPS calculation
        self.fps_label.setText("30")
        
    def _on_video_error(self, error_msg: str):
        """Handle video processing errors"""
        self.results_viewer.add_error(error_msg)
        QMessageBox.warning(self, "Video Error", error_msg)
    
    def _on_video_failsafe(self, status: str):
        """
        Handle video feed failsafe events.
        
        Args:
            status: "reconnecting", "landing", or "recovered"
        """
        if status == "reconnecting":
            self.results_viewer.add_log("🚨 VIDEO FEED LOST - Entering LOITER mode", "ERROR")
            self.results_viewer.add_log("🔄 Attempting video reconnection (10s timeout)...", "WARNING")
            self.statusBar().showMessage("⚠ VIDEO FEED LOST - Reconnecting...", 10000)
            
        elif status == "landing":
            self.results_viewer.add_log("🚨 VIDEO RECONNECTION FAILED - Commanding AUTO LAND", "ERROR")
            self.results_viewer.add_log("🛬 Drone entering emergency landing procedure", "ERROR")
            self.statusBar().showMessage("🚨 EMERGENCY AUTO LAND INITIATED", 30000)
            
            # Show critical alert dialog
            QMessageBox.critical(
                self,
                "Emergency Auto Land",
                "VIDEO FEED LOST!\n\n"
                "Reconnection attempts failed after 10 seconds.\n"
                "Drone has been commanded to AUTO LAND for safety.\n\n"
                "Please ensure landing area is clear!"
            )
            
        elif status == "recovered":
            self.results_viewer.add_log("✓ Video feed recovered - Resuming normal operations", "SUCCESS")
            self.statusBar().showMessage("✓ Video feed restored", 3000)
    
    def _update_mavlink_telemetry(self):
        """Poll and update MAVLink telemetry data"""
        if self.mavlink is None or not self.mavlink.is_connected:
            return
        
        try:
            # Read FRESH telemetry from MAVLink in flattened format for GUI display
            # This reads the latest messages and returns a flat dictionary
            telemetry = self.mavlink.get_flattened_telemetry()
            
            # DEBUG: Log what we received
            if not telemetry:
                print(f"[MainWindow] EMPTY telemetry dict received - skipping update")
                return  # No data this cycle, keep displaying last known good state
            
            # DEBUG: Log the armed and mode values we're about to send
            armed = telemetry.get('armed', None)
            mode = telemetry.get('flight_mode', None)
            print(f"[MainWindow] Telemetry received: armed={armed}, mode={mode}")
            
            # We have valid telemetry - update displays
            # Always update telemetry display with latest data
            self.telemetry_display.update_telemetry(telemetry)
            
            # Update drone control panel status
            armed_value = telemetry.get('armed', False)
            mode_value = telemetry.get('flight_mode', 'UNKNOWN')
            print(f"[MainWindow] Calling update_status: armed={armed_value}, mode={mode_value}")
            self.drone_control.update_status(armed_value, mode_value)
            
            # Update status bar with current mode
            if 'flight_mode' in telemetry:
                armed_status = "ARMED" if armed_value else "DISARMED"
                self.statusBar().showMessage(f"Drone: {mode_value} | {armed_status}")
        
        except Exception as e:
            print(f"[MainWindow] MAVLink telemetry error: {e}")
            import traceback
            traceback.print_exc()

    def _log_mavlink_action(self, message: str, level: str = "INFO"):
        """Display MAVLink command activity in the GUI logs."""
        if self.results_viewer:
            self.results_viewer.add_log(f"[MAVLINK] {message}", level)
        

    
    def _on_obstacle_avoidance_toggled(self, enabled: bool):
        """Handle obstacle avoidance toggle from drone control panel"""
        # Sync with menu action
        self.obstacle_avoidance_action.setChecked(enabled)
        
        if enabled:
            self.results_viewer.add_log("🛡️ Obstacle avoidance ENABLED", "SUCCESS")
            self.video_thread.set_obstacle_avoidance_enabled(True)
            self.statusBar().showMessage("🛡️ Obstacle Avoidance: ACTIVE", 5000)
        else:
            self.results_viewer.add_log("🛡️ Obstacle avoidance DISABLED", "WARNING")
            self.video_thread.set_obstacle_avoidance_enabled(False)
            self.statusBar().showMessage("Obstacle Avoidance: INACTIVE", 5000)
        
    def _on_video_play(self, file_path: str):
        """Handle video playback request"""
        self.results_viewer.add_log(f"Playing video: {file_path}", "INFO")
        # TODO: Implement video playback in video widget
        
    def _set_video_source(self, source_type: str):
        """Set video source"""
        if source_type == "webcam":
            # Detect available cameras
            available_cameras = []
            for idx in range(10):  # Check indices 0-9
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    # Get camera name/info
                    backend = cap.getBackendName()
                    available_cameras.append((idx, f"Camera {idx} ({backend})"))
                    cap.release()
            
            if not available_cameras:
                self.results_viewer.add_log("✗ No cameras detected", "ERROR")
                return
            
            # Show camera selection dialog
            from PyQt6.QtWidgets import QInputDialog
            camera_options = [f"{name}" for idx, name in available_cameras]
            camera_name, ok = QInputDialog.getItem(
                self, 
                "Select Camera", 
                "Available cameras:",
                camera_options,
                0,
                False
            )
            
            if not ok:
                return
            
            # Extract camera index from selection
            selected_idx = camera_options.index(camera_name)
            camera_idx = available_cameras[selected_idx][0]
            
            self.results_viewer.add_log(f"Switching to {camera_name}...", "INFO")
            
            # Stop current processing
            if self.video_thread.isRunning():
                self.video_thread.stop()
                
            # Set webcam source with specific index
            self.video_thread.set_video_source("webcam", camera_idx=camera_idx)
            
            # Start processing
            if not self.video_thread.isRunning():
                self.video_thread.start()
                
            self.results_viewer.add_log(f"✓ {camera_name} active", "INFO")
            self.statusBar().showMessage(f"Video source: {camera_name}")
            
        elif source_type == "rtsp":
            from PyQt6.QtWidgets import QInputDialog
            url, ok = QInputDialog.getText(self, "RTSP Stream", "Enter RTSP URL:", text="rtsp://192.168.1.231:8554/1")
            if ok and url:
                self.results_viewer.add_log(f"Connecting to RTSP: {url}", "INFO")
                
                # Stop current processing
                if self.video_thread.isRunning():
                    self.video_thread.stop()
                    
                # Set RTSP source
                self.video_thread.set_video_source("rtsp", url)
                
                # Start processing
                if not self.video_thread.isRunning():
                    self.video_thread.start()
                    
                self.results_viewer.add_log("✓ RTSP stream active", "INFO")
                self.statusBar().showMessage(f"Video source: RTSP ({url})")
                
        elif source_type == "file":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mkv)"
            )
            if file_path:
                self.results_viewer.add_log(f"Loading video: {file_path}", "INFO")
                
                # Stop current processing
                if self.video_thread.isRunning():
                    self.video_thread.stop()
                    
                # Set file source
                self.video_thread.set_video_source("file", file_path)
                
                # Start processing
                if not self.video_thread.isRunning():
                    self.video_thread.start()
                    
                self.results_viewer.add_log("✓ Video file playing", "INFO")
                self.statusBar().showMessage(f"Video source: File ({file_path})")
                
        elif source_type == "gazebo":
            # Connect to Gazebo simulation camera with auto-start
            self.results_viewer.add_log("🚁 Starting Gazebo Harmonic simulation...", "INFO")
            
            # Import Gazebo manager
            try:
                from drone_autonomy.utils.gazebo_manager import GazeboManager
            except ImportError as e:
                self.results_viewer.add_log(f"✗ Failed to import Gazebo manager: {e}", "ERROR")
                return

            if not hasattr(self, 'gazebo_starter_thread') or not self.gazebo_starter_thread.isRunning():
                # Use test_world.sdf for easier testing (simple ground plane + iris_with_camera)
                self.gazebo_starter_thread = GazeboStarterThread(
                    world_path=None,  # Use default (test_world.sdf)
                    udp_port=5600
                )
                self.gazebo_starter_thread.finished.connect(self._on_gazebo_ready)
                self.gazebo_starter_thread.progress.connect(lambda msg, level: self.results_viewer.add_log(msg, level))
                self.gazebo_starter_thread.start()
            else:
                self.results_viewer.add_log("Gazebo startup already in progress...", "WARNING")

    def _on_gazebo_ready(self, success, message):
        """Callback for when Gazebo is ready."""
        self.results_viewer.add_log(message, "SUCCESS" if success else "ERROR")
        if success:
            self._connect_gazebo_camera()
        else:
            QMessageBox.warning(self, "Gazebo Error", message)

    def _connect_gazebo_camera(self):
        """Helper method to connect to Gazebo camera."""
        self.results_viewer.add_log("Connecting to Gazebo camera GStreamer feed...", "INFO")
        
        import os
        gazebo_config_path = "config/gazebo_simulation.yaml"
        if not os.path.exists(gazebo_config_path):
            self.results_viewer.add_log(f"✗ Gazebo config not found: {gazebo_config_path}", "ERROR")
            return
        
        # Stop current processing if running
        if self.video_thread.isRunning():
            self.video_thread.stop()
            
        # Set Gazebo source with config file
        self.video_thread.set_video_source("gazebo", gazebo_config_path)
        
        # Start processing
        if not self.video_thread.isRunning():
            self.video_thread.start()
            
        self.results_viewer.add_log("✓ Gazebo camera stream active.", "INFO")
        self.statusBar().showMessage("Video source: Gazebo Simulation")
                
    def _toggle_recording(self):
        """Toggle video recording"""
        if self.record_action.isChecked():
            # Start recording
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"output/videos/recording_{timestamp}.mp4"
            
            # Get frame size from current frame
            if self.video_widget.current_frame is not None:
                h, w = self.video_widget.current_frame.shape[:2]
                frame_size = (w, h)
                
                if self.video_thread.start_recording(filename, frame_size, fps=30.0):
                    self.results_viewer.add_log(f"Recording started: {filename}", "INFO")
                    self.record_action.setText("⏹ Stop Recording")
                else:
                    self.results_viewer.add_log("Failed to start recording", "ERROR")
                    self.record_action.setChecked(False)
            else:
                self.results_viewer.add_log("No video feed to record", "WARNING")
                self.record_action.setChecked(False)
        else:
            # Stop recording
            filename = self.video_thread.stop_recording()
            if filename:
                self.results_viewer.add_log(f"Recording stopped: {filename}", "INFO")
            else:
                self.results_viewer.add_log("Recording stopped", "INFO")
            self.record_action.setText("⏺ Record")
            
    def _connect_to_drone(self):
        """Connect to drone"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QDialogButtonBox
        
        if not MAVLINK_AVAILABLE:
            self.results_viewer.add_log("MAVLink module not available. Install pymavlink.", "ERROR")
            QMessageBox.warning(self, "MAVLink Not Available", 
                              "MAVLink telemetry module is not available.\nPlease install pymavlink.")
            return
        
        # Create connection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Connect to Drone")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Protocol selection
        protocol_layout = QHBoxLayout()
        protocol_layout.addWidget(QLabel("Protocol:"))
        protocol_combo = QComboBox()
        protocol_combo.addItems(["UDP", "TCP", "Serial"])
        protocol_layout.addWidget(protocol_combo)
        layout.addLayout(protocol_layout)
        
        # Connection string
        connection_layout = QHBoxLayout()
        connection_layout.addWidget(QLabel("Address:"))
        connection_input = QLineEdit("127.0.0.1:14550")
        connection_layout.addWidget(connection_input)
        layout.addLayout(connection_layout)
        
        # Example text
        example_label = QLabel("Examples:\n  UDP: 127.0.0.1:14550\n  TCP: 127.0.0.1:5760\n  Serial: COM3 or /dev/ttyUSB0")
        example_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(example_label)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            protocol = protocol_combo.currentText().lower()
            address = connection_input.text()
            
            # Build connection string
            if protocol == "serial":
                connection_string = address  # Serial port path
            else:
                connection_string = f"{protocol}:{address}"
            
            self.results_viewer.add_log(f"Connecting to drone: {connection_string}", "INFO")
            self.telemetry_display.set_connection_status("Connecting")
            
            # Stop MAVLink timer if running
            if hasattr(self, 'mavlink_timer') and self.mavlink_timer.isActive():
                self.mavlink_timer.stop()
                self.results_viewer.add_log("Stopped MAVLink telemetry timer", "DEBUG")
            
            # Disconnect old connection if exists
            if self.mavlink is not None:
                try:
                    self.mavlink.disconnect()
                    self.results_viewer.add_log("Disconnected previous MAVLink connection", "INFO")
                    # Give time for socket to fully close
                    import time
                    time.sleep(0.5)
                except Exception as e:
                    self.results_viewer.add_log(f"Error disconnecting old connection: {e}", "WARNING")
                self.mavlink = None
            
            # Initialize MAVLink connection
            try:
                mavlink_config = {
                    'connection_string': connection_string,
                    'vio_publish_rate': 30,
                    'telemetry_rate': 10,
                    'baud': 57600,
                    'auto_detect': False,  # Don't auto-detect when user specifies
                    'heartbeat_timeout': 5  # 5 seconds timeout (was 10)
                }
                
                self.results_viewer.add_log(f"Attempting connection with {connection_string}...", "INFO")
                self.results_viewer.add_log("Waiting for heartbeat (5s timeout)...", "INFO")
                
                self.mavlink = MAVLinkTelemetry(mavlink_config)
                
                # Try to connect in background
                from PyQt6.QtCore import QThread
                
                class ConnectionThread(QThread):
                    connected = pyqtSignal(bool)
                    
                    def __init__(self, mavlink):
                        super().__init__()
                        self.mavlink = mavlink
                    
                    def run(self):
                        success = self.mavlink.connect()
                        self.connected.emit(success)
                
                def on_connected(success):
                    if success:
                        system_id = self.mavlink.connection.target_system if self.mavlink.connection else 0
                        component_id = self.mavlink.connection.target_component if self.mavlink.connection else 0
                        
                        self.results_viewer.add_log(f"✓ Heartbeat received from system {system_id}, component {component_id}", "SUCCESS")
                        self.results_viewer.add_log(f"✓ Connected to drone via {connection_string}", "SUCCESS")
                        self.telemetry_display.set_connection_status("Connected")

                        # Surface autopilot command logs in GUI
                        self.mavlink.set_command_logger(self._log_mavlink_action)
                        
                        # Provide MAVLink reference to video thread for failsafe commands
                        self.video_thread.set_mavlink(self.mavlink)
                        
                        # Provide MAVLink reference to drone control panel
                        self.drone_control.set_mavlink(self.mavlink)
                        
                        # Start telemetry polling timer
                        self.mavlink_timer.start()
                        self.results_viewer.add_log("✓ Telemetry polling started (10Hz)", "INFO")
                        self.results_viewer.add_log("✓ Video failsafe enabled (auto-land on 10s video loss)", "INFO")
                    else:
                        self.results_viewer.add_log(f"✗ No heartbeat received (timeout after 5s)", "ERROR")
                        self.results_viewer.add_log(f"✗ Failed to connect - check if drone/SITL is running", "ERROR")
                        self.telemetry_display.set_connection_status("Disconnected")
                        self.mavlink = None
                    
                    # Clean up connection thread after completion
                    if self.connection_thread is not None:
                        self.connection_thread.wait()  # Wait for thread to finish
                        self.connection_thread = None
                
                # Stop previous connection thread if exists
                if self.connection_thread is not None and self.connection_thread.isRunning():
                    self.connection_thread.wait()
                
                self.connection_thread = ConnectionThread(self.mavlink)
                self.connection_thread.connected.connect(on_connected)
                self.connection_thread.start()
                
            except Exception as e:
                self.results_viewer.add_log(f"Connection error: {str(e)}", "ERROR")
                self.telemetry_display.set_connection_status("Error")
                self.mavlink = None
            
    def _open_configuration(self):
        """Open configuration file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Configuration", "config", "YAML Files (*.yaml *.yml)"
        )
        if file_path:
            self.results_viewer.add_log(f"Loading configuration: {file_path}", "INFO")
            try:
                import yaml
                with open(file_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Apply configuration settings
                if 'depth' in config:
                    self.saved_settings['depth'].update(config['depth'])
                if 'detection' in config and 'target_detection' in config:
                    # Merge detection settings
                    if 'detection' not in self.saved_settings:
                        self.saved_settings['detection'] = {}
                    self.saved_settings['detection'].update({
                        'confidence_threshold': config.get('target_detection', {}).get('confidence_threshold', 0.5),
                        'nms_threshold': 0.4,
                        'imgsz': 640
                    })
                if 'performance' in config:
                    self.saved_settings['performance'].update(config['performance'])
                
                # Apply the loaded settings
                self._apply_new_settings(self.saved_settings)
                self.results_viewer.add_log(f"✓ Configuration loaded successfully", "SUCCESS")
                self.statusBar().showMessage(f"Configuration loaded: {os.path.basename(file_path)}", 5000)
                
            except Exception as e:
                self.results_viewer.add_log(f"✗ Failed to load configuration: {e}", "ERROR")
                QMessageBox.warning(self, "Configuration Error", f"Failed to load configuration:\n{e}")
            
    def _save_configuration(self):
        """Save configuration file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration", "config/custom.yaml", "YAML Files (*.yaml *.yml)"
        )
        if file_path:
            self.results_viewer.add_log(f"Saving configuration: {file_path}", "INFO")
            try:
                import yaml
                
                # Build configuration structure matching default_config.yaml format
                config = {
                    'depth': self.saved_settings.get('depth', {}),
                    'target_detection': {
                        'confidence_threshold': self.saved_settings.get('detection', {}).get('confidence_threshold', 0.5),
                        'hsv_lower': [0, 100, 100],
                        'hsv_upper': [10, 255, 255],
                        'min_radius': 10,
                        'max_radius': 200,
                        'circle_threshold': 0.7,
                        'downscale_factor': 2
                    },
                    'performance': self.saved_settings.get('performance', {}),
                    'display': self.saved_settings.get('display', {})
                }
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Save to YAML file
                with open(file_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                
                self.results_viewer.add_log(f"✓ Configuration saved successfully", "SUCCESS")
                self.statusBar().showMessage(f"Configuration saved: {os.path.basename(file_path)}", 5000)
                
            except Exception as e:
                self.results_viewer.add_log(f"✗ Failed to save configuration: {e}", "ERROR")
                QMessageBox.warning(self, "Save Error", f"Failed to save configuration:\n{e}")
            
    def _export_results(self):
        """Export task results"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "results.json", "JSON Files (*.json)"
        )
        if file_path:
            self.results_viewer.add_log(f"Exporting results: {file_path}", "INFO")
            try:
                import json
                from datetime import datetime
                
                # Collect results data
                results = {
                    'export_time': datetime.now().isoformat(),
                    'session_info': {
                        'video_source': self.video_thread.original_video_source_type or 'None',
                        'depth_enabled': self.video_thread.enable_depth,
                        'detection_enabled': self.video_thread.enable_detection,
                        'obstacle_avoidance_enabled': self.video_thread.obstacle_avoidance_enabled
                    },
                    'configuration': self.saved_settings,
                    'telemetry': {},
                    'logs': []
                }
                
                # Add current telemetry if available
                if self.mavlink and self.mavlink.is_connected:
                    results['telemetry'] = self.mavlink.get_flattened_telemetry()
                
                # Add logs from results viewer if accessible
                if hasattr(self.results_viewer, 'get_all_logs'):
                    results['logs'] = self.results_viewer.get_all_logs()
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Save to JSON file
                with open(file_path, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                
                self.results_viewer.add_log(f"✓ Results exported successfully", "SUCCESS")
                self.statusBar().showMessage(f"Results exported: {os.path.basename(file_path)}", 5000)
                
            except Exception as e:
                self.results_viewer.add_log(f"✗ Failed to export results: {e}", "ERROR")
                QMessageBox.warning(self, "Export Error", f"Failed to export results:\n{e}")
            
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def _open_settings(self):
        """Open settings dialog"""
        # Use saved settings as current settings
        current_settings = self.saved_settings.copy()
        
        # Update with any runtime values from video thread
        if self.video_thread.depth_estimator:
            current_settings['depth']['model'] = getattr(self.video_thread.depth_estimator, 'model_type', current_settings['depth']['model'])
            current_settings['depth']['device'] = getattr(self.video_thread.depth_estimator, 'device', current_settings['depth']['device'])
        
        # Create and show settings dialog
        dialog = SettingsDialog(current_settings, self)
        dialog.settings_changed.connect(self._apply_new_settings)
        
        if dialog.exec():
            # Get settings from dialog
            new_settings = dialog._collect_settings()
            
            # Save to persistent storage
            if self.settings_manager.save_settings(new_settings):
                self.saved_settings = new_settings
                self.results_viewer.add_log("✓ Settings saved successfully", "SUCCESS")
            else:
                self.results_viewer.add_log("✗ Failed to save settings", "ERROR")
            
    def _apply_new_settings(self, new_settings: Dict[str, Any]):
        """Apply new settings to the pipeline"""
        try:
            self.results_viewer.add_log("Applying new settings...", "INFO")
            
            # Update depth estimator if settings changed
            if 'depth' in new_settings and DEPTH_AVAILABLE:
                depth_config = new_settings['depth']
                
                # Check if model changed
                current_model = getattr(self.video_thread.depth_estimator, 'model_type', None) if self.video_thread.depth_estimator else None
                new_model = depth_config.get('model')
                
                if current_model != new_model or self.video_thread.depth_estimator is None:
                    self.results_viewer.add_log(f"Switching depth model to: {new_model}", "INFO")
                    
                    # Create new depth estimator with new config
                    import torch
                    depth_config_full = {
                        'model': depth_config['model'],
                        'device': depth_config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu'),
                        'output_width': depth_config.get('output_width', 518),
                        'output_height': depth_config.get('output_height', 518),
                        'use_metric_calibration': False
                    }
                    
                    new_estimator = DepthEstimator(depth_config_full)
                    if new_estimator.load_model():
                        self.video_thread.depth_estimator = new_estimator
                        self.results_viewer.add_log(f"✓ Depth model loaded: {new_model}", "INFO")
                    else:
                        self.results_viewer.add_log(f"✗ Failed to load depth model: {new_model}", "ERROR")
                else:
                    # Just update output resolution without reloading
                    if self.video_thread.depth_estimator and hasattr(self.video_thread.depth_estimator.model, 'output_width'):
                        self.video_thread.depth_estimator.model.output_width = depth_config.get('output_width', 518)
                        self.video_thread.depth_estimator.model.output_height = depth_config.get('output_height', 518)
                        self.results_viewer.add_log("✓ Depth output resolution updated", "INFO")
                        
            # Update detector settings if needed
            if 'detection' in new_settings and DEPTH_AVAILABLE:
                det_config = new_settings['detection']
                if self.video_thread.detector:
                    # Update detector thresholds
                    self.video_thread.detector.conf_threshold = det_config.get('confidence_threshold', 0.5)
                    self.video_thread.detector.nms_threshold = det_config.get('nms_threshold', 0.4)
                    self.results_viewer.add_log("✓ Detection settings updated", "INFO")
            
            # Update performance settings
            if 'performance' in new_settings:
                perf_config = new_settings['performance']
                enable_depth = perf_config.get('enable_depth', True)
                enable_detection = perf_config.get('enable_detection', True)
                self.video_thread.set_performance_settings(enable_depth, enable_detection)
                self.results_viewer.add_log(f"✓ Performance settings: depth={'ON' if enable_depth else 'OFF'}, detection={'ON' if enable_detection else 'OFF'}", "INFO")
            
            # Update display settings
            if 'display' in new_settings:
                display_config = new_settings['display']
                show_fps = display_config.get('show_fps', False)
                self.video_widget.set_fps_display(show_fps)
                self.results_viewer.add_log(f"✓ FPS counter: {'ON' if show_fps else 'OFF'}", "INFO")
                    
            self.statusBar().showMessage("Settings applied successfully", 3000)
            
        except Exception as e:
            self.results_viewer.add_log(f"Error applying settings: {e}", "ERROR")
            QMessageBox.warning(self, "Settings Error", f"Failed to apply settings:\n{e}")
            
    def _open_camera_calibration(self):
        """Open camera calibration tool"""
        QMessageBox.information(self, "Camera Calibration",
                               "Camera calibration tool coming soon!\n\n"
                               "Use examples/calibrate_camera.py for now.")
        
    def _run_diagnostics(self):
        """Run system diagnostics"""
        self.results_viewer.add_log("Running system diagnostics...", "INFO")
        
        diagnostics_results = []
        all_ok = True
        
        # Check depth estimator
        if DEPTH_AVAILABLE and self.video_thread.depth_estimator:
            diagnostics_results.append("✓ Depth Estimator: Available")
            model_type = getattr(self.video_thread.depth_estimator, 'model_type', 'Unknown')
            diagnostics_results.append(f"  Model: {model_type}")
        else:
            diagnostics_results.append("✗ Depth Estimator: Not available")
            all_ok = False
        
        # Check object detector
        if DEPTH_AVAILABLE and self.video_thread.detector:
            diagnostics_results.append("✓ Object Detector: Available")
        else:
            diagnostics_results.append("✗ Object Detector: Not available")
            all_ok = False
        
        # Check obstacle avoider
        if self.video_thread.obstacle_avoider:
            diagnostics_results.append("✓ Obstacle Avoider: Available")
        else:
            diagnostics_results.append("✗ Obstacle Avoider: Not available")
            all_ok = False
        
        # Check MAVLink connection
        if MAVLINK_AVAILABLE and self.mavlink and self.mavlink.is_connected:
            diagnostics_results.append("✓ MAVLink Connection: Connected")
            telemetry = self.mavlink.get_flattened_telemetry()
            if telemetry:
                diagnostics_results.append(f"  Flight Mode: {telemetry.get('flight_mode', 'Unknown')}")
                diagnostics_results.append(f"  Armed: {telemetry.get('armed', False)}")
        else:
            diagnostics_results.append("✗ MAVLink Connection: Not connected")
        
        # Check video source
        if self.video_thread.capture and self.video_thread.capture.isOpened():
            diagnostics_results.append("✓ Video Source: Active")
            diagnostics_results.append(f"  Type: {self.video_thread.video_source or 'Unknown'}")
        else:
            diagnostics_results.append("✗ Video Source: Not active")
        
        # Check CUDA availability
        try:
            import torch
            if torch.cuda.is_available():
                diagnostics_results.append("✓ CUDA: Available")
                diagnostics_results.append(f"  GPU: {torch.cuda.get_device_name(0)}")
            else:
                diagnostics_results.append("⚠ CUDA: Not available (using CPU)")
        except:
            diagnostics_results.append("⚠ PyTorch: Not available")
        
        # Display results
        result_text = "\n".join(diagnostics_results)
        self.results_viewer.add_log("Diagnostics complete", "INFO")
        
        for line in diagnostics_results:
            if "✗" in line:
                self.results_viewer.add_log(line, "ERROR")
            elif "⚠" in line:
                self.results_viewer.add_log(line, "WARNING")
            else:
                self.results_viewer.add_log(line, "SUCCESS")
        
        status = "All systems operational" if all_ok else "Some systems unavailable"
        QMessageBox.information(self, "System Diagnostics", f"{status}\n\n{result_text}")
    
    def _toggle_obstacle_avoidance(self, checked: bool):
        """Toggle obstacle avoidance active control from menu"""
        # Sync with drone control panel checkbox
        self.drone_control.avoidance_checkbox.setChecked(checked)
        
        self.video_thread.set_obstacle_avoidance_enabled(checked)
        
        if checked:
            self.results_viewer.add_log("✓ Obstacle avoidance ENABLED - Drone will avoid obstacles in GUIDED mode", "SUCCESS")
            self.statusBar().showMessage("🛡️ Obstacle Avoidance: ACTIVE", 5000)
            
            # Warn if not connected to drone
            if not self.mavlink or not self.mavlink.is_connected:
                QMessageBox.warning(
                    self,
                    "Obstacle Avoidance",
                    "Obstacle avoidance enabled, but no drone connected.\n\n"
                    "Commands will only be sent when:\n"
                    "1. MAVLink connection is active\n"
                    "2. Drone is in GUIDED mode\n\n"
                    "Connect to drone via Tools → Connect to Drone"
                )
        else:
            self.results_viewer.add_log("✗ Obstacle avoidance DISABLED - Manual control only", "WARNING")
            self.statusBar().showMessage("Obstacle Avoidance: INACTIVE", 5000)
        
    def _open_documentation(self):
        """Open documentation"""
        import webbrowser
        webbrowser.open("https://github.com/yourusername/DroneAutonomy/blob/main/README.md")
        
    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About Drone Autonomy",
                         "<h2>Drone Autonomy Control System</h2>"
                         "<p>Version 1.0.0</p>"
                         "<p>Advanced computer vision and autonomous navigation for drones.</p>"
                         "<p><b>Features:</b></p>"
                         "<ul>"
                         "<li>Real-time object detection (YOLO)</li>"
                         "<li>Depth estimation (Depth Anything V2)</li>"
                         "<li>Autonomous task execution</li>"
                         "<li>Competition task support</li>"
                         "<li>MAVLink telemetry integration</li>"
                         "</ul>"
                         "<p>© 2024 Drone Autonomy Project</p>")
    
    # ===== Task Handlers =====
    # Note: Task-specific handlers can be added here as needed
    # See examples/tasks/ for task implementation examples
    # For example implementations, refer to examples/tasks/simple_hover_example.py
        
    def closeEvent(self, event):
        """Handle window close event"""
        # Save window geometry
        geometry = self.geometry()
        self.saved_settings['window'] = {
            'x': geometry.x(),
            'y': geometry.y(),
            'width': geometry.width(),
            'height': geometry.height()
        }
        
        # Save splitter states
        self.saved_settings['splitters'] = {
            'main': bytes(self.main_splitter.saveState()).hex(),
            'left': bytes(self.left_splitter.saveState()).hex(),
            'right': bytes(self.right_splitter.saveState()).hex()
        }
        
        self.settings_manager.save_settings(self.saved_settings)
        
        # Stop MAVLink telemetry timer
        if hasattr(self, 'mavlink_timer') and self.mavlink_timer.isActive():
            self.mavlink_timer.stop()
        
        # Disconnect MAVLink
        if self.mavlink is not None:
            self.mavlink.disconnect()
            self.mavlink = None
        
        # Stop video thread
        if self.video_thread.running:
            self.video_thread.stop()
        
        # Stop connection thread if running
        if self.connection_thread is not None and self.connection_thread.isRunning():
            self.connection_thread.wait()  # Wait for thread to finish
            
        # Close fullscreen window if open
        if hasattr(self.video_widget, 'fullscreen_window') and self.video_widget.fullscreen_window:
            self.video_widget.fullscreen_window.close()
        
        event.accept()
    
    # ===== Panel Toggle Methods =====
    
    def _toggle_tasks_panel(self):
        """Toggle task control panel visibility"""
        widget = self.left_splitter.widget(1)  # Task tabs
        if widget.isVisible():
            widget.hide()
            self.toggle_tasks_action.setText("Show &Task Panel")
        else:
            widget.show()
            self.toggle_tasks_action.setText("Hide &Task Panel")
    
    def _toggle_results_panel(self):
        """Toggle results viewer visibility"""
        widget = self.right_splitter.widget(0)  # Results viewer
        if widget.isVisible():
            widget.hide()
            self.toggle_results_action.setText("Show &Results Panel")
        else:
            widget.show()
            self.toggle_results_action.setText("Hide &Results Panel")
    
    def _toggle_telemetry_panel(self):
        """Toggle telemetry display visibility"""
        widget = self.right_splitter.widget(1)  # Telemetry display
        if widget.isVisible():
            widget.hide()
            self.toggle_telemetry_action.setText("Show Tele&metry Panel")
        else:
            widget.show()
            self.toggle_telemetry_action.setText("Hide Tele&metry Panel")
    
    def _focus_video_mode(self):
        """Focus mode: Hide all panels except video"""
        # Hide task panels
        self.left_splitter.widget(1).hide()
        self.toggle_tasks_action.setText("Show &Task Panel")
        self.toggle_tasks_action.setChecked(False)
        
        # Minimize right panel by setting sizes
        total_width = self.main_splitter.width()
        self.main_splitter.setSizes([total_width - 50, 50])
        
        self.statusBar().showMessage("Focus Mode: Video maximized", 3000)
    
    def _restore_default_layout(self):
        """Restore default panel layout"""
        # Show all panels
        self.left_splitter.widget(1).show()
        self.toggle_tasks_action.setText("Hide &Task Panel")
        self.toggle_tasks_action.setChecked(True)
        
        self.right_splitter.widget(0).show()
        self.toggle_results_action.setText("Hide &Results Panel")
        self.toggle_results_action.setChecked(True)
        
        self.right_splitter.widget(1).show()
        self.toggle_telemetry_action.setText("Hide Tele&metry Panel")
        self.toggle_telemetry_action.setChecked(True)
        
        # Reset splitter sizes to defaults
        self.main_splitter.setSizes([1100, 500])
        self.left_splitter.setSizes([600, 400])
        self.right_splitter.setSizes([600, 400])
        
        self.statusBar().showMessage("Layout restored to default", 3000)

class GazeboStarterThread(QThread):
    """Thread to start Gazebo Harmonic without blocking the GUI."""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str, str)  # message, log_level
    
    def __init__(self, world_path=None, udp_port=5600):
        super().__init__()
        self.world_path = world_path
        self.udp_port = udp_port
    
    def run(self):
        """Start Gazebo Harmonic with GStreamer camera plugin."""
        from drone_autonomy.utils.gazebo_manager import GazeboManager
        
        try:
            manager = GazeboManager(world_path=self.world_path, udp_port=self.udp_port, auto_start_sitl=True)
            
            # Check if already running
            if manager.is_gazebo_running():
                self.progress.emit("✓ Gazebo is already running", "INFO")
                self.progress.emit("Connecting to existing stream...", "INFO")
                self.finished.emit(True, "✓ Connected to existing Gazebo simulation")
                return
            
            # Start Gazebo (will auto-start SITL if enabled)
            self.progress.emit(f"🚀 Starting Gazebo with GStreamer plugin...", "INFO")
            self.progress.emit(f"📁 World: {manager.world_path}", "INFO")
            self.progress.emit(f"🌐 Streaming to port {manager.udp_port}", "INFO")
            
            if not manager.start_gazebo(visible=True, use_nvidia_gpu=False):
                self.finished.emit(False, "✗ Failed to start Gazebo. Check WSL and try manually.")
                return
            
            # Wait for Gazebo to initialize
            self.progress.emit("⏳ Waiting for Gazebo to initialize...", "INFO")
            time.sleep(5)  # Give Gazebo time to start
            
            # Wait for stream
            self.progress.emit("🎥 Waiting for video stream...", "INFO")
            if manager.wait_for_stream(timeout=15):
                self.progress.emit("✓ Video stream detected!", "SUCCESS")
                
                # Test connection
                self.progress.emit("🧪 Testing GStreamer connection...", "INFO")
                if manager.test_gstreamer_connection():
                    self.finished.emit(True, "✓ Gazebo started successfully with video stream!")
                else:
                    self.finished.emit(True, "⚠ Gazebo started but video test failed. Stream may still work.")
            else:
                self.finished.emit(True, "⚠ Gazebo started but video stream not detected. Check camera plugin.")
                
        except Exception as e:
            self.progress.emit(f"✗ Error: {e}", "ERROR")
            self.finished.emit(False, f"✗ Failed to start Gazebo: {e}")


def main():
    """Main entry point for GUI application"""
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setApplicationName("Drone Autonomy")
    app.setOrganizationName("DroneAutonomy")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
