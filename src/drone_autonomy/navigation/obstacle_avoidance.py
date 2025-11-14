"""
Advanced Obstacle Avoidance Module with Tesla-Style Visualization

Features:
- Depth-based obstacle detection
- Multi-path trajectory planning
- Real-time path visualization (Tesla Autopilot style)
- Integration with target detection
- Safety zone monitoring
- Collision risk assessment
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging


class ObstacleType(Enum):
    """Types of detected obstacles"""
    STATIC = "static"
    DYNAMIC = "dynamic"
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    """
    Collision risk levels with severity ordering
    Lower value = safer, Higher value = more dangerous
    """
    SAFE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    
    def get_name(self) -> str:
        """Get risk level name as string"""
        names = {
            0: "safe",
            1: "low",
            2: "medium",
            3: "high",
            4: "critical"
        }
        return names[self.value]


@dataclass
class Obstacle:
    """
    Detected obstacle
    
    Attributes:
        position: (x, y) in image coordinates
        distance: Distance in meters
        size: (width, height) in pixels
        risk: Collision risk level
        type: Obstacle type
        velocity: Estimated velocity (dx, dy) if dynamic
    """
    position: Tuple[int, int]
    distance: float
    size: Tuple[int, int]
    risk: RiskLevel
    type: ObstacleType = ObstacleType.UNKNOWN
    velocity: Tuple[float, float] = (0.0, 0.0)
    
    def get_safety_radius(self) -> float:
        """Calculate required safety radius"""
        base_radius = 2.0  # meters
        if self.risk == RiskLevel.CRITICAL:
            return base_radius * 2.0
        elif self.risk == RiskLevel.HIGH:
            return base_radius * 1.5
        return base_radius


@dataclass
class PathSegment:
    """
    Trajectory path segment
    
    Attributes:
        points: List of (x, y) waypoints in image coordinates
        cost: Path cost (lower is better)
        clearance: Minimum clearance to obstacles
        curvature: Path curvature measure
        is_safe: Whether path avoids all obstacles
    """
    points: List[Tuple[int, int]]
    cost: float
    clearance: float
    curvature: float
    is_safe: bool


class ObstacleAvoider:
    """
    Advanced obstacle avoidance system with path visualization
    
    Features:
    - Depth map analysis for obstacle detection
    - Multiple path generation and evaluation
    - Tesla-style visualization overlay
    - Integration with target detection
    - Configurable safety parameters
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize obstacle avoidance system
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Obstacle detection parameters
        self.obstacle_distance_threshold = config.get('obstacle_distance_threshold', 3.0)  # meters
        self.critical_distance = config.get('critical_distance', 1.5)  # meters
        self.warning_distance = config.get('warning_distance', 2.5)  # meters
        
        # Detection zones (image regions)
        self.num_zones_horizontal = config.get('num_zones_horizontal', 5)
        self.num_zones_vertical = config.get('num_zones_vertical', 3)
        
        # Path planning parameters
        self.num_path_candidates = config.get('num_path_candidates', 5)
        self.path_horizon = config.get('path_horizon', 50)  # pixels ahead
        self.path_lateral_range = config.get('path_lateral_range', 100)  # pixels left/right
        
        # Safety parameters
        self.min_clearance = config.get('min_clearance', 1.0)  # meters
        self.safety_margin = config.get('safety_margin', 0.5)  # meters
        
        # Visualization parameters
        self.show_zones = config.get('show_zones', True)
        self.show_paths = config.get('show_paths', True)
        self.show_obstacles = config.get('show_obstacles', True)
        self.path_alpha = config.get('path_alpha', 0.6)
        
        # State
        self.detected_obstacles: List[Obstacle] = []
        self.current_paths: List[PathSegment] = []
        self.selected_path: Optional[PathSegment] = None
        self.avoidance_active = False
        self.feature_enabled = True
        
        # Target detection integration
        self.target_priority = config.get('target_priority', True)
        self.target_override_distance = config.get('target_override_distance', 5.0)  # meters
        
        self.logger.info("Obstacle Avoidance System initialized")
        self.logger.info(f"  Obstacle threshold: {self.obstacle_distance_threshold}m")
        self.logger.info(f"  Critical distance: {self.critical_distance}m")
        self.logger.info(f"  Min clearance: {self.min_clearance}m")
    
    def set_feature_enabled(self, enabled: bool) -> None:
        """Enable or disable obstacle avoidance processing/visualization."""
        self.feature_enabled = enabled
        if not enabled:
            # Clear runtime state so visualization reflects disabled mode
            self.detected_obstacles = []
            self.current_paths = []
            self.selected_path = None
            self.avoidance_active = False

    def detect_obstacles(
        self,
        depth_map: np.ndarray,
        confidence_threshold: float = 0.8
    ) -> List[Obstacle]:
        """
        Detect obstacles from depth map
        
        Args:
            depth_map: Depth estimation map (HxW)
            confidence_threshold: Minimum confidence for detection
            
        Returns:
            List of detected obstacles
        """
        if depth_map is None or depth_map.size == 0:
            return []
        
        obstacles = []
        h, w = depth_map.shape[:2]
        
        # Convert depth map to distance (assuming normalized 0-1 depth)
        # This is a simplified conversion - adjust based on depth model
        max_depth = 10.0  # meters
        distance_map = depth_map * max_depth
        
        # Divide image into detection zones
        zone_h = h // self.num_zones_vertical
        zone_w = w // self.num_zones_horizontal
        
        for i in range(self.num_zones_vertical):
            for j in range(self.num_zones_horizontal):
                # Extract zone
                y1 = i * zone_h
                y2 = min((i + 1) * zone_h, h)
                x1 = j * zone_w
                x2 = min((j + 1) * zone_w, w)
                
                zone = distance_map[y1:y2, x1:x2]
                
                if zone.size == 0:
                    continue
                
                # Calculate zone statistics
                min_distance = np.min(zone)
                mean_distance = np.mean(zone)
                
                # Check if zone contains obstacle
                if min_distance < self.obstacle_distance_threshold:
                    # Determine risk level
                    if min_distance < self.critical_distance:
                        risk = RiskLevel.CRITICAL
                    elif min_distance < self.warning_distance:
                        risk = RiskLevel.HIGH
                    elif min_distance < self.obstacle_distance_threshold:
                        risk = RiskLevel.MEDIUM
                    else:
                        risk = RiskLevel.LOW
                    
                    # Create obstacle
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    
                    obstacle = Obstacle(
                        position=(center_x, center_y),
                        distance=min_distance,
                        size=(x2 - x1, y2 - y1),
                        risk=risk,
                        type=ObstacleType.STATIC
                    )
                    
                    obstacles.append(obstacle)
        
        self.detected_obstacles = obstacles
        self.logger.debug(f"Detected {len(obstacles)} obstacles")
        
        return obstacles
    
    def generate_path_candidates(
        self,
        frame_shape: Tuple[int, int],
        current_target: Optional[Tuple[int, int]] = None
    ) -> List[PathSegment]:
        """
        Generate multiple path candidates
        
        Args:
            frame_shape: (height, width) of frame
            current_target: Current target position if following a target
            
        Returns:
            List of path candidates
        """
        h, w = frame_shape[:2]
        
        # Start point (center bottom of frame - vehicle position)
        start_x = w // 2
        start_y = h - 50
        
        # Generate paths
        paths = []
        
        # Central path (straight ahead)
        if current_target:
            # Path toward target
            end_x, end_y = current_target
        else:
            # Default forward path
            end_x = w // 2
            end_y = h // 2 - self.path_horizon
        
        # Generate multiple candidate paths
        for i in range(self.num_path_candidates):
            # Lateral offset for each candidate
            offset = (i - self.num_path_candidates // 2) * (self.path_lateral_range // self.num_path_candidates)
            
            # Generate smooth curve using quadratic bezier
            points = self._generate_bezier_path(
                start_x, start_y,
                start_x + offset, start_y - self.path_horizon // 2,
                end_x + offset, end_y,
                num_points=20
            )
            
            # Evaluate path
            cost = self._evaluate_path_cost(points, current_target)
            clearance = self._calculate_path_clearance(points)
            curvature = self._calculate_curvature(points)
            is_safe = clearance >= self.min_clearance
            
            path = PathSegment(
                points=points,
                cost=cost,
                clearance=clearance,
                curvature=curvature,
                is_safe=is_safe
            )
            
            paths.append(path)
        
        self.current_paths = paths
        
        # Select best path
        safe_paths = [p for p in paths if p.is_safe]
        if safe_paths:
            self.selected_path = min(safe_paths, key=lambda p: p.cost)
        else:
            # Emergency: select path with best clearance
            self.selected_path = max(paths, key=lambda p: p.clearance)
            if self.feature_enabled:
                self.logger.warning("No safe path found - selecting best available")
        
        return paths
    
    def _generate_bezier_path(
        self,
        x0: int, y0: int,
        x1: int, y1: int,
        x2: int, y2: int,
        num_points: int = 20
    ) -> List[Tuple[int, int]]:
        """Generate smooth Bezier curve path"""
        t = np.linspace(0, 1, num_points)
        
        # Quadratic Bezier formula
        x = (1 - t)**2 * x0 + 2 * (1 - t) * t * x1 + t**2 * x2
        y = (1 - t)**2 * y0 + 2 * (1 - t) * t * y1 + t**2 * y2
        
        points = [(int(x[i]), int(y[i])) for i in range(num_points)]
        return points
    
    def _evaluate_path_cost(
        self,
        path_points: List[Tuple[int, int]],
        target: Optional[Tuple[int, int]]
    ) -> float:
        """
        Calculate path cost
        
        Lower cost = better path
        """
        cost = 0.0
        
        # Distance to obstacles
        for point in path_points:
            min_obstacle_dist = float('inf')
            for obstacle in self.detected_obstacles:
                dist = np.linalg.norm(
                    np.array(point) - np.array(obstacle.position)
                )
                min_obstacle_dist = min(min_obstacle_dist, dist)
            
            # Penalize paths near obstacles
            if min_obstacle_dist < 100:  # pixels
                cost += (100 - min_obstacle_dist) / 10.0
        
        # Path length
        path_length = sum(
            np.linalg.norm(
                np.array(path_points[i+1]) - np.array(path_points[i])
            )
            for i in range(len(path_points) - 1)
        )
        cost += path_length / 100.0
        
        # Distance to target (if following target)
        if target:
            end_point = path_points[-1]
            target_dist = np.linalg.norm(
                np.array(end_point) - np.array(target)
            )
            cost += target_dist / 50.0
        
        return cost
    
    def _calculate_path_clearance(self, path_points: List[Tuple[int, int]]) -> float:
        """Calculate minimum clearance to obstacles along path"""
        if not self.detected_obstacles:
            return float('inf')
        
        min_clearance = float('inf')
        
        for point in path_points:
            for obstacle in self.detected_obstacles:
                # Distance in pixels
                pixel_dist = np.linalg.norm(
                    np.array(point) - np.array(obstacle.position)
                )
                
                # Convert to meters (approximate)
                # Assuming obstacle.distance gives depth
                clearance = (pixel_dist / 100.0) * obstacle.distance
                
                min_clearance = min(min_clearance, clearance)
        
        return min_clearance
    
    def _calculate_curvature(self, path_points: List[Tuple[int, int]]) -> float:
        """Calculate path curvature measure"""
        if len(path_points) < 3:
            return 0.0
        
        total_curvature = 0.0
        
        for i in range(len(path_points) - 2):
            p0 = np.array(path_points[i])
            p1 = np.array(path_points[i + 1])
            p2 = np.array(path_points[i + 2])
            
            # Calculate angle change
            v1 = p1 - p0
            v2 = p2 - p1
            
            if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                cos_angle = np.clip(cos_angle, -1.0, 1.0)
                angle = np.arccos(cos_angle)
                total_curvature += angle
        
        return total_curvature
    
    def should_avoid(
        self,
        target_detected: bool = False,
        target_distance: Optional[float] = None
    ) -> bool:
        """
        Determine if obstacle avoidance should be active
        
        Args:
            target_detected: Whether a target is currently detected
            target_distance: Distance to target if detected
            
        Returns:
            True if avoidance should be active
        """
        # Check for critical obstacles
        critical_obstacles = [
            obs for obs in self.detected_obstacles
            if obs.risk in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        ]
        
        if critical_obstacles:
            self.avoidance_active = True
            return True
        
        # If target priority is enabled and target is close
        if self.target_priority and target_detected:
            if target_distance and target_distance < self.target_override_distance:
                # Target is close - disable avoidance to allow approach
                self.avoidance_active = False
                return False
        
        # Check for any obstacles within threshold
        if self.detected_obstacles:
            self.avoidance_active = True
            return True
        
        self.avoidance_active = False
        return False
    
    def get_avoidance_command(self) -> Dict[str, Any]:
        """
        Get avoidance command for drone control
        
        Returns:
            Command dictionary with movement adjustments
        """
        if not self.selected_path or not self.avoidance_active:
            return {'avoid': False}
        
        # Calculate steering based on selected path
        if len(self.selected_path.points) < 2:
            return {'avoid': False}
        
        # Get next waypoint
        next_point = self.selected_path.points[len(self.selected_path.points) // 3]
        
        # Calculate lateral offset from center
        frame_center = 320  # Assuming 640px width
        lateral_offset = next_point[0] - frame_center
        
        # Normalize to -1 to 1
        lateral_command = np.clip(lateral_offset / 320.0, -1.0, 1.0)
        
        return {
            'avoid': True,
            'lateral': lateral_command,
            'clearance': self.selected_path.clearance,
            'risk': self._get_maximum_risk()
        }
    
    def _get_maximum_risk(self) -> str:
        """Get maximum risk level from detected obstacles"""
        if not self.detected_obstacles:
            return "safe"
        
        # Get risk level with highest integer value
        max_risk_enum = max(self.detected_obstacles, key=lambda obs: obs.risk.value).risk
        return max_risk_enum.get_name()
    
    def visualize(
        self,
        frame: np.ndarray,
        depth_map: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Create Tesla-style visualization overlay
        
        Args:
            frame: Input frame
            depth_map: Depth map for visualization
            
        Returns:
            Frame with visualization overlay
        """
        overlay = frame.copy()
        h, w = frame.shape[:2]
        
        # Create semi-transparent overlay
        viz_overlay = np.zeros_like(frame, dtype=np.uint8)
        
        # 1. Draw detection zones
        if self.show_zones:
            self._draw_detection_zones(viz_overlay, (h, w))
        
        # 2. Draw obstacles
        if self.show_obstacles and self.detected_obstacles:
            self._draw_obstacles(viz_overlay)
        
        # 3. Draw path candidates
        if self.show_paths and self.current_paths:
            self._draw_paths(viz_overlay)
        
        # 4. Draw selected path (highlighted)
        if self.selected_path:
            self._draw_selected_path(viz_overlay)
        
        # 5. Draw vehicle indicator
        self._draw_vehicle_indicator(viz_overlay, (h, w))
        
        # 6. Draw status HUD
        self._draw_status_hud(viz_overlay, (h, w))
        
        # Apply disabled styling if feature is off
        overlay_alpha = self.path_alpha
        if not self.feature_enabled:
            viz_overlay = self._apply_disabled_style(viz_overlay, (h, w))
            overlay_alpha = min(self.path_alpha, 0.35)
        
        # Blend overlay with frame
        result = cv2.addWeighted(frame, 1.0, viz_overlay, overlay_alpha, 0)
        
        return result
    
    def _draw_detection_zones(self, overlay: np.ndarray, shape: Tuple[int, int]):
        """Draw detection zone grid"""
        h, w = shape
        zone_h = h // self.num_zones_vertical
        zone_w = w // self.num_zones_horizontal
        
        # Draw grid lines
        for i in range(1, self.num_zones_vertical):
            y = i * zone_h
            cv2.line(overlay, (0, y), (w, y), (50, 50, 50), 1)
        
        for j in range(1, self.num_zones_horizontal):
            x = j * zone_w
            cv2.line(overlay, (x, 0), (x, h), (50, 50, 50), 1)
    
    def _draw_obstacles(self, overlay: np.ndarray):
        """Draw detected obstacles"""
        for obstacle in self.detected_obstacles:
            x, y = obstacle.position
            w, h = obstacle.size
            
            # Color based on risk
            if obstacle.risk == RiskLevel.CRITICAL:
                color = (0, 0, 255)  # Red
            elif obstacle.risk == RiskLevel.HIGH:
                color = (0, 165, 255)  # Orange
            elif obstacle.risk == RiskLevel.MEDIUM:
                color = (0, 255, 255)  # Yellow
            else:
                color = (0, 255, 0)  # Green
            
            # Draw obstacle rectangle
            cv2.rectangle(
                overlay,
                (x - w//2, y - h//2),
                (x + w//2, y + h//2),
                color, 2
            )
            
            # Draw distance label
            label = f"{obstacle.distance:.1f}m"
            cv2.putText(
                overlay, label,
                (x - 20, y - h//2 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                color, 1
            )
            
            # Draw warning circle for critical obstacles
            if obstacle.risk == RiskLevel.CRITICAL:
                radius = int(obstacle.get_safety_radius() * 50)  # Scale to pixels
                cv2.circle(overlay, (x, y), radius, color, 2)
    
    def _draw_paths(self, overlay: np.ndarray):
        """Draw all path candidates"""
        for path in self.current_paths:
            if path == self.selected_path:
                continue  # Draw selected path separately
            
            # Color based on safety
            if path.is_safe:
                color = (100, 100, 255)  # Blue (safe)
            else:
                color = (100, 100, 100)  # Gray (unsafe)
            
            # Draw path curve
            points = np.array(path.points, dtype=np.int32)
            cv2.polylines(overlay, [points], False, color, 1)
    
    def _draw_selected_path(self, overlay: np.ndarray):
        """Draw selected path with highlighting"""
        if not self.selected_path:
            return
        
        points = np.array(self.selected_path.points, dtype=np.int32)
        
        # Color based on safety
        if self.selected_path.is_safe:
            color = (0, 255, 0)  # Green (safe)
        else:
            color = (0, 165, 255)  # Orange (warning)
        
        # Draw thick highlighted path
        cv2.polylines(overlay, [points], False, color, 3)
        
        # Draw path direction arrows
        for i in range(0, len(points) - 5, 5):
            p1 = tuple(points[i])
            p2 = tuple(points[i + 5])
            cv2.arrowedLine(overlay, p1, p2, color, 2, tipLength=0.3)
        
        # Draw clearance indicator
        if len(points) > 0:
            mid_point = points[len(points) // 2]
            label = f"Clear: {self.selected_path.clearance:.1f}m"
            cv2.putText(
                overlay, label,
                (mid_point[0] + 10, mid_point[1]),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                color, 1
            )
    
    def _draw_vehicle_indicator(self, overlay: np.ndarray, shape: Tuple[int, int]):
        """Draw vehicle/drone indicator at bottom center"""
        h, w = shape
        center_x = w // 2
        bottom_y = h - 30
        
        # Draw drone icon (simplified triangle)
        pts = np.array([
            [center_x, bottom_y - 15],
            [center_x - 15, bottom_y + 10],
            [center_x + 15, bottom_y + 10]
        ], dtype=np.int32)
        
        cv2.fillPoly(overlay, [pts], (255, 255, 255))
        cv2.polylines(overlay, [pts], True, (0, 255, 0), 2)
    
    def _draw_status_hud(self, overlay: np.ndarray, shape: Tuple[int, int]):
        """Draw status HUD with obstacle info"""
        h, w = shape
        
        # Draw status panel background
        panel_height = 80
        cv2.rectangle(
            overlay,
            (10, 10),
            (250, 10 + panel_height),
            (0, 0, 0), -1
        )
        cv2.rectangle(
            overlay,
            (10, 10),
            (250, 10 + panel_height),
            (100, 100, 100), 2
        )
        
        # Status text
        y_offset = 30
        
        # Avoidance status
        if not self.feature_enabled:
            status_text = "DISABLED"
            status_color = (160, 160, 160)
        else:
            status_text = "AVOIDING" if self.avoidance_active else "CLEAR"
            status_color = (0, 165, 255) if self.avoidance_active else (0, 255, 0)
        cv2.putText(
            overlay, f"Status: {status_text}",
            (20, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
            status_color, 1
        )
        
        # Obstacle count
        y_offset += 20
        cv2.putText(
            overlay, f"Obstacles: {len(self.detected_obstacles)}",
            (20, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4,
            (255, 255, 255), 1
        )
        
        # Minimum distance
        y_offset += 20
        if self.detected_obstacles:
            min_dist = min(obs.distance for obs in self.detected_obstacles)
            dist_color = (0, 0, 255) if min_dist < self.critical_distance else (255, 255, 255)
            cv2.putText(
                overlay, f"Min Dist: {min_dist:.2f}m",
                (20, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                dist_color, 1
            )
        
        # Path clearance
        if self.selected_path:
            y_offset += 20
            cv2.putText(
                overlay, f"Clearance: {self.selected_path.clearance:.2f}m",
                (20, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                (255, 255, 255), 1
            )
    
    def reset(self):
        """Reset obstacle avoidance state"""
        self.detected_obstacles = []
        self.current_paths = []
        self.selected_path = None
        self.avoidance_active = False
        self.logger.info("Obstacle avoidance system reset")

    def _apply_disabled_style(self, overlay: np.ndarray, shape: Tuple[int, int]) -> np.ndarray:
        """Desaturate overlay and add disabled banner."""
        # Desaturate overlay to greyscale
        grey = cv2.cvtColor(overlay, cv2.COLOR_RGB2GRAY)
        desaturated = cv2.cvtColor(grey, cv2.COLOR_GRAY2RGB)
        
        # Draw disabled banner on top-left panel
        self._draw_disabled_banner(desaturated, shape)
        return desaturated

    def _draw_disabled_banner(self, overlay: np.ndarray, shape: Tuple[int, int]) -> None:
        """Overlay a disabled banner message."""
        h, w = shape
        banner_w = min(280, w - 20)
        cv2.rectangle(
            overlay,
            (10, h - 60),
            (10 + banner_w, h - 20),
            (30, 30, 30),
            -1
        )
        cv2.rectangle(
            overlay,
            (10, h - 60),
            (10 + banner_w, h - 20),
            (90, 90, 90),
            1
        )
        cv2.putText(
            overlay,
            "Obstacle avoidance disabled",
            (20, h - 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (180, 180, 180),
            1
        )
