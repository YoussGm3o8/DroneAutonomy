"""
Autonomous Controller for Drone Navigation
Handles obstacle avoidance, target detection, centering, and approach
"""

import cv2
import numpy as np
import time
import logging
from enum import Enum
from typing import Optional, Tuple, Dict, Any
import csv
from pathlib import Path
from datetime import datetime

from .obstacle_avoidance import ObstacleAvoider


class NavigationState(Enum):
    """States for autonomous navigation"""
    IDLE = "idle"
    SEARCHING = "searching"
    TARGET_DETECTED = "target_detected"
    CENTERING = "centering"
    APPROACHING = "approaching"
    TARGET_LOCKED = "target_locked"
    AVOIDING_OBSTACLE = "avoiding_obstacle"
    EMERGENCY_STOP = "emergency_stop"


class AutonomousController:
    """
    Autonomous navigation controller
    
    Features:
    - Obstacle avoidance using depth estimation
    - Target detection and tracking
    - Camera centering on target
    - Safe approach with depth-based distance control
    - GPS/telemetry logging
    - Photo capture on target lock
    """
    
    def __init__(self, config: Dict[str, Any], telemetry, logger: logging.Logger):
        """
        Initialize autonomous controller
        
        Args:
            config: Configuration dictionary with navigation parameters
            telemetry: MAVLink telemetry interface
            logger: Logger instance
        """
        self.config = config
        self.telemetry = telemetry
        self.logger = logger
        
        # Navigation parameters
        self.obstacle_distance_threshold = config.get('obstacle_distance_threshold', 3.0)  # meters
        self.approach_distance_target = config.get('approach_distance_target', 2.0)  # meters
        self.approach_distance_min = config.get('approach_distance_min', 1.5)  # meters
        self.centering_tolerance = config.get('centering_tolerance', 50)  # pixels
        
        # PID gains for centering
        self.pid_kp = config.get('pid_kp', 0.5)
        self.pid_ki = config.get('pid_ki', 0.1)
        self.pid_kd = config.get('pid_kd', 0.2)
        
        # Speed limits
        self.max_yaw_rate = config.get('max_yaw_rate', 30.0)  # deg/s
        self.max_forward_speed = config.get('max_forward_speed', 1.0)  # m/s
        self.max_lateral_speed = config.get('max_lateral_speed', 0.5)  # m/s
        
        # State
        self.state = NavigationState.IDLE
        self.target_bbox = None
        self.target_depth = None
        
        # PID state
        self.error_integral_x = 0.0
        self.error_integral_y = 0.0
        self.last_error_x = 0.0
        self.last_error_y = 0.0
        self.last_update_time = time.time()
        
        # Logging
        self.log_dir = Path(config.get('log_dir', 'logs/autonomous'))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.photo_dir = Path(config.get('photo_dir', 'logs/autonomous/photos'))
        self.photo_dir.mkdir(parents=True, exist_ok=True)
        
        # CSV logging
        self.csv_file = self.log_dir / f"targets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self._init_csv()
        
        # Initialize obstacle avoidance system
        avoidance_config = config.get('obstacle_avoidance', {})
        avoidance_config['obstacle_distance_threshold'] = self.obstacle_distance_threshold
        self.obstacle_avoider = ObstacleAvoider(avoidance_config, logger)
        
        self.logger.info(f"AutonomousController initialized in state: {self.state.value}")
        self.logger.info(f"Obstacle threshold: {self.obstacle_distance_threshold}m")
        self.logger.info(f"Approach target: {self.approach_distance_target}m (min: {self.approach_distance_min}m)")
    
    def _init_csv(self):
        """Initialize CSV file for target logging"""
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'latitude', 'longitude', 'altitude_msl', 
                'altitude_rel', 'heading', 'distance_to_target', 
                'target_center_x', 'target_center_y', 'photo_filename'
            ])
        self.logger.info(f"Target log CSV created: {self.csv_file}")
    
    def update(self, frame: np.ndarray, depth_map: Optional[np.ndarray], 
               yolo_detections: list, target_detection: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main update loop for autonomous navigation
        
        Args:
            frame: Current camera frame
            depth_map: Depth estimation map (normalized 0-1, closer=darker)
            yolo_detections: YOLO detection results
            target_detection: Target detection result with bbox and center
        
        Returns:
            Dictionary with navigation commands and status
        """
        result = {
            'state': self.state.value,
            'velocity_command': None,
            'yaw_rate_command': None,
            'target_locked': False,
            'obstacle_detected': False,
            'avoidance_active': False
        }
        
        # Run obstacle detection
        if depth_map is not None:
            obstacles = self.obstacle_avoider.detect_obstacles(depth_map)
            result['obstacle_detected'] = len(obstacles) > 0
            
            # Generate path candidates
            target_position = None
            if target_detection and target_detection.get('detected'):
                target_position = target_detection['center']
            
            self.obstacle_avoider.generate_path_candidates(frame.shape, target_position)
            
            # Check if avoidance should be active
            target_detected = target_detection and target_detection.get('detected')
            target_distance = None
            if target_detected and self.target_depth:
                target_distance = self._depth_to_distance(self.target_depth)
            
            should_avoid = self.obstacle_avoider.should_avoid(target_detected, target_distance)
            result['avoidance_active'] = should_avoid
            
            if should_avoid and self.state not in [NavigationState.IDLE, NavigationState.EMERGENCY_STOP]:
                if self.state != NavigationState.AVOIDING_OBSTACLE:
                    self.logger.warning("Obstacle detected! Switching to avoidance mode")
                    self.state = NavigationState.AVOIDING_OBSTACLE
        
        # State machine
        if self.state == NavigationState.IDLE:
            # Waiting for activation
            pass
        
        elif self.state == NavigationState.SEARCHING:
            # Look for targets
            if target_detection and target_detection.get('detected'):
                self.target_bbox = target_detection['bbox']
                self.state = NavigationState.TARGET_DETECTED
                self.logger.info("Target detected! Switching to centering mode")
        
        elif self.state == NavigationState.TARGET_DETECTED:
            # Target found, start centering
            self.state = NavigationState.CENTERING
        
        elif self.state == NavigationState.CENTERING:
            if target_detection and target_detection.get('detected'):
                self.target_bbox = target_detection['bbox']
                
                # Calculate centering commands
                center_x, center_y = target_detection['center']
                frame_center_x = frame.shape[1] / 2
                frame_center_y = frame.shape[0] / 2
                
                error_x = center_x - frame_center_x
                error_y = center_y - frame_center_y
                
                # Check if centered
                if abs(error_x) < self.centering_tolerance and abs(error_y) < self.centering_tolerance:
                    self.logger.info("Target centered! Switching to approach mode")
                    self.state = NavigationState.APPROACHING
                else:
                    # Calculate PID control for yaw (horizontal centering)
                    yaw_rate = self._calculate_pid_yaw(error_x)
                    result['yaw_rate_command'] = yaw_rate
                    
                    # Send yaw command to MAVLink
                    if self.telemetry and self.telemetry.is_connected:
                        yaw_rate_rad = np.deg2rad(yaw_rate)
                        self.telemetry.send_velocity_body(0.0, 0.0, 0.0, yaw_rate_rad)
                        self.logger.debug(f"Sent centering yaw rate: {yaw_rate:.2f} deg/s")
                    
                    # Optionally add pitch control for vertical centering
                    # (not implemented - requires ANGLE mode or velocity control)
            else:
                # Lost target
                self.logger.warning("Target lost during centering. Returning to search")
                self.state = NavigationState.SEARCHING
        
        elif self.state == NavigationState.APPROACHING:
            if target_detection and target_detection.get('detected'):
                self.target_bbox = target_detection['bbox']
                center_x, center_y = target_detection['center']
                
                # Get depth at target location
                target_depth = self._get_target_depth(depth_map, center_x, center_y)
                self.target_depth = target_depth
                
                # Check if still centered
                frame_center_x = frame.shape[1] / 2
                error_x = center_x - frame_center_x
                
                if abs(error_x) > self.centering_tolerance * 1.5:
                    self.logger.warning("Target no longer centered during approach. Re-centering")
                    self.state = NavigationState.CENTERING
                else:
                    # Check distance
                    if target_depth is not None:
                        distance = self._depth_to_distance(target_depth)
                        
                        if distance <= self.approach_distance_target and distance >= self.approach_distance_min:
                            # Perfect distance - lock target
                            self.logger.info(f"Target locked at distance {distance:.2f}m!")
                            self.state = NavigationState.TARGET_LOCKED
                            result['target_locked'] = True
                            
                            # Log target and capture photo
                            self._log_target(frame, center_x, center_y, distance)
                        
                        elif distance > self.approach_distance_target:
                            # Too far - move forward
                            forward_speed = min(self.max_forward_speed, (distance - self.approach_distance_target) * 0.5)
                            velocity_cmd = {'forward': forward_speed, 'right': 0, 'down': 0}
                            result['velocity_command'] = velocity_cmd
                            
                            # Send velocity command to MAVLink
                            if self.telemetry and self.telemetry.is_connected:
                                self.telemetry.send_velocity_body(
                                    velocity_cmd['forward'],
                                    velocity_cmd['right'],
                                    velocity_cmd['down'],
                                    0.0
                                )
                                self.logger.debug(f"Sent approach velocity: forward={forward_speed:.2f} m/s")
                        
                        else:
                            # Too close - back up
                            self.logger.warning(f"Too close to target ({distance:.2f}m)! Backing up")
                            velocity_cmd = {'forward': -0.3, 'right': 0, 'down': 0}
                            result['velocity_command'] = velocity_cmd
                            
                            # Send backup command to MAVLink
                            if self.telemetry and self.telemetry.is_connected:
                                self.telemetry.send_velocity_body(-0.3, 0.0, 0.0, 0.0)
                                self.logger.debug("Sent backup velocity: forward=-0.3 m/s")
            else:
                # Lost target
                self.logger.warning("Target lost during approach. Returning to search")
                self.state = NavigationState.SEARCHING
        
        elif self.state == NavigationState.TARGET_LOCKED:
            # Target logged and photographed
            # Wait for next command or return to search
            self.logger.info("Target locked. Ready for next target")
            self.state = NavigationState.SEARCHING
        
        elif self.state == NavigationState.AVOIDING_OBSTACLE:
            # Use advanced obstacle avoidance system
            avoidance_command = self.obstacle_avoider.get_avoidance_command()
            
            if avoidance_command['avoid']:
                # Convert lateral command to velocity
                lateral_speed = avoidance_command['lateral'] * self.max_lateral_speed
                velocity_cmd = {
                    'forward': self.max_forward_speed * 0.3,  # Slow forward during avoidance
                    'right': lateral_speed,
                    'down': 0
                }
                result['velocity_command'] = velocity_cmd
                
                # Send velocity command to MAVLink
                if self.telemetry and self.telemetry.is_connected:
                    self.telemetry.send_velocity_body(
                        velocity_cmd['forward'],
                        velocity_cmd['right'],
                        velocity_cmd['down'],
                        0.0  # No yaw rate
                    )
                    self.logger.debug(f"Sent avoidance velocity: forward={velocity_cmd['forward']:.2f}, right={velocity_cmd['right']:.2f}")
            
            # Check if obstacle cleared
            if not self.obstacle_avoider.should_avoid(
                target_detection and target_detection.get('detected'),
                target_distance
            ):
                self.logger.info("Obstacle cleared. Returning to search mode")
                self.state = NavigationState.SEARCHING
        
        elif self.state == NavigationState.EMERGENCY_STOP:
            # Emergency stop - no commands
            velocity_cmd = {'forward': 0, 'right': 0, 'down': 0}
            result['velocity_command'] = velocity_cmd
            
            # Send stop command to MAVLink
            if self.telemetry and self.telemetry.is_connected:
                self.telemetry.send_velocity_body(0.0, 0.0, 0.0, 0.0)
                self.logger.debug("Sent emergency stop command")
        
        return result
    
    def _check_obstacles(self, depth_map: np.ndarray) -> bool:
        """
        Check for obstacles in depth map
        
        Args:
            depth_map: Depth estimation (0=far, 1=close)
        
        Returns:
            True if obstacle detected within threshold distance
        """
        if depth_map is None:
            return False
        
        # Check center region (where drone will move)
        h, w = depth_map.shape
        center_region = depth_map[h//3:2*h//3, w//3:2*w//3]
        
        # Depth map: 0 = far (white), 1 = close (black)
        # Higher values = closer = potential obstacle
        close_threshold = 0.7  # Corresponds to roughly < 3m
        
        obstacle_pixels = np.sum(center_region > close_threshold)
        obstacle_ratio = obstacle_pixels / center_region.size
        
        # If more than 10% of center region is close, consider it an obstacle
        return obstacle_ratio > 0.1
    
    def _calculate_avoidance_command(self, depth_map: np.ndarray) -> Dict[str, float]:
        """
        Calculate velocity command to avoid obstacles
        
        Args:
            depth_map: Depth estimation map
        
        Returns:
            Velocity command dictionary
        """
        if depth_map is None:
            return {'forward': 0, 'right': 0, 'down': 0}
        
        h, w = depth_map.shape
        
        # Divide view into left/center/right regions
        left_region = depth_map[:, :w//3]
        center_region = depth_map[:, w//3:2*w//3]
        right_region = depth_map[:, 2*w//3:]
        
        # Calculate average depth for each region (higher = closer)
        left_close = np.mean(left_region > 0.7)
        center_close = np.mean(center_region > 0.7)
        right_close = np.mean(right_region > 0.7)
        
        # Simple avoidance: move away from obstacles
        lateral_speed = 0.0
        
        if left_close > 0.2:
            # Obstacle on left - move right
            lateral_speed = self.max_lateral_speed
        elif right_close > 0.2:
            # Obstacle on right - move left
            lateral_speed = -self.max_lateral_speed
        
        # If center is blocked, back up
        forward_speed = 0.0
        if center_close > 0.3:
            forward_speed = -0.3
        
        return {'forward': forward_speed, 'right': lateral_speed, 'down': 0}
    
    def _calculate_pid_yaw(self, error_x: float) -> float:
        """
        Calculate yaw rate command using PID controller
        
        Args:
            error_x: Horizontal error in pixels (positive = target right of center)
        
        Returns:
            Yaw rate command in deg/s (positive = turn right)
        """
        current_time = time.time()
        dt = current_time - self.last_update_time
        
        if dt <= 0:
            dt = 0.01
        
        # PID calculation
        self.error_integral_x += error_x * dt
        error_derivative = (error_x - self.last_error_x) / dt
        
        # Calculate command
        yaw_rate = (self.pid_kp * error_x + 
                   self.pid_ki * self.error_integral_x + 
                   self.pid_kd * error_derivative)
        
        # Normalize by image width (1920 pixels -> max yaw rate)
        yaw_rate = yaw_rate / 1920.0 * self.max_yaw_rate
        
        # Clamp
        yaw_rate = np.clip(yaw_rate, -self.max_yaw_rate, self.max_yaw_rate)
        
        # Update state
        self.last_error_x = error_x
        self.last_update_time = current_time
        
        return yaw_rate
    
    def _get_target_depth(self, depth_map: np.ndarray, x: float, y: float) -> Optional[float]:
        """
        Get depth value at target location
        
        Args:
            depth_map: Depth estimation map
            x: Target x coordinate
            y: Target y coordinate
        
        Returns:
            Depth value (0=far, 1=close) or None
        """
        if depth_map is None:
            return None
        
        h, w = depth_map.shape
        
        # Sample region around target (not just single pixel)
        sample_radius = 20
        x_min = max(0, int(x) - sample_radius)
        x_max = min(w, int(x) + sample_radius)
        y_min = max(0, int(y) - sample_radius)
        y_max = min(h, int(y) + sample_radius)
        
        region = depth_map[y_min:y_max, x_min:x_max]
        
        # Use median to avoid outliers
        return np.median(region)
    
    def _depth_to_distance(self, depth_value: float) -> float:
        """
        Convert normalized depth value to estimated distance in meters
        
        Args:
            depth_value: Normalized depth (0=far, 1=close)
        
        Returns:
            Estimated distance in meters
        """
        # Depth Anything V2 provides relative depth, not metric
        # This is a rough approximation - needs calibration for real distances
        # Assuming: 0.0 = 10m, 1.0 = 0.5m (inverse relationship)
        
        # Inverse mapping: depth_value=1.0 -> 0.5m, depth_value=0.0 -> 10m
        min_dist = 0.5
        max_dist = 10.0
        
        distance = max_dist - (depth_value * (max_dist - min_dist))
        
        return max(min_dist, min(max_dist, distance))
    
    def _log_target(self, frame: np.ndarray, center_x: float, center_y: float, distance: float):
        """
        Log target information and capture photo
        
        Args:
            frame: Current camera frame
            center_x: Target center x coordinate
            center_y: Target center y coordinate
            distance: Estimated distance to target
        """
        # Get telemetry data
        telemetry_data = self.telemetry.get_data() if self.telemetry else {}
        
        timestamp = datetime.now().isoformat()
        lat = telemetry_data.get('latitude', None)
        lon = telemetry_data.get('longitude', None)
        alt_msl = telemetry_data.get('altitude_msl', None)
        alt_rel = telemetry_data.get('altitude_rel', None)
        heading = telemetry_data.get('heading', None)
        
        # Save photo
        photo_filename = f"target_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        photo_path = self.photo_dir / photo_filename
        cv2.imwrite(str(photo_path), frame)
        self.logger.info(f"Target photo saved: {photo_path}")
        
        # Log to CSV
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, lat, lon, alt_msl, alt_rel, heading,
                f"{distance:.2f}", int(center_x), int(center_y), photo_filename
            ])
        
        self.logger.info(f"Target logged: GPS=({lat}, {lon}), Alt={alt_rel}m, Heading={heading}°, Distance={distance:.2f}m")
    
    def start(self):
        """Start autonomous navigation (enter SEARCHING state)"""
        if self.state == NavigationState.IDLE:
            self.state = NavigationState.SEARCHING
            self.logger.info("Autonomous navigation STARTED - Entering SEARCHING mode")
    
    def stop(self):
        """Stop autonomous navigation (return to IDLE state)"""
        self.state = NavigationState.IDLE
        self.logger.info("Autonomous navigation STOPPED")
    
    def emergency_stop(self):
        """Emergency stop - halt all commands"""
        self.state = NavigationState.EMERGENCY_STOP
        self.logger.critical("EMERGENCY STOP ACTIVATED")
    
    def get_state(self) -> str:
        """Get current navigation state"""
        return self.state.value
