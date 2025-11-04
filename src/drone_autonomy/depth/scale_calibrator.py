"""
Depth Scale Calibration for Monocular Depth Estimation

Converts relative depth (0-1) to metric distance (meters) using:
1. Drone altitude (barometer/GPS)
2. Ground plane estimation
3. Camera geometry
4. IMU orientation (pitch/roll)
"""

import numpy as np
import cv2
import logging
from typing import Tuple, Optional, Dict
from dataclasses import dataclass
from collections import deque


@dataclass
class CameraIntrinsics:
    """Camera intrinsic parameters"""
    fx: float  # Focal length x
    fy: float  # Focal length y
    cx: float  # Principal point x
    cy: float  # Principal point y
    width: int
    height: int
    
    @classmethod
    def from_fov(cls, width: int, height: int, hfov_degrees: float = 90.0):
        """
        Create intrinsics from field of view
        
        Args:
            width: Image width in pixels
            height: Image height in pixels
            hfov_degrees: Horizontal field of view in degrees
        """
        # Calculate focal length from FOV
        hfov_rad = np.deg2rad(hfov_degrees)
        fx = width / (2.0 * np.tan(hfov_rad / 2.0))
        fy = fx  # Assume square pixels
        cx = width / 2.0
        cy = height / 2.0
        
        return cls(fx=fx, fy=fy, cx=cx, cy=cy, width=width, height=height)


class DepthScaleCalibrator:
    """
    Calibrates relative depth to metric depth using drone telemetry
    and ground plane estimation.
    """
    
    def __init__(self, config: dict, camera_intrinsics: Optional[CameraIntrinsics] = None):
        """
        Initialize depth scale calibrator
        
        Args:
            config: Configuration dictionary
            camera_intrinsics: Camera intrinsic parameters (or None to estimate from FOV)
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Camera parameters
        if camera_intrinsics is None:
            # Default camera intrinsics (estimate from typical FOV)
            img_width = config.get('image_width', 640)
            img_height = config.get('image_height', 480)
            hfov = config.get('horizontal_fov', 90.0)
            self.camera = CameraIntrinsics.from_fov(img_width, img_height, hfov)
        else:
            self.camera = camera_intrinsics
        
        # Calibration parameters
        self.use_altitude_calibration = config.get('use_altitude_calibration', True)
        self.use_ground_plane = config.get('use_ground_plane', True)
        self.ground_plane_sample_region = config.get('ground_plane_sample_region', 0.3)  # Bottom 30% of image
        
        # Scale estimation
        self.scale_factor = 1.0  # Metric scale (meters per relative depth unit)
        self.scale_history = deque(maxlen=30)  # Smooth scale estimates over time
        self.min_altitude_for_calibration = config.get('min_altitude_for_calibration', 1.0)  # meters
        
        # Ground plane estimation
        self.ground_plane = None  # (a, b, c, d) for ax + by + cz + d = 0
        
        # Fallback parameters when no telemetry available
        self.default_max_range = config.get('default_max_range', 10.0)  # meters
        self.default_min_range = config.get('default_min_range', 0.5)  # meters
        
    def calibrate_from_altitude(
        self,
        depth_map: np.ndarray,
        altitude_agl: float,
        pitch_deg: float = 0.0,
        roll_deg: float = 0.0
    ) -> bool:
        """
        Calibrate depth scale using drone altitude above ground level
        
        Args:
            depth_map: Relative depth map (0=far, 1=close)
            altitude_agl: Altitude above ground level in meters
            pitch_deg: Camera pitch angle in degrees (positive = nose up)
            roll_deg: Camera roll angle in degrees
            
        Returns:
            True if calibration successful
        """
        if altitude_agl < self.min_altitude_for_calibration:
            self.logger.debug(f"Altitude {altitude_agl:.2f}m too low for calibration")
            return False
        
        try:
            # Sample ground region (bottom portion of image)
            h, w = depth_map.shape
            ground_region_start = int(h * (1.0 - self.ground_plane_sample_region))
            ground_region = depth_map[ground_region_start:, :]
            
            # Get median depth in ground region
            # Relative depth: 1.0 = close (ground), 0.0 = far (sky)
            median_ground_depth = np.median(ground_region)
            
            if median_ground_depth < 0.1:
                # Ground not visible or depth map invalid
                self.logger.debug("Ground region has very low depth value - may be looking at sky")
                return False
            
            # Account for camera pitch
            pitch_rad = np.deg2rad(pitch_deg)
            # When pitched down, altitude_agl is actual distance to ground
            # When pitched up, ground is farther away
            
            # Calculate expected ground distance considering pitch
            # Ground center pixel in image
            ground_center_y = h - int(h * self.ground_plane_sample_region / 2)
            
            # Angle from camera to ground center pixel
            pixel_angle = np.arctan2(ground_center_y - self.camera.cy, self.camera.fy)
            actual_angle = pitch_rad + pixel_angle
            
            # Distance to ground at this angle
            if abs(np.cos(actual_angle)) > 0.1:  # Avoid division by near-zero
                ground_distance = altitude_agl / np.cos(actual_angle)
            else:
                ground_distance = altitude_agl
            
            # Calculate scale factor
            # median_ground_depth (relative) should map to ground_distance (meters)
            # If depth model outputs: 0=far, 1=close
            # Then for ground at distance D: depth_value = scale / (D + offset)
            
            # Simple inverse model: depth = max_range - (depth_value * (max_range - min_range))
            # Solving for max_range when we know ground_distance and depth_value:
            # ground_distance = max_range - (median_ground_depth * (max_range - min_range))
            
            # Estimate max range (far distance) from ground observation
            estimated_max_range = (ground_distance + median_ground_depth * self.default_min_range) / median_ground_depth
            
            # Clamp to reasonable values
            estimated_max_range = np.clip(estimated_max_range, altitude_agl, altitude_agl * 10)
            
            # Update scale factor (max range becomes our calibration)
            self.scale_history.append(estimated_max_range)
            self.scale_factor = np.median(list(self.scale_history))
            
            self.logger.debug(
                f"Calibrated scale: altitude={altitude_agl:.2f}m, "
                f"pitch={pitch_deg:.1f}°, ground_depth={median_ground_depth:.3f}, "
                f"scale_factor={self.scale_factor:.2f}m"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in altitude calibration: {e}")
            return False
    
    def estimate_ground_plane(
        self,
        depth_map: np.ndarray,
        pitch_deg: float = 0.0,
        roll_deg: float = 0.0
    ) -> Optional[np.ndarray]:
        """
        Estimate ground plane from depth map
        
        Args:
            depth_map: Relative depth map
            pitch_deg: Camera pitch angle
            roll_deg: Camera roll angle
            
        Returns:
            Ground plane parameters (a, b, c, d) or None
        """
        try:
            h, w = depth_map.shape
            
            # Sample ground region
            ground_region_start = int(h * (1.0 - self.ground_plane_sample_region))
            ground_region = depth_map[ground_region_start:, :]
            
            # Convert to 3D points (assuming metric depth available)
            points_3d = []
            
            for y in range(ground_region_start, h, 5):  # Sample every 5 pixels
                for x in range(0, w, 5):
                    depth_rel = depth_map[y, x]
                    
                    if depth_rel < 0.1:  # Skip sky/invalid
                        continue
                    
                    # Convert relative depth to metric (using current scale)
                    depth_metric = self.relative_to_metric(depth_rel)
                    
                    # Project to 3D using camera intrinsics
                    X = (x - self.camera.cx) * depth_metric / self.camera.fx
                    Y = (y - self.camera.cy) * depth_metric / self.camera.fy
                    Z = depth_metric
                    
                    points_3d.append([X, Y, Z])
            
            if len(points_3d) < 10:
                return None
            
            points_3d = np.array(points_3d)
            
            # Fit plane using RANSAC
            # Plane equation: ax + by + cz + d = 0
            # We want normal vector pointing up: (a, b, c) with c > 0
            
            # Simple least squares plane fit
            centroid = np.mean(points_3d, axis=0)
            centered = points_3d - centroid
            
            # SVD to find normal
            _, _, Vt = np.linalg.svd(centered)
            normal = Vt[-1]  # Last row = normal to plane
            
            # Ensure normal points up (negative Z in camera coords)
            if normal[2] > 0:
                normal = -normal
            
            # Plane parameters
            a, b, c = normal
            d = -np.dot(normal, centroid)
            
            self.ground_plane = np.array([a, b, c, d])
            
            return self.ground_plane
            
        except Exception as e:
            self.logger.error(f"Error estimating ground plane: {e}")
            return None
    
    def relative_to_metric(self, depth_relative: np.ndarray) -> np.ndarray:
        """
        Convert relative depth to metric depth
        
        Args:
            depth_relative: Relative depth (0=far, 1=close)
            
        Returns:
            Metric depth in meters
        """
        # Inverse depth model with calibrated scale
        max_range = self.scale_factor if self.scale_factor > 0 else self.default_max_range
        min_range = self.default_min_range
        
        # Convert: depth_rel=1.0 -> min_range, depth_rel=0.0 -> max_range
        depth_metric = max_range - (depth_relative * (max_range - min_range))
        
        return depth_metric
    
    def metric_to_relative(self, depth_metric: np.ndarray) -> np.ndarray:
        """
        Convert metric depth to relative depth (inverse operation)
        
        Args:
            depth_metric: Metric depth in meters
            
        Returns:
            Relative depth (0=far, 1=close)
        """
        max_range = self.scale_factor if self.scale_factor > 0 else self.default_max_range
        min_range = self.default_min_range
        
        # Inverse: depth_metric -> depth_rel
        depth_relative = (max_range - depth_metric) / (max_range - min_range)
        
        return np.clip(depth_relative, 0.0, 1.0)
    
    def calibrate_from_telemetry(
        self,
        depth_map: np.ndarray,
        telemetry: Dict[str, float]
    ) -> bool:
        """
        Calibrate using telemetry data
        
        Args:
            depth_map: Relative depth map
            telemetry: Dictionary with altitude_rel, pitch, roll, etc.
            
        Returns:
            True if calibration successful
        """
        altitude_agl = telemetry.get('altitude_rel', None)
        
        if altitude_agl is None or altitude_agl < self.min_altitude_for_calibration:
            return False
        
        pitch_deg = telemetry.get('pitch', 0.0)
        roll_deg = telemetry.get('roll', 0.0)
        
        return self.calibrate_from_altitude(depth_map, altitude_agl, pitch_deg, roll_deg)
    
    def get_calibration_status(self) -> Dict[str, any]:
        """Get current calibration status"""
        return {
            'scale_factor': self.scale_factor,
            'max_range': self.scale_factor,
            'min_range': self.default_min_range,
            'calibrated': len(self.scale_history) > 5,
            'num_samples': len(self.scale_history),
            'ground_plane': self.ground_plane is not None
        }
