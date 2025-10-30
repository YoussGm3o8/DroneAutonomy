"""Main pipeline orchestrator for DroneAutonomy system."""

import cv2
import numpy as np
import logging
import time
import torch
from typing import Optional
from pathlib import Path

from drone_autonomy.video.stream import VideoStream
from drone_autonomy.vio.vio_estimator import VIOEstimator
from drone_autonomy.depth.depth_estimator import DepthEstimator
from drone_autonomy.detection.target_detector import TargetDetector
from drone_autonomy.fusion.decision_layer import DecisionLayer
from drone_autonomy.mavlink.telemetry import MAVLinkTelemetry
from drone_autonomy.simulation.airsim_interface import AirSimInterface
from drone_autonomy.navigation.autonomous_controller import AutonomousController
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
            config_path: Path to configuration file. If None, looks for config/default_config.yaml
        """
        # If no config path provided, try to find default config
        if config_path is None:
            # Try to find config relative to this file
            pipeline_dir = Path(__file__).parent.parent.parent  # Go up to project root
            default_config = pipeline_dir / 'config' / 'default_config.yaml'
            if default_config.exists():
                config_path = str(default_config)
                print(f"Using default config: {config_path}")
            else:
                print(f"Warning: Default config not found at {default_config}")
                print("Using built-in defaults (may not work with RTSP camera)")
        
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
        self.target_detector = None
        self.decision_layer = None
        self.mavlink = None
        self.airsim = None
        self.autonomous_controller = None
        
        # State
        self.is_running = False
        self.frame_count = 0
        self.start_time = None
        self.autonomous_mode = False
        
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
                else:
                    # Auto takeoff if configured
                    if self.config.get('simulation.auto_takeoff', False):
                        self.logger.info("Auto-takeoff enabled, taking off...")
                        self.airsim.takeoff(timeout_sec=10.0)
            
            # Initialize video stream
            if self.airsim is not None:
                # Use AirSim for video - no VideoStream needed
                self.logger.info("Using AirSim for video input")
                self.video_stream = None
            else:
                self.logger.info("Initializing video stream...")
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
            
            # Initialize target detector (circle detection)
            self.logger.info("Initializing target detector...")
            self.target_detector = TargetDetector(self.config.config['target_detection'])
            
            # Initialize decision layer
            self.logger.info("Initializing decision layer...")
            self.decision_layer = DecisionLayer(self.config.config['fusion'])
            
            # Initialize MAVLink (skip in simulation mode)
            if self.airsim is None:  # Only use MAVLink with real drone
                self.logger.info("Initializing MAVLink...")
                self.mavlink = MAVLinkTelemetry(self.config.config['mavlink'])
                if not self.mavlink.connect():
                    self.logger.warning("MAVLink connection failed, continuing without telemetry")
                    self.mavlink = None
            else:
                self.logger.info("Simulation mode: skipping MAVLink initialization")
                self.mavlink = None
            
            # Initialize autonomous controller if config present
            if 'autonomous' in self.config.config:
                self.logger.info("Initializing autonomous controller...")
                self.autonomous_controller = AutonomousController(
                    self.config.config['autonomous'],
                    self.mavlink,
                    self.logger
                )
            
            self.logger.info("Pipeline initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing pipeline: {e}", exc_info=True)
            return False
    
    def run(self, display: bool = True, max_frames: Optional[int] = None, 
            process_interval: int = 1, fast_mode: bool = False, autonomous: bool = False):
        """
        Run the main pipeline loop.
        
        Args:
            display: Whether to display output
            max_frames: Maximum number of frames to process (None for infinite)
            process_interval: Process every Nth frame (1 = all frames, 2 = every other frame)
            fast_mode: If True, skip depth estimation for faster processing
            autonomous: If True, enable autonomous navigation
        """
        self.is_running = True
        self.start_time = time.time()
        self.fast_mode = fast_mode
        self.process_interval = process_interval
        self.autonomous_mode = autonomous
        
        # Start autonomous controller if enabled
        if autonomous and self.autonomous_controller:
            self.autonomous_controller.start()
            self.logger.info("Autonomous navigation ENABLED")
        
        self.logger.info(f"Starting pipeline main loop (fast={fast_mode}, interval={process_interval}, autonomous={autonomous})")
        
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
                    # Check for quit
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # Check termination
                if max_frames and self.frame_count >= max_frames:
                    break
                
                # Performance stats
                loop_time = time.time() - loop_start
                self.perf_stats['total_time'].append(loop_time)
                
                # Log periodic stats
                if self.frame_count % 30 == 0:
                    self._log_performance()
                    
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
        
        # Determine if this frame should be fully processed
        should_process = (self.frame_count % self.process_interval == 0)
        
        # VIO estimation (always run for odometry)
        if self.vio_estimator is not None and should_process:
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
        
        # Depth estimation (skip in fast mode or non-processed frames)
        depth_map = None
        if not self.fast_mode and should_process:
            t_start = time.time()
            depth_map, depth_time = self.depth_estimator.estimate_depth(frame)
            results['depth_map'] = depth_map
            results['depth_time'] = depth_time
        
        # Target detection (circle detection - always run)
        targets = []
        if should_process:
            t_start = time.time()
            targets, target_time = self.target_detector.detect(frame)
            results['targets'] = targets
            results['target_time'] = target_time
        
        # Fusion and decision (depth + targets)
        if depth_map is not None and targets:
            t_start = time.time()
            
            fused_targets = self.decision_layer.fuse_targets_with_depth(
                targets, depth_map, depth_scale=10.0
            )
            
            # Compute obstacle avoidance from depth map (no YOLO detections)
            avoidance_cmd = self.decision_layer.compute_avoidance_from_depth(
                depth_map, frame.shape[1], frame.shape[0]
            )
            target_cmd = self.decision_layer.compute_target_approach(
                fused_targets, frame.shape[1], frame.shape[0]
            )
            
            results['fused_targets'] = fused_targets
            results['avoidance_command'] = avoidance_cmd
            results['target_command'] = target_cmd
            results['fusion_time'] = time.time() - t_start
        
        # Autonomous navigation control
        if self.autonomous_mode and self.autonomous_controller is not None and should_process:
            # Prepare target detection for autonomous controller
            target_info = None
            if targets:
                # Use first (best) target
                target_info = {
                    'detected': True,
                    'bbox': targets[0]['bbox'],
                    'center': (targets[0]['center'][0], targets[0]['center'][1])
                }
            
            # Update autonomous controller (no YOLO detections, depth-only obstacle avoidance)
            nav_result = self.autonomous_controller.update(
                frame, depth_map, [], target_info  # Empty list for detections
            )
            
            results['autonomous_nav'] = nav_result
            
            # Send navigation commands to MAVLink or AirSim
            if nav_result['velocity_command'] and self.mavlink:
                # TODO: Implement MAVLink velocity control
                pass
            elif nav_result['velocity_command'] and self.airsim:
                # TODO: Implement AirSim velocity control
                pass
            
            if nav_result['yaw_rate_command'] and self.mavlink:
                # TODO: Implement MAVLink yaw control
                pass
            elif nav_result['yaw_rate_command'] and self.airsim:
                # TODO: Implement AirSim yaw control
                pass
        
        return results
    
    def _display_results(self, frame: np.ndarray, results: dict):
        """
        Display processing results.
        
        Args:
            frame: Input frame
            results: Processing results
        """
        # Resize frame to 720p for display (maintain aspect ratio)
        display_height = 720
        aspect_ratio = frame.shape[1] / frame.shape[0]
        display_width = int(display_height * aspect_ratio)
        display_frame = cv2.resize(frame, (display_width, display_height))
        
        # Draw detections (REMOVED - no YOLO)
        
        # Draw targets (circle detection)
        if 'targets' in results and results['targets']:
            # Scale target coordinates for display resolution
            scaled_targets = []
            scale_x = display_width / frame.shape[1]
            scale_y = display_height / frame.shape[0]
            
            for target in results['targets']:
                scaled_target = target.copy()
                if 'center' in scaled_target:
                    x, y = scaled_target['center']
                    scaled_target['center'] = (int(x*scale_x), int(y*scale_y))
                if 'radius' in scaled_target:
                    scaled_target['radius'] = int(scaled_target['radius'] * min(scale_x, scale_y))
                scaled_targets.append(scaled_target)
            
            display_frame = self.target_detector.draw_targets(display_frame, scaled_targets)
        
        # Display depth map (smaller)
        if 'depth_map' in results and results['depth_map'] is not None:
            depth_vis = self.depth_estimator.visualize_depth(results['depth_map'])
            if depth_vis is not None:
                depth_vis = cv2.resize(depth_vis, (display_width // 2, display_height // 2))
                cv2.imshow('Depth Map', depth_vis)
        
        # Add text overlay with performance stats
        y_offset = 25
        font_scale = 0.6
        thickness = 2
        
        # Frame info
        cv2.putText(display_frame, f"Frame: {self.frame_count}", (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
        
        # GPU info
        if self.depth_estimator and self.depth_estimator.device == 'cuda':
            y_offset += 25
            gpu_mem = torch.cuda.memory_allocated(0) / 1024**2  # MB
            cv2.putText(display_frame, f"GPU: {torch.cuda.get_device_name(0)[:15]} ({gpu_mem:.0f}MB)", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale-0.1, (0, 255, 0), thickness-1)
        
        # FPS
        if self.start_time:
            elapsed = time.time() - self.start_time
            fps = self.frame_count / elapsed if elapsed > 0 else 0
            y_offset += 25
            cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
        
        # VIO position
        if 'vio_success' in results and results['vio_success']:
            y_offset += 25
            pos = results['vio_position']
            cv2.putText(display_frame, f"VIO: [{pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}]",
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, font_scale-0.1, (0, 255, 0), thickness-1)
        
        # Autonomous navigation state
        if 'autonomous_nav' in results:
            nav = results['autonomous_nav']
            y_offset += 30
            
            # State indicator with color
            state = nav['state']
            if state == 'searching':
                color = (255, 255, 0)  # Cyan
            elif state in ['centering', 'approaching']:
                color = (0, 255, 255)  # Yellow
            elif state == 'target_locked':
                color = (0, 255, 0)  # Green
            elif state == 'avoiding_obstacle':
                color = (0, 165, 255)  # Orange
            elif state == 'emergency_stop':
                color = (0, 0, 255)  # Red
            else:
                color = (128, 128, 128)  # Gray
            
            cv2.putText(display_frame, f"AUTO: {state.upper()}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
            
            # Velocity command
            if 'velocity_command' in nav and nav['velocity_command']:
                vel = nav['velocity_command']
                y_offset += 25
                cv2.putText(display_frame, 
                           f"VEL: [{vel[0]:.2f}, {vel[1]:.2f}, {vel[2]:.2f}] m/s", 
                           (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale-0.1, (0, 255, 0), thickness-1)
            
            # Obstacle indicator
            if nav.get('obstacle_detected'):
                y_offset += 25
                cv2.putText(display_frame, "OBSTACLE DETECTED!", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 255), thickness)
        
        # Avoidance command overlay
        if 'avoidance_command' in results and results['avoidance_command']:
            avoid = results['avoidance_command']
            y_offset += 25
            cv2.putText(display_frame,
                       f"AVOID: {avoid['direction']} (dist: {avoid.get('min_distance', 0):.1f}m)",
                       (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale-0.1, (0, 165, 255), thickness-1)
        
        # Target detection status
        if 'targets' in results:
            num_targets = len(results['targets']) if results['targets'] else 0
            y_offset += 25
            target_color = (0, 255, 0) if num_targets > 0 else (128, 128, 128)
            cv2.putText(display_frame,
                       f"TARGETS: {num_targets} detected",
                       (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale-0.1, target_color, thickness-1)
        
        # Target command overlay (only if fusion occurred)
        if 'target_command' in results and results['target_command']:
            target = results['target_command']
            if target.get('approach', False):  # Only show if actually approaching
                y_offset += 25
                cv2.putText(display_frame,
                           f"TARGET: {target['action']} (dist: {target.get('distance', 0):.1f}m)",
                           (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale-0.1, (255, 0, 255), thickness-1)
        
        # Make window resizable
        cv2.namedWindow('DroneAutonomy Pipeline', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('DroneAutonomy Pipeline', display_width, display_height)
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
        
        # Stop autonomous controller
        if self.autonomous_controller is not None:
            self.autonomous_controller.stop()
        
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
    parser.add_argument('--interval', type=int, default=None, 
                       help='Process every Nth frame (default: depends on mode)')
    parser.add_argument('--fast', action='store_true', 
                       help='Fast mode: skip depth estimation for higher FPS')
    parser.add_argument('--auto-mode', action='store_true',
                       help='Skip interactive mode selection (use command-line args)')
    parser.add_argument('--autonomous', action='store_true',
                       help='Enable autonomous navigation with obstacle avoidance and target approach')
    
    args = parser.parse_args()
    
    # Interactive mode selection if not using command-line args
    if not args.auto_mode and not args.fast and args.interval is None:
        print("=" * 80)
        print("DroneAutonomy - Simplified Pipeline (YOLO-Free)")
        print("=" * 80)
        print()
        print("Active Features:")
        print("  ✓ Depth Anything V2 (480p) - Obstacle avoidance from depth map")
        print("  ✓ Circle Detection (OpenCV) - Red target tracking")
        print("  ✓ Autonomous Navigation - MAVLink control")
        print("  ✗ YOLO Detection - Removed for performance")
        print()
        print("Choose a performance mode:")
        print()
        print("  1. Full Quality Mode (~12 FPS)")
        print("     - Depth + Circle Detection every frame")
        print("     - Every frame processed")
        print("     - Best for: Maximum detail and accuracy")
        print()
        print("  2. Balanced Mode (~18 FPS) ⚡ [RECOMMENDED]")
        print("     - Depth + Circle Detection")
        print("     - Every 2nd frame processed")
        print("     - Best for: Real-time performance with good detail")
        print()
        print("  3. High Performance Mode (~28 FPS) 🚀")
        print("     - Depth + Circle Detection")
        print("     - Every 3rd frame processed")
        print("     - Best for: Maximum speed")
        print()
        print("Display Overlay:")
        print("  - FPS, Autonomous State, Velocity Commands")
        print("  - Obstacle Avoidance (direction & distance)")
        print("  - Target Approach Status")
        print()
        print("=" * 80)
        
        while True:
            try:
                choice = input("Enter mode (1-3) [default: 2]: ").strip()
                if choice == '':
                    choice = '2'
                
                mode = int(choice)
                if mode in [1, 2, 3]:
                    break
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
            except ValueError:
                print("Invalid input. Please enter a number between 1 and 3.")
            except KeyboardInterrupt:
                print("\n\nCancelled by user")
                return 0
        
        print()
        print("=" * 80)
        
        # Apply mode settings - depth always enabled
        if mode == 1:
            # Full Quality Mode
            args.fast = False
            args.interval = 1
            print("Selected: Full Quality Mode")
            print("  - Depth + Circle Detection: Every frame")
            print("  - Expected FPS: ~12")
            
        elif mode == 2:
            # Balanced Mode
            args.fast = False
            args.interval = 2
            print("Selected: Balanced Mode [RECOMMENDED]")
            print("  - Depth + Circle Detection: Every 2nd frame")
            print("  - Expected FPS: ~18")
            
        elif mode == 3:
            # High Performance Mode
            args.fast = False
            args.interval = 3
            print("Selected: High Performance Mode")
            print("  - Depth + Circle Detection: Every 3rd frame")
            print("  - Expected FPS: ~28")
        
        print("=" * 80)
        print("Starting pipeline... Press 'q' in video window to quit")
        print("=" * 80)
        print()
    
    # Default values if not set
    if args.interval is None:
        args.interval = 1
    
    # Create and run pipeline
    pipeline = DronePipeline(args.config)
    
    if pipeline.initialize():
        pipeline.run(
            display=not args.no_display,
            max_frames=args.max_frames,
            process_interval=args.interval,
            fast_mode=args.fast,
            autonomous=args.autonomous
        )
    else:
        logging.error("Failed to initialize pipeline")
        return 1
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
