"""Visual Inertial Odometry module for state estimation."""

import numpy as np
import cv2
import logging
from typing import Tuple, Optional


class VIOEstimator:
    """
    Visual Inertial Odometry estimator.
    
    Provides 6-DoF pose estimation using monocular camera and IMU data.
    This is a placeholder for integration with VINS-Mono or ORB-SLAM3.
    """
    
    def __init__(self, config: dict, camera_matrix: np.ndarray, dist_coeffs: np.ndarray):
        """
        Initialize VIO estimator.
        
        Args:
            config: VIO configuration dictionary
            camera_matrix: Camera intrinsic matrix (3x3)
            dist_coeffs: Camera distortion coefficients
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        
        self.vio_type = config.get('type', 'vins-mono')
        self.enabled = config.get('enabled', True)
        
        # State
        self.is_initialized = False
        self.pose = np.eye(4)  # 4x4 transformation matrix
        self.velocity = np.zeros(3)
        self.covariance = np.eye(6)
        
        # Feature tracking
        self.prev_frame = None
        self.prev_keypoints = None
        self.prev_descriptors = None
        
        # Initialize feature detector and matcher
        self.feature_detector = cv2.ORB_create(nfeatures=1000)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        
        self.logger.info(f"VIO Estimator initialized: {self.vio_type}")
    
    def process_frame(self, frame: np.ndarray, imu_data: Optional[dict] = None) -> Tuple[bool, np.ndarray, np.ndarray]:
        """
        Process a frame for visual odometry.
        
        Args:
            frame: Input grayscale or BGR image
            imu_data: IMU measurements (optional)
            
        Returns:
            Tuple of (success, position, orientation_quaternion)
        """
        if not self.enabled:
            return False, np.zeros(3), np.array([1, 0, 0, 0])
        
        try:
            # Convert to grayscale if needed
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            
            # Detect features
            keypoints, descriptors = self.feature_detector.detectAndCompute(gray, None)
            
            if self.prev_frame is None:
                # First frame - initialization
                self.prev_frame = gray
                self.prev_keypoints = keypoints
                self.prev_descriptors = descriptors
                self.is_initialized = True
                return True, self._get_position(), self._get_orientation_quat()
            
            # Match features
            if descriptors is not None and self.prev_descriptors is not None:
                matches = self.matcher.match(self.prev_descriptors, descriptors)
                
                if len(matches) > 10:
                    # Extract matched keypoints
                    pts1 = np.float32([self.prev_keypoints[m.queryIdx].pt for m in matches])
                    pts2 = np.float32([keypoints[m.trainIdx].pt for m in matches])
                    
                    # Estimate essential matrix
                    E, mask = cv2.findEssentialMat(
                        pts1, pts2, self.camera_matrix,
                        method=cv2.RANSAC, prob=0.999, threshold=1.0
                    )
                    
                    if E is not None:
                        # Recover pose
                        _, R, t, mask = cv2.recoverPose(E, pts1, pts2, self.camera_matrix, mask=mask)
                        
                        # Update pose (simplified - should integrate with previous pose)
                        self._update_pose(R, t)
            
            # Update for next iteration
            self.prev_frame = gray
            self.prev_keypoints = keypoints
            self.prev_descriptors = descriptors
            
            return True, self._get_position(), self._get_orientation_quat()
            
        except Exception as e:
            self.logger.error(f"Error processing VIO frame: {e}")
            return False, np.zeros(3), np.array([1, 0, 0, 0])
    
    def _update_pose(self, R: np.ndarray, t: np.ndarray):
        """
        Update pose from rotation and translation.
        
        Args:
            R: Rotation matrix (3x3)
            t: Translation vector (3x1)
        """
        # Create transformation matrix
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = t.flatten()
        
        # Update cumulative pose
        self.pose = self.pose @ T
    
    def _get_position(self) -> np.ndarray:
        """
        Get current position estimate.
        
        Returns:
            Position vector [x, y, z]
        """
        return self.pose[:3, 3]
    
    def _get_orientation_quat(self) -> np.ndarray:
        """
        Get current orientation as quaternion.
        
        Returns:
            Quaternion [w, x, y, z]
        """
        R = self.pose[:3, :3]
        return self._rotation_matrix_to_quaternion(R)
    
    @staticmethod
    def _rotation_matrix_to_quaternion(R: np.ndarray) -> np.ndarray:
        """
        Convert rotation matrix to quaternion.
        
        Args:
            R: Rotation matrix (3x3)
            
        Returns:
            Quaternion [w, x, y, z]
        """
        trace = np.trace(R)
        
        if trace > 0:
            s = 0.5 / np.sqrt(trace + 1.0)
            w = 0.25 / s
            x = (R[2, 1] - R[1, 2]) * s
            y = (R[0, 2] - R[2, 0]) * s
            z = (R[1, 0] - R[0, 1]) * s
        elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
            s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
            w = (R[2, 1] - R[1, 2]) / s
            x = 0.25 * s
            y = (R[0, 1] + R[1, 0]) / s
            z = (R[0, 2] + R[2, 0]) / s
        elif R[1, 1] > R[2, 2]:
            s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
            w = (R[0, 2] - R[2, 0]) / s
            x = (R[0, 1] + R[1, 0]) / s
            y = 0.25 * s
            z = (R[1, 2] + R[2, 1]) / s
        else:
            s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
            w = (R[1, 0] - R[0, 1]) / s
            x = (R[0, 2] + R[2, 0]) / s
            y = (R[1, 2] + R[2, 1]) / s
            z = 0.25 * s
        
        return np.array([w, x, y, z])
    
    def reset(self):
        """Reset VIO estimator state."""
        self.is_initialized = False
        self.pose = np.eye(4)
        self.velocity = np.zeros(3)
        self.covariance = np.eye(6)
        self.prev_frame = None
        self.prev_keypoints = None
        self.prev_descriptors = None
        self.logger.info("VIO state reset")
    
    def get_covariance(self) -> np.ndarray:
        """
        Get pose covariance matrix.
        
        Returns:
            6x6 covariance matrix
        """
        return self.covariance
