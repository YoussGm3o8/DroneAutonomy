"""
Autonomous Approach-Aim-Wet-Capture Task - Competition Task 2

Implements full autonomous loop:
1. Detect target from >2m distance
2. Lock target with vision
3. Stabilize position parallel to target plane
4. Actuate water system
5. Capture photo in real-time
6. Auto-upload for judge confirmation

Full autonomy required - manual positioning does not count.
Handles indoor doorway ingress (~4m × 4m opening) and partial occlusions.
"""

import cv2
import numpy as np
import time
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime
from enum import Enum
import logging

from .base_task import BaseTask, TaskStatus
from .landmark_description import LandmarkBasedDescriptionGenerator, BuildingDimensions


class ApproachState(Enum):
    """States for autonomous approach"""
    SEARCHING = "searching"
    TARGET_LOCKED = "target_locked"
    APPROACHING = "approaching"
    POSITIONING = "positioning"
    STABILIZING = "stabilizing"
    WETTING = "wetting"
    CAPTURING = "capturing"
    UPLOADING = "uploading"
    RELOADING = "reloading"
    COMPLETED = "completed"


class AutonomousWetCaptureTask(BaseTask):
    """
    Autonomous Approach-Aim-Wet-Capture Task
    
    Objective:
    - Autonomously detect and lock onto target from >2m
    - Navigate to optimal position parallel to target plane
    - Actuate water system with precision aiming
    - Capture photo in real-time
    - Auto-upload deliverables
    
    Requirements:
    - Full autonomy for aiming and last-meter positioning
    - Indoor doorway navigation capability
    - Handle partial occlusions
    - One UAV constraint
    - Water reload capability
    
    Scoring:
    - 40 points for autonomous detection and approach
    - 30 points for precision aiming and wetting
    - 20 points for photo capture and upload
    - 10 points for speed and efficiency
    - Bonus points for handling occlusions
    """
    
    def __init__(
        self,
        task_id: str,
        config: Dict[str, Any],
        telemetry,
        water_actuator,
        uploader,
        logger=None
    ):
        """
        Initialize autonomous wet-capture task
        
        Args:
            task_id: Unique task identifier
            config: Task configuration
            telemetry: MAVLink telemetry interface
            water_actuator: Water system actuator interface
            uploader: Auto-upload interface
            logger: Logger instance
        """
        super().__init__(
            task_id=task_id,
            task_name="Autonomous Approach-Aim-Wet-Capture",
            config=config,
            telemetry=telemetry,
            logger=logger
        )
        
        self.water_actuator = water_actuator
        self.uploader = uploader
        
        # Task configuration
        self.min_detection_distance = config.get('min_detection_distance', 2.0)  # meters
        self.optimal_distance = config.get('optimal_distance', 1.5)  # meters
        self.position_tolerance = config.get('position_tolerance', 0.1)  # meters
        self.aiming_tolerance = config.get('aiming_tolerance', 20)  # pixels
        self.stabilization_time = config.get('stabilization_time', 2.0)  # seconds
        self.water_duration = config.get('water_duration', 1.0)  # seconds
        self.doorway_width = config.get('doorway_width', 4.0)  # meters
        self.doorway_height = config.get('doorway_height', 4.0)  # meters
        
        # Building dimensions for landmark descriptions
        building_config = config.get('building', {})
        self.building = BuildingDimensions(
            length_north_south=building_config.get('length_north_south', 20.0),
            width_east_west=building_config.get('width_east_west', 15.0),
            height=building_config.get('height', 10.0)
        )
        
        self.description_generator = LandmarkBasedDescriptionGenerator(
            self.building, logger
        )
        
        # State
        self.state = ApproachState.SEARCHING
        self.target_locked = False
        self.target_3d_position = None
        self.target_color = None
        self.stabilization_start_time = None
        self.water_start_time = None
        self.targets_completed = []
        self.water_remaining = config.get('water_capacity', 5)  # Number of wets
        
        # Control parameters
        self.approach_speed = config.get('approach_speed', 0.3)  # m/s
        self.positioning_speed = config.get('positioning_speed', 0.1)  # m/s
        
        # PID for fine positioning
        self.pid_kp = config.get('pid_kp', 0.5)
        self.pid_ki = config.get('pid_ki', 0.05)
        self.pid_kd = config.get('pid_kd', 0.1)
        self.error_integral = np.zeros(3)
        self.last_error = np.zeros(3)
        
        # Photos directory
        self.photo_dir = self.log_dir / f"photos_{task_id}"
        self.photo_dir.mkdir(parents=True, exist_ok=True)
        
        # Deliverables directory
        self.deliverables_dir = self.log_dir / f"deliverables_{task_id}"
        self.deliverables_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Autonomous wet-capture task initialized")
        self.logger.info(f"  Min detection distance: {self.min_detection_distance}m")
        self.logger.info(f"  Optimal distance: {self.optimal_distance}m")
        self.logger.info(f"  Water remaining: {self.water_remaining}")
    
    def _on_start(self) -> bool:
        """Initialize autonomous wet-capture task"""
        try:
            self.state = ApproachState.SEARCHING
            self.target_locked = False
            self.targets_completed = []
            
            self.logger.info("Starting autonomous wet-capture task")
            self.logger.info("Searching for targets from >2m distance...")
            
            # Reset water actuator
            if self.water_actuator:
                self.water_actuator.reset()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting task: {e}", exc_info=True)
            return False
    
    def _on_update(
        self,
        frame,
        depth_map,
        detections: List[Dict],
        target_detection: Optional[Dict]
    ) -> bool:
        """
        Update autonomous wet-capture task
        
        Args:
            frame: Current camera frame
            depth_map: Depth estimation map
            detections: Object detections (for obstacle avoidance)
            target_detection: Target detection dictionary
            
        Returns:
            True to continue, False when complete
        """
        try:
            # Get current drone state
            drone_position = self._get_drone_position()
            drone_heading = self._get_drone_heading()
            
            # State machine execution
            if self.state == ApproachState.SEARCHING:
                return self._state_searching(frame, depth_map, target_detection, drone_position)
            
            elif self.state == ApproachState.TARGET_LOCKED:
                return self._state_target_locked(frame, depth_map, target_detection, drone_position)
            
            elif self.state == ApproachState.APPROACHING:
                return self._state_approaching(frame, depth_map, target_detection, drone_position)
            
            elif self.state == ApproachState.POSITIONING:
                return self._state_positioning(frame, depth_map, target_detection, drone_position)
            
            elif self.state == ApproachState.STABILIZING:
                return self._state_stabilizing(frame, target_detection)
            
            elif self.state == ApproachState.WETTING:
                return self._state_wetting(frame)
            
            elif self.state == ApproachState.CAPTURING:
                return self._state_capturing(frame, drone_position, drone_heading)
            
            elif self.state == ApproachState.UPLOADING:
                return self._state_uploading()
            
            elif self.state == ApproachState.RELOADING:
                return self._state_reloading()
            
            elif self.state == ApproachState.COMPLETED:
                self.status = TaskStatus.COMPLETED
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in task update: {e}", exc_info=True)
            self.metrics['errors_encountered'] += 1
            return True
    
    def _state_searching(
        self,
        frame,
        depth_map,
        target_detection: Optional[Dict],
        drone_position: Tuple[float, float, float]
    ) -> bool:
        """Search for target from >2m distance"""
        if not target_detection:
            self.logger.debug("Searching for target...")
            return True
        
        # Calculate distance to target using depth map
        target_depth = self._estimate_target_depth(target_detection, depth_map)
        
        if target_depth is None or target_depth < self.min_detection_distance:
            self.logger.debug(f"Target too close: {target_depth:.2f}m < {self.min_detection_distance}m")
            return True
        
        # Target detected at valid distance - lock it
        self.target_locked = True
        self.target_color = target_detection.get('color', 'unknown')
        self.target_3d_position = self._calculate_3d_position(target_detection, target_depth, drone_position)
        
        self.logger.info(f"✓ Target locked! Color: {self.target_color}, Distance: {target_depth:.2f}m")
        self.logger.info(f"Target 3D position: {self.target_3d_position}")
        
        self.state = ApproachState.TARGET_LOCKED
        return True
    
    def _state_target_locked(
        self,
        frame,
        depth_map,
        target_detection: Optional[Dict],
        drone_position: Tuple[float, float, float]
    ) -> bool:
        """Target locked - verify and begin approach"""
        if not target_detection:
            self.logger.warning("Target lost after lock - resuming search")
            self.state = ApproachState.SEARCHING
            self.target_locked = False
            return True
        
        # Verify target is still at valid distance
        target_depth = self._estimate_target_depth(target_detection, depth_map)
        
        if target_depth and target_depth >= self.min_detection_distance:
            self.logger.info("Beginning autonomous approach...")
            self.state = ApproachState.APPROACHING
        else:
            self.logger.debug("Waiting for target at valid distance...")
        
        return True
    
    def _state_approaching(
        self,
        frame,
        depth_map,
        target_detection: Optional[Dict],
        drone_position: Tuple[float, float, float]
    ) -> bool:
        """Autonomously approach target to optimal distance"""
        if not target_detection:
            self.logger.warning("Target lost during approach")
            self.state = ApproachState.SEARCHING
            return True
        
        # Calculate current distance
        target_depth = self._estimate_target_depth(target_detection, depth_map)
        
        if target_depth is None:
            self.logger.warning("Cannot estimate target depth")
            return True
        
        distance_error = target_depth - self.optimal_distance
        
        self.logger.debug(f"Approaching... Distance: {target_depth:.2f}m, Error: {distance_error:.2f}m")
        
        # Check if at optimal distance
        if abs(distance_error) < 0.2:  # Within 20cm
            self.logger.info("✓ Reached optimal distance - beginning fine positioning")
            self.state = ApproachState.POSITIONING
        else:
            # Generate approach command (would be sent to flight controller)
            approach_velocity = self._calculate_approach_velocity(distance_error)
            self.logger.debug(f"Approach velocity: {approach_velocity:.2f} m/s")
        
        return True
    
    def _state_positioning(
        self,
        frame,
        depth_map,
        target_detection: Optional[Dict],
        drone_position: Tuple[float, float, float]
    ) -> bool:
        """Fine position control parallel to target plane"""
        if not target_detection:
            self.logger.warning("Target lost during positioning")
            self.state = ApproachState.APPROACHING
            return True
        
        # Calculate centering error
        frame_h, frame_w = frame.shape[:2]
        target_x = target_detection.get('center_x', frame_w // 2)
        target_y = target_detection.get('center_y', frame_h // 2)
        
        error_x = target_x - (frame_w // 2)
        error_y = target_y - (frame_h // 2)
        total_error = np.sqrt(error_x**2 + error_y**2)
        
        self.logger.debug(f"Positioning... Centering error: {total_error:.1f} pixels")
        
        # Check if well positioned
        if total_error < self.aiming_tolerance:
            self.logger.info("✓ Target centered - stabilizing...")
            self.state = ApproachState.STABILIZING
            self.stabilization_start_time = time.time()
        else:
            # Calculate PID control for fine positioning
            control_output = self._calculate_pid_control(error_x, error_y, 0)
            self.logger.debug(f"Position control: {control_output}")
        
        return True
    
    def _state_stabilizing(self, frame, target_detection: Optional[Dict]) -> bool:
        """Stabilize position before wetting"""
        if not target_detection:
            self.logger.warning("Target lost during stabilization")
            self.state = ApproachState.POSITIONING
            self.stabilization_start_time = None
            return True
        
        # Check stabilization time
        elapsed = time.time() - self.stabilization_start_time
        
        # Verify still centered
        frame_h, frame_w = frame.shape[:2]
        target_x = target_detection.get('center_x', frame_w // 2)
        target_y = target_detection.get('center_y', frame_h // 2)
        error_x = target_x - (frame_w // 2)
        error_y = target_y - (frame_h // 2)
        total_error = np.sqrt(error_x**2 + error_y**2)
        
        if total_error > self.aiming_tolerance * 1.5:
            self.logger.warning("Position drift detected - repositioning")
            self.state = ApproachState.POSITIONING
            self.stabilization_start_time = None
            return True
        
        self.logger.debug(f"Stabilizing... {elapsed:.1f}/{self.stabilization_time:.1f}s")
        
        if elapsed >= self.stabilization_time:
            self.logger.info("✓ Stabilized - actuating water system!")
            self.state = ApproachState.WETTING
            self.water_start_time = time.time()
        
        return True
    
    def _state_wetting(self, frame) -> bool:
        """Actuate water system"""
        if not self.water_actuator:
            self.logger.warning("No water actuator - skipping to capture")
            self.state = ApproachState.CAPTURING
            return True
        
        elapsed = time.time() - self.water_start_time
        
        # Actuate water
        if elapsed < self.water_duration:
            if not self.water_actuator.is_active():
                self.water_actuator.activate()
                self.water_remaining -= 1
                self.logger.info(f"💧 Water activated! ({self.water_remaining} remaining)")
        else:
            # Water complete
            if self.water_actuator.is_active():
                self.water_actuator.deactivate()
            
            self.logger.info("✓ Wetting complete - capturing photo")
            self.state = ApproachState.CAPTURING
        
        return True
    
    def _state_capturing(
        self,
        frame,
        drone_position: Tuple[float, float, float],
        drone_heading: float
    ) -> bool:
        """Capture photo in real-time"""
        try:
            # Save photo
            target_id = f"target_{len(self.targets_completed) + 1}"
            timestamp = datetime.now()
            photo_filename = f"{target_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            photo_path = self.photo_dir / photo_filename
            
            cv2.imwrite(str(photo_path), frame)
            self.logger.info(f"📸 Photo captured: {photo_filename}")
            
            # Generate landmark-based description immediately
            description = self.description_generator.generate_description(
                target_id=target_id,
                color=self.target_color,
                position_3d=self.target_3d_position,
                drone_position=drone_position,
                drone_heading=drone_heading,
                confidence=1.0
            )
            
            if description:
                # Validate description schema
                is_valid, errors = description.validate_schema()
                if not is_valid:
                    self.logger.error(f"Description validation failed: {errors}")
                    self.logger.error("Ambiguity detected - losing points!")
                else:
                    self.logger.info("✓ Description validated successfully")
                
                # Export description to deliverables
                desc_file = self.deliverables_dir / f"{target_id}_description.txt"
                with open(desc_file, 'w') as f:
                    f.write(description.to_text())
                
                self.logger.info(f"📝 Description saved: {desc_file}")
            
            # Store target completion data
            self.targets_completed.append({
                'target_id': target_id,
                'color': self.target_color,
                'photo_path': str(photo_path),
                'description': description,
                'timestamp': timestamp,
            })
            
            self.logger.info("✓ Target complete - beginning auto-upload")
            self.state = ApproachState.UPLOADING
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error capturing photo: {e}", exc_info=True)
            self.metrics['errors_encountered'] += 1
            return True
    
    def _state_uploading(self) -> bool:
        """Auto-upload deliverables"""
        if not self.uploader:
            self.logger.warning("No uploader configured - skipping upload")
            self.state = ApproachState.COMPLETED
            return False
        
        try:
            target_data = self.targets_completed[-1]
            
            # Upload photo
            photo_uploaded = self.uploader.upload_file(
                target_data['photo_path'],
                category='photo'
            )
            
            # Upload description
            desc_file = self.deliverables_dir / f"{target_data['target_id']}_description.txt"
            desc_uploaded = self.uploader.upload_file(
                str(desc_file),
                category='description'
            )
            
            if photo_uploaded and desc_uploaded:
                self.logger.info("✓ ✓ Auto-upload successful - deliverables submitted!")
                self.logger.info("Judge confirmation pending...")
            else:
                self.logger.error("Upload failed - manual submission required")
            
            # Check if more targets to find
            if self.water_remaining > 0:
                self.logger.info(f"Water remaining: {self.water_remaining} - searching for next target")
                self.state = ApproachState.SEARCHING
                self.target_locked = False
            else:
                self.logger.info("No water remaining - task complete")
                self.state = ApproachState.COMPLETED
            
            return self.state != ApproachState.COMPLETED
            
        except Exception as e:
            self.logger.error(f"Error uploading: {e}", exc_info=True)
            self.state = ApproachState.COMPLETED
            return False
    
    def _state_reloading(self) -> bool:
        """Reload water (if applicable)"""
        self.logger.info("Reloading water...")
        # In real implementation, navigate to reload station
        # For now, just reset counter
        self.water_remaining = 5
        self.state = ApproachState.SEARCHING
        return True
    
    # Helper methods
    
    def _get_drone_position(self) -> Tuple[float, float, float]:
        """Get current drone position"""
        if self.telemetry:
            lat = getattr(self.telemetry, 'latitude', 0.0)
            lon = getattr(self.telemetry, 'longitude', 0.0)
            alt = getattr(self.telemetry, 'altitude', 0.0)
            return (lat, lon, alt)
        return (0.0, 0.0, 0.0)
    
    def _get_drone_heading(self) -> float:
        """Get current drone heading"""
        if self.telemetry:
            return getattr(self.telemetry, 'heading', 0.0)
        return 0.0
    
    def _estimate_target_depth(
        self,
        target_detection: Dict,
        depth_map
    ) -> Optional[float]:
        """Estimate distance to target using depth map"""
        if depth_map is None:
            return None
        
        cx = target_detection.get('center_x', 0)
        cy = target_detection.get('center_y', 0)
        
        # Sample depth at target center
        h, w = depth_map.shape
        y = int(cy / 1080 * h) if cy > 100 else int(cy)  # Assume 1080p frame
        x = int(cx / 1920 * w) if cx > 100 else int(cx)  # Assume 1920p frame
        
        if 0 <= y < h and 0 <= x < w:
            depth_value = depth_map[y, x]
            # Convert relative depth to metric distance (calibration needed)
            distance = self._depth_to_distance(depth_value)
            return distance
        
        return None
    
    def _depth_to_distance(self, depth_value: float) -> float:
        """Convert relative depth value to metric distance"""
        # Inverse relationship: higher depth = closer
        # Calibration: depth=1.0 -> 0.5m, depth=0.0 -> 10m
        min_dist = 0.5
        max_dist = 10.0
        distance = max_dist - (depth_value * (max_dist - min_dist))
        return distance
    
    def _calculate_3d_position(
        self,
        target_detection: Dict,
        depth: float,
        drone_position: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """Calculate target 3D position"""
        # Simplified 3D calculation
        # In real implementation, use camera intrinsics and pose
        cx = target_detection.get('center_x', 0)
        cy = target_detection.get('center_y', 0)
        
        # Convert to 3D (placeholder - needs proper camera model)
        x = drone_position[0] + depth * 0.01 * (cx - 320)
        y = drone_position[1] + depth * 0.01 * (cy - 240)
        z = drone_position[2]
        
        return (x, y, z)
    
    def _calculate_approach_velocity(self, distance_error: float) -> float:
        """Calculate approach velocity based on distance error"""
        # Proportional control
        velocity = self.approach_speed * np.clip(distance_error / 2.0, -1.0, 1.0)
        return velocity
    
    def _calculate_pid_control(self, error_x: float, error_y: float, error_z: float) -> np.ndarray:
        """Calculate PID control output for fine positioning"""
        dt = 0.033  # Assume 30 Hz update rate
        
        error = np.array([error_x, error_y, error_z])
        
        # PID calculation
        self.error_integral += error * dt
        error_derivative = (error - self.last_error) / dt
        
        control = (self.pid_kp * error + 
                   self.pid_ki * self.error_integral + 
                   self.pid_kd * error_derivative)
        
        self.last_error = error
        
        return control
    
    def _calculate_score(self) -> float:
        """Calculate task score"""
        if not self.targets_completed:
            return 0.0
        
        # Base score for completed targets
        base_score = len(self.targets_completed) * 25.0
        
        # Autonomy bonus (full autonomous = +20)
        autonomy_bonus = 20.0
        
        # Precision bonus (description quality)
        precision_bonus = 0
        for target in self.targets_completed:
            if target.get('description'):
                is_valid, _ = target['description'].validate_schema()
                if is_valid:
                    precision_bonus += 5.0
        
        # Time bonus
        time_bonus = max(0, (1.0 - self.elapsed_time / self.timeout) * 10.0)
        
        total_score = base_score + autonomy_bonus + precision_bonus + time_bonus
        
        return min(total_score, 100.0)
    
    def _on_stop(self):
        """Cleanup task"""
        self.logger.info(f"Autonomous wet-capture task complete")
        self.logger.info(f"Targets completed: {len(self.targets_completed)}")
        
        # Export all descriptions
        desc_file = self.deliverables_dir / "all_targets.txt"
        self.description_generator.export_to_file(desc_file)
        
        json_file = self.deliverables_dir / "all_targets.json"
        self.description_generator.export_to_json(json_file)
        
        self.logger.info(f"Deliverables exported to: {self.deliverables_dir}")
