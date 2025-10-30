"""Main pipeline orchestrator for DroneAutonomy system."""

import cv2
import numpy as np
import logging
import time
from typing import Optional
from pathlib import Path

from drone_autonomy.video.stream import VideoStream
from drone_autonomy.vio.vio_estimator import VIOEstimator
from drone_autonomy.depth.depth_estimator import DepthEstimator
from drone_autonomy.detection.yolo_detector import YOLODetector
from drone_autonomy.detection.target_detector import TargetDetector
from drone_autonomy.fusion.decision_layer import DecisionLayer
from drone_autonomy.mavlink.telemetry import MAVLinkTelemetry
from drone_autonomy.simulation.airsim_interface import AirSimInterface
from drone_autonomy.utils.config import Config
from drone_autonomy.utils.camera_calibration import CameraCalibration
from drone_autonomy.utils.logger import setup_logging


class DronePipeline:
    """
    Main drone autonomy pipeline orchestrator.
    
    Integrates video stream, VIO, depth estimation, object detection,
    target detection, fusion, and MAVLink communication.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize drone pipeline.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = Config(config_path)
        
        # Setup logging
        log_config = self.config.config.get('logging', {})
        self.logger = setup_logging(
            log_level=log_config.get('level', 'INFO'),
            log_dir=log_config.get('log_dir', 'logs'),
            log_to_file=True
        )
        
        self.logger.info("=" * 80)
        self.logger.info("DroneAutonomy Pipeline Starting")
        self.logger.info("=" * 80)
        
        # Initialize camera calibration
        self.camera_calib = CameraCalibration()
        self.camera_calib.load_from_config(self.config.config.get('camera', {}))
        
        # Initialize modules
        self.video_stream = None
        self.vio_estimator = None
        self.depth_estimator = None
        self.yolo_detector = None
        self.target_detector = None
        self.decision_layer = None
        self.mavlink = None
        self.airsim = None
        
        # State
        self.is_running = False
        self.frame_count = 0
        self.start_time = None
        
        # Performance tracking
        self.perf_stats = {
            'vio_time': [],
            'depth_time': [],
            'detection_time': [],
            'target_time': [],
            'fusion_time': [],
            'total_time': []
        }
        
    def initialize(self) -> bool:
        """
        Initialize all pipeline components.
        
        Returns:
            True if initialization successful
        """
        try:
            # Initialize simulation if enabled
            if self.config.get('simulation.enabled', False):
                self.logger.info("Initializing AirSim simulation...")
                self.airsim = AirSimInterface(self.config.config['simulation'])
                if not self.airsim.connect():
                    self.logger.warning("AirSim connection failed, continuing without simulation")
                    self.airsim = None
            
            # Initialize video stream
            self.logger.info("Initializing video stream...")
            if self.airsim is not None:
                # Use AirSim for video
                self.video_stream = None
            else:
                self.video_stream = VideoStream(self.config.config['video'])
                if not self.video_stream.start():
                    self.logger.error("Failed to start video stream")
                    return False
            
            # Initialize VIO estimator
            if self.config.get('vio.enabled', True):
                self.logger.info("Initializing VIO estimator...")
                self.vio_estimator = VIOEstimator(
                    self.config.config['vio'],
                    self.camera_calib.get_camera_matrix(),
                    self.camera_calib.get_dist_coeffs()
                )
            
            # Initialize depth estimator
            self.logger.info("Initializing depth estimator...")
            self.depth_estimator = DepthEstimator(self.config.config['depth'])
            if not self.depth_estimator.load_model():
                self.logger.error("Failed to load depth model")
                return False
            
            # Initialize YOLO detector
            self.logger.info("Initializing YOLO detector...")
            self.yolo_detector = YOLODetector(self.config.config['detection'])
            if not self.yolo_detector.load_model():
                self.logger.error("Failed to load YOLO model")
                return False
            
            # Initialize target detector
            self.logger.info("Initializing target detector...")
            self.target_detector = TargetDetector(self.config.config['target_detection'])
            
            # Initialize decision layer
            self.logger.info("Initializing decision layer...")
            self.decision_layer = DecisionLayer(self.config.config['fusion'])
            
            # Initialize MAVLink
            self.logger.info("Initializing MAVLink...")
            self.mavlink = MAVLinkTelemetry(self.config.config['mavlink'])
            if not self.mavlink.connect():
                self.logger.warning("MAVLink connection failed, continuing without telemetry")
                self.mavlink = None
            
            self.logger.info("Pipeline initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing pipeline: {e}", exc_info=True)
            return False
    
    def run(self, display: bool = True, max_frames: Optional[int] = None):
        """
        Run the main pipeline loop.
        
        Args:
            display: Whether to display output
            max_frames: Maximum number of frames to process (None for infinite)
        """
        self.is_running = True
        self.start_time = time.time()
        
        self.logger.info("Starting pipeline main loop")
        
        try:
            while self.is_running:
                loop_start = time.time()
                
                # Get frame
                if self.airsim is not None:
                    frame = self.airsim.get_camera_image()
                    if frame is None:
                        continue
                    timestamp = time.time()
                elif self.video_stream is not None:
                    ret, frame, timestamp = self.video_stream.read()
                    if not ret:
                        self.logger.warning("Failed to read frame")
                        break
                else:
                    self.logger.error("No video source available")
                    break
                
                self.frame_count += 1
                
                # Process frame
                results = self._process_frame(frame, timestamp)
                
                # Display results
                if display:
                    self._display_results(frame, results)
                
                # Check termination
                if max_frames and self.frame_count >= max_frames:
                    break
                
                # Performance stats
                loop_time = time.time() - loop_start
                self.perf_stats['total_time'].append(loop_time)
                
                # Log periodic stats
                if self.frame_count % 30 == 0:
                    self._log_performance()
                
                # Check for quit
                if display and cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            self.logger.info("Pipeline interrupted by user")
        except Exception as e:
            self.logger.error(f"Error in pipeline loop: {e}", exc_info=True)
        finally:
            self.stop()
    
    def _process_frame(self, frame: np.ndarray, timestamp: float) -> dict:
        """
        Process a single frame through the pipeline.
        
        Args:
            frame: Input frame
            timestamp: Frame timestamp
            
        Returns:
            Dictionary with processing results
        """
        results = {
            'timestamp': timestamp,
            'frame': frame
        }
        
        # VIO estimation
        if self.vio_estimator is not None:
            t_start = time.time()
            imu_data = self.airsim.get_imu_data() if self.airsim else None
            success, position, orientation = self.vio_estimator.process_frame(frame, imu_data)
            results['vio_time'] = time.time() - t_start
            results['vio_position'] = position
            results['vio_orientation'] = orientation
            results['vio_success'] = success
            
            # Publish to MAVLink
            if success and self.mavlink is not None:
                self.mavlink.publish_visual_odometry(position, orientation)
        
        # Depth estimation
        t_start = time.time()
        depth_map, depth_time = self.depth_estimator.estimate_depth(frame)
        results['depth_map'] = depth_map
        results['depth_time'] = depth_time
        
        # YOLO detection
        t_start = time.time()
        detections, detect_time = self.yolo_detector.detect(frame)
        results['detections'] = detections
        results['detection_time'] = detect_time
        
        # Target detection
        t_start = time.time()
        targets, target_time = self.target_detector.detect(frame)
        results['targets'] = targets
        results['target_time'] = target_time
        
        # Fusion and decision
        if depth_map is not None:
            t_start = time.time()
            
            fused_detections = self.decision_layer.fuse_detections_with_depth(
                detections, depth_map, depth_scale=10.0
            )
            fused_targets = self.decision_layer.fuse_targets_with_depth(
                targets, depth_map, depth_scale=10.0
            )
            
            avoidance_cmd = self.decision_layer.compute_avoidance_command(
                fused_detections, frame.shape[1], frame.shape[0]
            )
            target_cmd = self.decision_layer.compute_target_approach(
                fused_targets, frame.shape[1], frame.shape[0]
            )
            
            results['fused_detections'] = fused_detections
            results['fused_targets'] = fused_targets
            results['avoidance_command'] = avoidance_cmd
            results['target_command'] = target_cmd
            results['fusion_time'] = time.time() - t_start
        
        return results
    
    def _display_results(self, frame: np.ndarray, results: dict):
        """
        Display processing results.
        
        Args:
            frame: Input frame
            results: Processing results
        """
        # Create display frame
        display_frame = frame.copy()
        
        # Draw detections
        if 'detections' in results and results['detections']:
            display_frame = self.yolo_detector.draw_detections(display_frame, results['detections'])
        
        # Draw targets
        if 'targets' in results and results['targets']:
            display_frame = self.target_detector.draw_targets(display_frame, results['targets'])
        
        # Display depth map
        if 'depth_map' in results and results['depth_map'] is not None:
            depth_vis = self.depth_estimator.visualize_depth(results['depth_map'])
            if depth_vis is not None:
                depth_vis = cv2.resize(depth_vis, (frame.shape[1] // 2, frame.shape[0] // 2))
                cv2.imshow('Depth Map', depth_vis)
        
        # Add text overlay
        y_offset = 30
        cv2.putText(display_frame, f"Frame: {self.frame_count}", (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        if 'vio_success' in results and results['vio_success']:
            y_offset += 30
            pos = results['vio_position']
            cv2.putText(display_frame, f"VIO Pos: [{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}]",
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        cv2.imshow('DroneAutonomy Pipeline', display_frame)
    
    def _log_performance(self):
        """Log performance statistics."""
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        self.logger.info(f"Performance Stats - Frame {self.frame_count}, FPS: {fps:.2f}")
        
        if self.perf_stats['total_time']:
            avg_total = np.mean(self.perf_stats['total_time'][-30:])
            self.logger.info(f"  Avg loop time: {avg_total*1000:.1f}ms")
    
    def stop(self):
        """Stop the pipeline."""
        self.logger.info("Stopping pipeline...")
        self.is_running = False
        
        if self.video_stream is not None:
            self.video_stream.stop()
        
        if self.mavlink is not None:
            self.mavlink.disconnect()
        
        if self.airsim is not None:
            self.airsim.disconnect()
        
        cv2.destroyAllWindows()
        
        self.logger.info("Pipeline stopped")
        self._log_final_stats()
    
    def _log_final_stats(self):
        """Log final statistics."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        self.logger.info("=" * 80)
        self.logger.info("Final Statistics")
        self.logger.info(f"  Total frames: {self.frame_count}")
        self.logger.info(f"  Total time: {elapsed:.2f}s")
        self.logger.info(f"  Average FPS: {fps:.2f}")
        self.logger.info("=" * 80)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='DroneAutonomy Pipeline')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--no-display', action='store_true', help='Disable display')
    parser.add_argument('--max-frames', type=int, help='Maximum number of frames to process')
    
    args = parser.parse_args()
    
    # Create and run pipeline
    pipeline = DronePipeline(args.config)
    
    if pipeline.initialize():
        pipeline.run(display=not args.no_display, max_frames=args.max_frames)
    else:
        logging.error("Failed to initialize pipeline")
        return 1
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
