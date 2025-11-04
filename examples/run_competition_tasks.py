"""
Competition Task Execution Example

Demonstrates how to run competition tasks with the DroneAutonomy system.

Usage:
    python examples/run_competition_tasks.py --config config/default_config.yaml --tasks target_search
    python examples/run_competition_tasks.py --tasks target_search waypoint obstacle precision --simulation
"""

import sys
import os
import argparse
import cv2
import logging

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from drone_autonomy.utils.config import Config
from drone_autonomy.utils.logger import setup_logging
from drone_autonomy.depth.depth_estimator import DepthEstimator
from drone_autonomy.detection.yolo_detector import YOLODetector
from drone_autonomy.detection.target_detector import TargetDetector
from drone_autonomy.video.stream import VideoStream
from drone_autonomy.mavlink.telemetry import MAVLinkTelemetry
from drone_autonomy.simulation.airsim_interface import AirSimInterface

# Import competition tasks
from drone_autonomy.tasks import (
    TaskManager,
    TargetSearchTask,
    WaypointNavigationTask,
    ObstacleCourseTask,
    PrecisionLandingTask,
)


def create_task(task_type: str, task_id: str, config: dict, telemetry, logger) -> object:
    """
    Create task instance based on type
    
    Args:
        task_type: Type of task ('target_search', 'waypoint', 'obstacle', 'precision')
        task_id: Unique task identifier
        config: Task configuration
        telemetry: MAVLink telemetry interface
        logger: Logger instance
        
    Returns:
        Task instance
    """
    task_configs = {
        'target_search': {
            'target_count_required': config.get('target_count', 3),
            'search_altitude': 5.0,
            'centering_accuracy': 30,
            'identification_time_bonus': 5.0,
            'timeout': 300.0,  # 5 minutes
            'log_dir': 'logs/competition/target_search',
        },
        'waypoint': {
            'waypoints': config.get('waypoints', [
                (47.6062, -122.3321, 10.0),  # Example waypoints (Seattle area)
                (47.6065, -122.3325, 10.0),
                (47.6068, -122.3329, 10.0),
            ]),
            'waypoint_tolerance': 2.0,
            'altitude_tolerance': 0.5,
            'timeout': 300.0,
            'log_dir': 'logs/competition/waypoint',
        },
        'obstacle': {
            'obstacle_threshold': 2.0,
            'goal_position': config.get('goal_position', None),
            'collision_penalty': 10.0,
            'timeout': 300.0,
            'log_dir': 'logs/competition/obstacle',
        },
        'precision': {
            'landing_altitude': 5.0,
            'descent_rate': 0.5,
            'centering_tolerance': 50,
            'landing_tolerance': 1.0,
            'timeout': 180.0,  # 3 minutes
            'log_dir': 'logs/competition/precision',
        },
    }
    
    task_classes = {
        'target_search': TargetSearchTask,
        'waypoint': WaypointNavigationTask,
        'obstacle': ObstacleCourseTask,
        'precision': PrecisionLandingTask,
    }
    
    if task_type not in task_classes:
        raise ValueError(f"Unknown task type: {task_type}")
    
    task_config = task_configs[task_type]
    task_class = task_classes[task_type]
    
    return task_class(task_id, task_config, telemetry, logger)


def main():
    """Main competition execution"""
    parser = argparse.ArgumentParser(description='Run DroneAutonomy Competition Tasks')
    parser.add_argument('--config', type=str, default='config/default_config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--tasks', nargs='+', 
                        choices=['target_search', 'waypoint', 'obstacle', 'precision'],
                        default=['target_search'],
                        help='Tasks to run (in order)')
    parser.add_argument('--simulation', action='store_true',
                        help='Use AirSim simulation')
    parser.add_argument('--webcam', action='store_true',
                        help='Use webcam instead of RTSP stream')
    parser.add_argument('--no-display', action='store_true',
                        help='Disable display windows')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging()
    logger.info("=" * 80)
    logger.info("DroneAutonomy Competition Task Execution")
    logger.info("=" * 80)
    logger.info(f"Tasks: {', '.join(args.tasks)}")
    logger.info(f"Simulation: {args.simulation}")
    logger.info("=" * 80)
    
    # Load configuration
    config = Config(args.config)
    
    # Initialize components
    try:
        # Video source
        if args.simulation:
            logger.info("Initializing AirSim simulation...")
            airsim = AirSimInterface(config.config.get('simulation', {}))
            if not airsim.connect():
                logger.error("Failed to connect to AirSim")
                return 1
            video_stream = None
        else:
            if args.webcam:
                config.config['video']['backend'] = 'opencv'
                config.config['video']['camera_id'] = 0
            
            logger.info("Initializing video stream...")
            video_stream = VideoStream(config.config.get('video', {}))
            if not video_stream.start():
                logger.error("Failed to start video stream")
                return 1
            airsim = None
        
        # Depth estimator
        logger.info("Loading depth estimation model...")
        depth_config = config.config.get('depth', {})
        depth_estimator = DepthEstimator(depth_config)
        if not depth_estimator.load_model():
            logger.error("Failed to load depth model")
            return 1
        
        # YOLO detector
        logger.info("Loading YOLO model...")
        yolo_config = config.config.get('detection', {})
        yolo_detector = YOLODetector(yolo_config)
        if not yolo_detector.load_model():
            logger.error("Failed to load YOLO model")
            return 1
        
        # Target detector
        logger.info("Initializing target detector...")
        target_config = config.config.get('target_detection', {})
        target_detector = TargetDetector(target_config)
        
        # MAVLink telemetry (optional)
        telemetry = None
        mavlink_config = config.config.get('mavlink', {})
        if not args.simulation and mavlink_config.get('enabled', True):
            logger.info("Connecting to MAVLink...")
            try:
                telemetry = MAVLinkTelemetry(mavlink_config)
                telemetry.connect()
            except Exception as e:
                logger.warning(f"MAVLink connection failed: {e}")
                logger.info("Continuing without telemetry...")
        
        # Create task manager
        logger.info("Initializing task manager...")
        task_manager_config = {
            'max_tasks': 10,
            'auto_advance': True,
            'stop_on_failure': False,
            'log_dir': 'logs/competition',
        }
        task_manager = TaskManager(task_manager_config, telemetry, logger)
        
        # Add tasks to manager
        for i, task_type in enumerate(args.tasks):
            task_id = f"{task_type}_{i+1}"
            task = create_task(task_type, task_id, config.config, telemetry, logger)
            task_manager.add_task(task)
        
        logger.info(f"Added {len(args.tasks)} tasks to manager")
        
        # Start competition
        logger.info("\nStarting competition...")
        if not task_manager.start_competition():
            logger.error("Failed to start competition")
            return 1
        
        # Main processing loop
        frame_count = 0
        try:
            while True:
                # Get frame
                if airsim:
                    frame = airsim.get_image()
                else:
                    frame = video_stream.read()
                
                if frame is None:
                    logger.warning("No frame received")
                    break
                
                frame_count += 1
                
                # Estimate depth
                depth_map, depth_time = depth_estimator.estimate_depth(frame)
                
                # Detect objects
                detections, det_time = yolo_detector.detect(frame)
                
                # Detect target
                target_detection, target_frame = target_detector.detect(frame)
                
                # Update task manager
                continue_competition = task_manager.update(
                    frame, depth_map, detections, target_detection
                )
                
                if not continue_competition:
                    logger.info("Competition complete!")
                    break
                
                # Display (optional)
                if not args.no_display:
                    display_frame = frame.copy()
                    
                    # Draw target if detected
                    if target_detection:
                        cx = target_detection['center_x']
                        cy = target_detection['center_y']
                        radius = target_detection['radius']
                        cv2.circle(display_frame, (cx, cy), radius, (0, 255, 0), 2)
                        cv2.circle(display_frame, (cx, cy), 3, (0, 0, 255), -1)
                    
                    # Draw YOLO detections
                    for det in detections:
                        bbox = det['bbox']
                        label = det['label']
                        conf = det['confidence']
                        x1, y1, x2, y2 = bbox
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                        cv2.putText(display_frame, f"{label} {conf:.2f}", (x1, y1-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    
                    # Show current task
                    if task_manager.current_task:
                        task_info = f"Task: {task_manager.current_task.task_name}"
                        cv2.putText(display_frame, task_info, (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    cv2.imshow("Competition", display_frame)
                    
                    # Depth visualization
                    if depth_map is not None:
                        depth_vis = depth_estimator.visualize_depth(depth_map)
                        cv2.imshow("Depth", depth_vis)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        logger.info("User quit")
                        break
                    elif key == ord('p'):
                        logger.info("Paused - press any key to continue")
                        cv2.waitKey(0)
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        
        # Stop competition and get results
        logger.info("\nStopping competition...")
        competition_result = task_manager.stop_competition()
        
        logger.info("\n" + "=" * 80)
        logger.info("FINAL RESULTS")
        logger.info("=" * 80)
        logger.info(f"Total Score: {competition_result.total_score:.1f}")
        logger.info(f"Tasks Completed: {competition_result.tasks_completed}/{len(args.tasks)}")
        logger.info(f"Tasks Failed: {competition_result.tasks_failed}/{len(args.tasks)}")
        logger.info(f"Total Duration: {competition_result.total_duration:.2f}s")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error during competition: {e}", exc_info=True)
        return 1
    
    finally:
        # Cleanup
        if video_stream:
            video_stream.stop()
        if airsim:
            airsim.disconnect()
        if telemetry:
            telemetry.disconnect()
        cv2.destroyAllWindows()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
