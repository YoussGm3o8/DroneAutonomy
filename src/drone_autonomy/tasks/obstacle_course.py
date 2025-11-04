"""
Obstacle Course Task - Competition Task 3

Navigate through obstacle course using vision-based avoidance:
- Detect and avoid obstacles using depth estimation
- Follow designated path
- Minimize collisions
- Complete within time limit
"""

import numpy as np
from typing import Dict, Any, Optional, List

from .base_task import BaseTask, TaskStatus


class ObstacleCourseTask(BaseTask):
    """
    Obstacle Course Navigation Task
    
    Objective:
    - Navigate through obstacle course
    - Avoid collisions using depth estimation
    - Reach end goal
    - Complete within time limit
    
    Scoring:
    - Base 50 points for completing course
    - Penalties for obstacles hit (-10 per collision)
    - Time bonus for efficient navigation
    - Smoothness bonus for controlled flight
    """
    
    def __init__(
        self,
        task_id: str,
        config: Dict[str, Any],
        telemetry,
        logger=None
    ):
        """
        Initialize obstacle course task
        
        Args:
            task_id: Unique task identifier
            config: Task configuration
            telemetry: MAVLink telemetry interface
            logger: Logger instance
        """
        super().__init__(
            task_id=task_id,
            task_name="Obstacle Course Navigation",
            config=config,
            telemetry=telemetry,
            logger=logger
        )
        
        # Configuration
        self.obstacle_threshold = config.get('obstacle_threshold', 2.0)  # meters
        self.goal_position = config.get('goal_position', None)  # (lat, lon) tuple
        self.collision_penalty = config.get('collision_penalty', 10.0)
        
        # State
        self.obstacles_avoided = 0
        self.collisions_detected = 0
        self.course_progress = 0.0
        
        self.logger.info(f"Obstacle course task initialized")
        self.logger.info(f"  Obstacle threshold: {self.obstacle_threshold}m")
    
    def _on_start(self) -> bool:
        """Initialize obstacle course navigation"""
        self.obstacles_avoided = 0
        self.collisions_detected = 0
        self.course_progress = 0.0
        
        self.logger.info("Starting obstacle course navigation")
        return True
    
    def _on_update(
        self,
        frame,
        depth_map,
        detections: List[Dict],
        target_detection: Optional[Dict]
    ) -> bool:
        """
        Update obstacle course navigation
        
        Args:
            frame: Current camera frame
            depth_map: Depth estimation map
            detections: Object detections
            target_detection: Target detection (not used)
            
        Returns:
            True to continue, False when goal reached
        """
        # Analyze depth map for obstacles
        if depth_map is not None:
            obstacles_in_path = self._detect_obstacles(depth_map)
            
            if obstacles_in_path:
                self.logger.debug(f"Obstacles detected: {len(obstacles_in_path)}")
                self.obstacles_avoided += len(obstacles_in_path)
        
        # Check for collisions (using accelerometer data if available)
        collision = self._check_collision()
        if collision:
            self.collisions_detected += 1
            self.logger.warning(f"Collision detected! Total: {self.collisions_detected}")
        
        # Check if goal reached
        if self.goal_position and self.telemetry:
            current_lat = getattr(self.telemetry, 'latitude', 0.0)
            current_lon = getattr(self.telemetry, 'longitude', 0.0)
            goal_lat, goal_lon = self.goal_position
            
            distance = self._calculate_distance(current_lat, current_lon, goal_lat, goal_lon)
            
            if distance < 5.0:  # Within 5 meters of goal
                self.logger.info("Goal reached!")
                self.status = TaskStatus.COMPLETED
                return False
        
        return True
    
    def _detect_obstacles(self, depth_map) -> List[Dict]:
        """
        Detect obstacles in depth map
        
        Args:
            depth_map: Depth estimation map
            
        Returns:
            List of detected obstacles
        """
        obstacles = []
        
        # Analyze center region of depth map
        h, w = depth_map.shape
        center_region = depth_map[h//3:(2*h)//3, w//3:(2*w)//3]
        
        # Find close obstacles (high depth values indicate close objects)
        close_threshold = 0.7  # Relative depth threshold
        close_pixels = center_region > close_threshold
        
        if np.sum(close_pixels) > (close_pixels.size * 0.1):  # More than 10% close
            obstacles.append({
                'region': 'center',
                'coverage': np.sum(close_pixels) / close_pixels.size
            })
        
        return obstacles
    
    def _check_collision(self) -> bool:
        """
        Check for collision using telemetry data
        
        Returns:
            True if collision detected, False otherwise
        """
        # In real implementation, check accelerometer data for sudden impacts
        # For now, return False (placeholder)
        return False
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371000  # Earth radius in meters
        
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)
        
        a = sin(delta_lat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c
    
    def _calculate_score(self) -> float:
        """Calculate obstacle course score"""
        # Base score for completion
        if self.status == TaskStatus.COMPLETED:
            base_score = 50.0
        else:
            base_score = 0.0
        
        # Collision penalties
        collision_penalty = self.collisions_detected * self.collision_penalty
        
        # Time bonus
        time_bonus = max(0, (1.0 - self.elapsed_time / self.timeout) * 30.0)
        
        # Obstacle avoidance bonus
        avoidance_bonus = min(20.0, self.obstacles_avoided * 2.0)
        
        total_score = base_score + time_bonus + avoidance_bonus - collision_penalty
        
        return max(0, min(total_score, 100.0))
    
    def _on_stop(self):
        """Cleanup obstacle course navigation"""
        self.logger.info(f"Obstacle course complete")
        self.logger.info(f"Obstacles avoided: {self.obstacles_avoided}")
        self.logger.info(f"Collisions: {self.collisions_detected}")
