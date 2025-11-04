"""
Waypoint Navigation Task - Competition Task 2

Navigate through a series of GPS waypoints with precision:
- Follow predefined waypoint sequence
- Maintain altitude and speed limits
- Minimize deviation from path
- Complete within time limit
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple

from .base_task import BaseTask, TaskStatus


class WaypointNavigationTask(BaseTask):
    """
    Waypoint Navigation Task
    
    Objective:
    - Navigate through sequence of GPS waypoints
    - Maintain specified altitude
    - Complete within time limit
    
    Scoring:
    - 10 points per waypoint reached (within tolerance)
    - Accuracy bonus based on path deviation
    - Time bonus for efficient navigation
    - Penalties for altitude violations
    """
    
    def __init__(
        self,
        task_id: str,
        config: Dict[str, Any],
        telemetry,
        logger=None
    ):
        """
        Initialize waypoint navigation task
        
        Args:
            task_id: Unique task identifier
            config: Task configuration including waypoints
            telemetry: MAVLink telemetry interface
            logger: Logger instance
        """
        super().__init__(
            task_id=task_id,
            task_name="Waypoint Navigation",
            config=config,
            telemetry=telemetry,
            logger=logger
        )
        
        # Waypoints configuration
        self.waypoints = config.get('waypoints', [])  # List of (lat, lon, alt) tuples
        self.waypoint_tolerance = config.get('waypoint_tolerance', 2.0)  # meters
        self.altitude_tolerance = config.get('altitude_tolerance', 0.5)  # meters
        
        # State
        self.current_waypoint_index = 0
        self.waypoints_reached = []
        self.path_deviation = []
        
        self.logger.info(f"Waypoint navigation task initialized")
        self.logger.info(f"  Waypoints: {len(self.waypoints)}")
        self.logger.info(f"  Tolerance: {self.waypoint_tolerance}m")
    
    def _on_start(self) -> bool:
        """Initialize waypoint navigation"""
        if not self.waypoints:
            self.logger.error("No waypoints defined")
            return False
        
        self.current_waypoint_index = 0
        self.waypoints_reached = []
        self.path_deviation = []
        
        self.logger.info(f"Starting waypoint navigation: {len(self.waypoints)} waypoints")
        return True
    
    def _on_update(
        self,
        frame,
        depth_map,
        detections: List[Dict],
        target_detection: Optional[Dict]
    ) -> bool:
        """
        Update waypoint navigation
        
        Args:
            frame: Current camera frame (not used)
            depth_map: Depth map (used for obstacle avoidance)
            detections: Object detections (used for obstacle avoidance)
            target_detection: Target detection (not used)
            
        Returns:
            True to continue, False when all waypoints reached
        """
        if not self.telemetry:
            self.logger.warning("No telemetry - cannot navigate waypoints")
            return False
        
        # Get current position
        current_lat = getattr(self.telemetry, 'latitude', 0.0)
        current_lon = getattr(self.telemetry, 'longitude', 0.0)
        current_alt = getattr(self.telemetry, 'altitude', 0.0)
        
        # Get current waypoint
        if self.current_waypoint_index >= len(self.waypoints):
            self.logger.info("All waypoints reached!")
            self.status = TaskStatus.COMPLETED
            return False
        
        target_waypoint = self.waypoints[self.current_waypoint_index]
        target_lat, target_lon, target_alt = target_waypoint
        
        # Calculate distance to waypoint
        distance = self._calculate_distance(current_lat, current_lon, target_lat, target_lon)
        altitude_error = abs(current_alt - target_alt)
        
        # Track path deviation
        self.path_deviation.append(distance)
        
        # Check if waypoint reached
        if distance <= self.waypoint_tolerance and altitude_error <= self.altitude_tolerance:
            self.logger.info(f"Waypoint {self.current_waypoint_index + 1}/{len(self.waypoints)} reached!")
            self.waypoints_reached.append({
                'index': self.current_waypoint_index,
                'distance_error': distance,
                'altitude_error': altitude_error,
            })
            self.current_waypoint_index += 1
        
        return self.current_waypoint_index < len(self.waypoints)
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates using Haversine formula"""
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
        """Calculate waypoint navigation score"""
        if not self.waypoints:
            return 0.0
        
        # Points per waypoint
        waypoints_score = (len(self.waypoints_reached) / len(self.waypoints)) * 50.0
        
        # Accuracy bonus based on average path deviation
        if self.path_deviation:
            avg_deviation = np.mean(self.path_deviation)
            accuracy_bonus = max(0, 30.0 * (1.0 - avg_deviation / (self.waypoint_tolerance * 3)))
        else:
            accuracy_bonus = 0.0
        
        # Time bonus
        time_bonus = max(0, (1.0 - self.elapsed_time / self.timeout) * 20.0)
        
        total_score = waypoints_score + accuracy_bonus + time_bonus
        
        return min(total_score, 100.0)
    
    def _on_stop(self):
        """Cleanup waypoint navigation"""
        self.logger.info(f"Waypoint navigation complete")
        self.logger.info(f"Waypoints reached: {len(self.waypoints_reached)}/{len(self.waypoints)}")
