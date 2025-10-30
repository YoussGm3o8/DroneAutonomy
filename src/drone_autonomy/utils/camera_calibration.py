"""Camera calibration utilities."""

import numpy as np
import cv2
import json
import logging
from pathlib import Path
from typing import Tuple, Optional


class CameraCalibration:
    """
    Camera calibration utilities for monocular vision systems.
    """
    
    def __init__(self):
        """Initialize camera calibration."""
        self.logger = logging.getLogger(__name__)
        self.camera_matrix = None
        self.dist_coeffs = None
        self.image_size = None
        
    def calibrate_from_chessboard(self, images_path: str, pattern_size: Tuple[int, int],
                                   square_size: float = 1.0) -> bool:
        """
        Calibrate camera from chessboard images.
        
        Args:
            images_path: Path to directory with calibration images
            pattern_size: Chessboard pattern size (cols, rows)
            square_size: Size of chessboard square in meters
            
        Returns:
            True if calibration successful
        """
        try:
            import glob
            
            # Prepare object points
            objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
            objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
            objp *= square_size
            
            # Arrays to store object points and image points
            objpoints = []  # 3d points in real world space
            imgpoints = []  # 2d points in image plane
            
            # Find images
            images = glob.glob(f"{images_path}/*.jpg") + glob.glob(f"{images_path}/*.png")
            
            if not images:
                self.logger.error(f"No images found in {images_path}")
                return False
            
            self.logger.info(f"Found {len(images)} calibration images")
            
            for fname in images:
                img = cv2.imread(fname)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Find chessboard corners
                ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)
                
                if ret:
                    objpoints.append(objp)
                    
                    # Refine corner positions
                    corners2 = cv2.cornerSubPix(
                        gray, corners, (11, 11), (-1, -1),
                        criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                    )
                    imgpoints.append(corners2)
                    
                    self.logger.info(f"Found corners in {Path(fname).name}")
            
            if len(objpoints) < 3:
                self.logger.error("Not enough valid calibration images")
                return False
            
            # Calibrate camera
            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                objpoints, imgpoints, gray.shape[::-1], None, None
            )
            
            if ret:
                self.camera_matrix = mtx
                self.dist_coeffs = dist
                self.image_size = gray.shape[::-1]
                
                self.logger.info("Camera calibration successful")
                self.logger.info(f"Camera matrix:\n{mtx}")
                self.logger.info(f"Distortion coefficients: {dist.ravel()}")
                
                return True
            else:
                self.logger.error("Camera calibration failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during calibration: {e}")
            return False
    
    def load_from_config(self, config: dict):
        """
        Load calibration from configuration dictionary.
        
        Args:
            config: Camera configuration dictionary
        """
        self.camera_matrix = np.array([
            [config.get('fx', 500.0), 0, config.get('cx', 320.0)],
            [0, config.get('fy', 500.0), config.get('cy', 240.0)],
            [0, 0, 1]
        ])
        
        self.dist_coeffs = np.array([
            config.get('k1', 0.0),
            config.get('k2', 0.0),
            config.get('p1', 0.0),
            config.get('p2', 0.0)
        ])
        
        self.logger.info("Loaded calibration from config")
    
    def save_to_file(self, filepath: str):
        """
        Save calibration to JSON file.
        
        Args:
            filepath: Path to save calibration file
        """
        if self.camera_matrix is None or self.dist_coeffs is None:
            self.logger.error("No calibration data to save")
            return
        
        calibration_data = {
            'camera_matrix': self.camera_matrix.tolist(),
            'dist_coeffs': self.dist_coeffs.tolist(),
            'image_size': self.image_size if self.image_size else [640, 480]
        }
        
        with open(filepath, 'w') as f:
            json.dump(calibration_data, f, indent=2)
        
        self.logger.info(f"Saved calibration to {filepath}")
    
    def load_from_file(self, filepath: str) -> bool:
        """
        Load calibration from JSON file.
        
        Args:
            filepath: Path to calibration file
            
        Returns:
            True if loaded successfully
        """
        try:
            with open(filepath, 'r') as f:
                calibration_data = json.load(f)
            
            self.camera_matrix = np.array(calibration_data['camera_matrix'])
            self.dist_coeffs = np.array(calibration_data['dist_coeffs'])
            self.image_size = tuple(calibration_data.get('image_size', [640, 480]))
            
            self.logger.info(f"Loaded calibration from {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading calibration: {e}")
            return False
    
    def undistort_image(self, image: np.ndarray) -> np.ndarray:
        """
        Undistort an image using calibration parameters.
        
        Args:
            image: Input image
            
        Returns:
            Undistorted image
        """
        if self.camera_matrix is None or self.dist_coeffs is None:
            return image
        
        return cv2.undistort(image, self.camera_matrix, self.dist_coeffs)
    
    def get_camera_matrix(self) -> Optional[np.ndarray]:
        """Get camera intrinsic matrix."""
        return self.camera_matrix
    
    def get_dist_coeffs(self) -> Optional[np.ndarray]:
        """Get distortion coefficients."""
        return self.dist_coeffs
