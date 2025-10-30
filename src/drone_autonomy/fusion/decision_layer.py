"""Fusion and decision layer for combining depth and detection outputs."""

import cv2
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional


class DecisionLayer:
    """
    Fusion and decision layer for combining depth and detection outputs.
    
    Fuses depth maps with object detections to compute keep-out regions
    and target gates for avoidance and navigation.
    """
    
    def __init__(self, config: dict):
        """
        Initialize decision layer.
        
        Args:
            config: Fusion configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.depth_weight = config.get('depth_weight', 0.6)
        self.detection_weight = config.get('detection_weight', 0.4)
        self.min_confidence = config.get('min_confidence', 0.6)
        self.proximity_threshold = config.get('proximity_threshold', 2.0)  # meters
        
    def fuse_detections_with_depth(self, detections: List[dict], depth_map: np.ndarray,
                                   depth_scale: float = 1.0) -> List[dict]:
        """
        Fuse object detections with depth information.
        
        Args:
            detections: List of detections from YOLO
            depth_map: Normalized depth map (0-1 range, where 0 is close)
            depth_scale: Scale factor to convert normalized depth to meters
            
        Returns:
            List of fused detections with depth information
        """
        fused_detections = []
        
        for det in detections:
            # Get detection center and bbox
            center = det.get('center', (0, 0))
            bbox = det.get('bbox', (0, 0, 0, 0))
            
            # Sample depth at detection center and bbox
            depth_at_center = self._sample_depth(depth_map, center[0], center[1])
            depth_at_bbox = self._sample_depth_bbox(depth_map, bbox)
            
            # Average depth (inverted because 0 is close in normalized depth)
            avg_depth = (depth_at_center + depth_at_bbox) / 2.0
            
            # Convert to distance estimate (simplified)
            # In real implementation, this would use camera calibration
            distance_estimate = (1.0 - avg_depth) * depth_scale
            
            # Compute fused confidence
            fused_confidence = (
                self.detection_weight * det['confidence'] +
                self.depth_weight * (1.0 - avg_depth)  # Closer objects have higher weight
            )
            
            # Create fused detection
            fused_det = det.copy()
            fused_det['depth'] = avg_depth
            fused_det['distance'] = distance_estimate
            fused_det['fused_confidence'] = fused_confidence
            fused_det['is_close'] = distance_estimate < self.proximity_threshold
            
            fused_detections.append(fused_det)
        
        # Sort by fused confidence (descending)
        fused_detections.sort(key=lambda x: x['fused_confidence'], reverse=True)
        
        return fused_detections
    
    def fuse_targets_with_depth(self, targets: List[dict], depth_map: np.ndarray,
                               depth_scale: float = 1.0) -> List[dict]:
        """
        Fuse target detections with depth information.
        
        Args:
            targets: List of circular target detections
            depth_map: Normalized depth map
            depth_scale: Scale factor to convert normalized depth to meters
            
        Returns:
            List of fused targets with depth information
        """
        fused_targets = []
        
        for target in targets:
            center = target.get('center', (0, 0))
            radius = target.get('radius', 10)
            
            # Sample depth at target center
            depth_at_center = self._sample_depth(depth_map, center[0], center[1])
            
            # Sample depth in target circle
            circle_bbox = (
                center[0] - radius,
                center[1] - radius,
                center[0] + radius,
                center[1] + radius
            )
            depth_at_circle = self._sample_depth_bbox(depth_map, circle_bbox)
            
            avg_depth = (depth_at_center + depth_at_circle) / 2.0
            distance_estimate = (1.0 - avg_depth) * depth_scale
            
            # Create fused target
            fused_target = target.copy()
            fused_target['depth'] = avg_depth
            fused_target['distance'] = distance_estimate
            fused_target['fused_confidence'] = (
                self.detection_weight * target['confidence'] +
                self.depth_weight * (1.0 - avg_depth)
            )
            
            fused_targets.append(fused_target)
        
        # Sort by fused confidence (descending)
        fused_targets.sort(key=lambda x: x['fused_confidence'], reverse=True)
        
        return fused_targets
    
    def compute_avoidance_command(self, fused_detections: List[dict],
                                 frame_width: int, frame_height: int) -> Dict[str, float]:
        """
        Compute avoidance command based on fused detections.
        
        Args:
            fused_detections: List of fused detections
            frame_width: Frame width
            frame_height: Frame height
            
        Returns:
            Avoidance command dictionary
        """
        # Initialize command
        command = {
            'avoid_left': 0.0,
            'avoid_right': 0.0,
            'avoid_up': 0.0,
            'avoid_down': 0.0,
            'priority': 0.0
        }
        
        # Filter close detections with high confidence
        close_detections = [
            det for det in fused_detections
            if det.get('is_close', False) and det['fused_confidence'] > self.min_confidence
        ]
        
        if not close_detections:
            return command
        
        # Process each close detection
        center_x = frame_width / 2
        center_y = frame_height / 2
        
        for det in close_detections:
            det_center = det.get('center', (center_x, center_y))
            distance = det.get('distance', 10.0)
            
            # Compute avoidance weight (closer = higher weight)
            weight = 1.0 / (distance + 0.1)
            
            # Compute direction to avoid
            dx = det_center[0] - center_x
            dy = det_center[1] - center_y
            
            # Avoid in opposite direction
            if dx > 0:
                command['avoid_left'] += weight
            else:
                command['avoid_right'] += weight
            
            if dy > 0:
                command['avoid_up'] += weight
            else:
                command['avoid_down'] += weight
        
        # Normalize and set priority
        total_weight = sum([command['avoid_left'], command['avoid_right'],
                          command['avoid_up'], command['avoid_down']])
        
        if total_weight > 0:
            command['avoid_left'] /= total_weight
            command['avoid_right'] /= total_weight
            command['avoid_up'] /= total_weight
            command['avoid_down'] /= total_weight
            command['priority'] = min(1.0, len(close_detections) * 0.3)
        
        return command
    
    def compute_avoidance_from_depth(self, depth_map: np.ndarray,
                                     frame_width: int, frame_height: int) -> Dict[str, any]:
        """
        Compute avoidance command directly from depth map (no YOLO detections).
        Analyzes depth map to detect close obstacles in different regions.
        
        Args:
            depth_map: Depth map (0.0=near, 1.0=far)
            frame_width: Original frame width
            frame_height: Original frame height
            
        Returns:
            Avoidance command dictionary with direction and min_distance
        """
        if depth_map is None or depth_map.size == 0:
            return {'direction': 'none', 'min_distance': 10.0}
        
        # Resize depth map to match frame dimensions if needed
        if depth_map.shape[1] != frame_width or depth_map.shape[0] != frame_height:
            depth_map = cv2.resize(depth_map, (frame_width, frame_height))
        
        h, w = depth_map.shape
        
        # Divide frame into regions (left, center, right, top, bottom)
        region_threshold = 0.3  # Depth < 0.3 = close obstacle (~3m or less with scale=10)
        
        # Define regions
        left_region = depth_map[:, :w//3]
        center_region = depth_map[:, w//3:2*w//3]
        right_region = depth_map[:, 2*w//3:]
        top_region = depth_map[:h//3, :]
        bottom_region = depth_map[2*h//3:, :]
        
        # Calculate minimum depth in each region
        left_min = np.min(left_region)
        center_min = np.min(center_region)
        right_min = np.min(right_region)
        top_min = np.min(top_region)
        bottom_min = np.min(bottom_region)
        
        overall_min = min(left_min, center_min, right_min, top_min, bottom_min)
        min_distance = overall_min * 10.0  # Convert to approximate meters
        
        # Determine avoidance direction
        if overall_min > region_threshold:
            return {'direction': 'none', 'min_distance': min_distance}
        
        # Priority: avoid based on closest obstacle
        if center_min < region_threshold:
            # Obstacle ahead - check which side is clearer
            if left_min > right_min:
                direction = 'left'
            else:
                direction = 'right'
        elif left_min < region_threshold:
            direction = 'right'
        elif right_min < region_threshold:
            direction = 'left'
        elif top_min < region_threshold:
            direction = 'down'
        elif bottom_min < region_threshold:
            direction = 'up'
        else:
            direction = 'none'
        
        return {
            'direction': direction,
            'min_distance': min_distance,
            'region_depths': {
                'left': left_min * 10.0,
                'center': center_min * 10.0,
                'right': right_min * 10.0,
                'top': top_min * 10.0,
                'bottom': bottom_min * 10.0
            }
        }
    
    def compute_target_approach(self, fused_targets: List[dict],
                               frame_width: int, frame_height: int) -> Dict[str, float]:
        """
        Compute approach command for target.
        
        Args:
            fused_targets: List of fused targets
            frame_width: Frame width
            frame_height: Frame height
            
        Returns:
            Approach command dictionary
        """
        command = {
            'approach': False,
            'action': 'none',
            'offset_x': 0.0,
            'offset_y': 0.0,
            'distance': 0.0,
            'confidence': 0.0
        }
        
        # Get best target
        if not fused_targets:
            return command
        
        best_target = fused_targets[0]
        
        if best_target['fused_confidence'] < self.min_confidence:
            return command
        
        # Compute offset from center
        center_x = frame_width / 2
        center_y = frame_height / 2
        target_center = best_target.get('center', (center_x, center_y))
        
        command['approach'] = True
        command['action'] = 'approach'
        command['offset_x'] = (target_center[0] - center_x) / frame_width
        command['offset_y'] = (target_center[1] - center_y) / frame_height
        command['distance'] = best_target.get('distance', 0.0)
        command['confidence'] = best_target['fused_confidence']
        
        return command
    
    def _sample_depth(self, depth_map: np.ndarray, x: int, y: int, radius: int = 5) -> float:
        """
        Sample depth at a point with averaging.
        
        Args:
            depth_map: Depth map
            x: X coordinate
            y: Y coordinate
            radius: Sampling radius
            
        Returns:
            Average depth value
        """
        if depth_map is None or depth_map.size == 0:
            return 0.5
        
        h, w = depth_map.shape
        x = max(radius, min(x, w - radius))
        y = max(radius, min(y, h - radius))
        
        region = depth_map[y-radius:y+radius+1, x-radius:x+radius+1]
        return np.mean(region)
    
    def _sample_depth_bbox(self, depth_map: np.ndarray, bbox: Tuple[int, int, int, int]) -> float:
        """
        Sample average depth in bounding box.
        
        Args:
            depth_map: Depth map
            bbox: Bounding box (x1, y1, x2, y2)
            
        Returns:
            Average depth value
        """
        if depth_map is None or depth_map.size == 0:
            return 0.5
        
        x1, y1, x2, y2 = bbox
        h, w = depth_map.shape
        
        x1 = max(0, min(x1, w))
        x2 = max(0, min(x2, w))
        y1 = max(0, min(y1, h))
        y2 = max(0, min(y2, h))
        
        if x2 <= x1 or y2 <= y1:
            return 0.5
        
        region = depth_map[y1:y2, x1:x2]
        return np.mean(region)
