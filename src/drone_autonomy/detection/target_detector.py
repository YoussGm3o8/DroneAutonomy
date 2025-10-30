"""Red circular target detection using HSV thresholding and Hough Circle Transform."""

import cv2
import numpy as np
import logging
from typing import List, Tuple


class TargetDetector:
    """
    Red circular target detector using HSV color thresholding and Hough Circle Transform.
    
    Provides robust detection of red circular markers for navigation and targeting.
    """
    
    def __init__(self, config: dict):
        """
        Initialize target detector.
        
        Args:
            config: Target detection configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # HSV thresholds for red color
        # Red wraps around in HSV, so we need two ranges
        self.hsv_lower1 = np.array(config.get('hsv_lower', [0, 100, 100]))
        self.hsv_upper1 = np.array(config.get('hsv_upper', [10, 255, 255]))
        self.hsv_lower2 = np.array([170, 100, 100])
        self.hsv_upper2 = np.array([180, 255, 255])
        
        self.min_radius = config.get('min_radius', 10)
        self.max_radius = config.get('max_radius', 200)
        self.circle_threshold = config.get('circle_threshold', 0.7)
        
        # Downscale for faster processing
        self.downscale_factor = config.get('downscale_factor', 2)  # Process at half resolution
        
    def detect(self, frame: np.ndarray) -> Tuple[List[dict], float]:
        """
        Detect red circular targets in a frame.
        
        Args:
            frame: Input BGR image
            
        Returns:
            Tuple of (targets, processing_time)
            Each target is a dict with keys: center (x, y), radius, confidence
        """
        try:
            import time
            start_time = time.time()
            
            # Downscale for faster processing
            h, w = frame.shape[:2]
            small_frame = cv2.resize(frame, (w // self.downscale_factor, h // self.downscale_factor))
            
            # Convert to HSV
            hsv = cv2.cvtColor(small_frame, cv2.COLOR_BGR2HSV)
            
            # Create mask for red color (two ranges)
            mask1 = cv2.inRange(hsv, self.hsv_lower1, self.hsv_upper1)
            mask2 = cv2.inRange(hsv, self.hsv_lower2, self.hsv_upper2)
            mask = cv2.bitwise_or(mask1, mask2)
            
            # Apply morphological operations to reduce noise (smaller kernel for downscaled image)
            kernel_size = max(3, 5 // self.downscale_factor)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            # Detect circles using Hough Circle Transform (scaled parameters)
            blur_size = max(5, 9 // self.downscale_factor)
            if blur_size % 2 == 0:
                blur_size += 1
            blurred = cv2.GaussianBlur(mask, (blur_size, blur_size), 2)
            
            min_radius_scaled = max(5, self.min_radius // self.downscale_factor)
            max_radius_scaled = self.max_radius // self.downscale_factor
            
            circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=min_radius_scaled * 2,
                param1=50,
                param2=30,
                minRadius=min_radius_scaled,
                maxRadius=max_radius_scaled
            )
            
            targets = []
            
            if circles is not None:
                circles = np.round(circles[0, :]).astype("int")
                
                for (x, y, r) in circles:
                    # Validate circle by checking mask coverage
                    circle_mask = np.zeros(mask.shape, dtype=np.uint8)
                    cv2.circle(circle_mask, (x, y), r, 255, -1)
                    
                    # Calculate coverage ratio
                    intersection = cv2.bitwise_and(mask, circle_mask)
                    coverage = np.count_nonzero(intersection) / np.count_nonzero(circle_mask)
                    
                    if coverage >= self.circle_threshold:
                        # Scale coordinates back to original resolution
                        x_orig = x * self.downscale_factor
                        y_orig = y * self.downscale_factor
                        r_orig = r * self.downscale_factor
                        
                        targets.append({
                            'center': (x_orig, y_orig),
                            'radius': r_orig,
                            'confidence': coverage,
                            'bbox': (x_orig - r_orig, y_orig - r_orig, x_orig + r_orig, y_orig + r_orig)
                        })
            
            processing_time = time.time() - start_time
            
            return targets, processing_time
            
        except Exception as e:
            self.logger.error(f"Error detecting targets: {e}")
            return [], 0.0
    
    def draw_targets(self, frame: np.ndarray, targets: List[dict]) -> np.ndarray:
        """
        Draw detected targets on frame.
        
        Args:
            frame: Input BGR image
            targets: List of detected targets
            
        Returns:
            Frame with drawn targets
        """
        output = frame.copy()
        
        for target in targets:
            center = target['center']
            radius = target['radius']
            confidence = target['confidence']
            
            # Draw circle
            cv2.circle(output, center, radius, (0, 0, 255), 2)
            cv2.circle(output, center, 2, (0, 0, 255), 3)
            
            # Draw crosshair
            cv2.line(output, (center[0] - 10, center[1]), (center[0] + 10, center[1]), (0, 0, 255), 2)
            cv2.line(output, (center[0], center[1] - 10), (center[0], center[1] + 10), (0, 0, 255), 2)
            
            # Draw label
            label = f"Target: {confidence:.2f}"
            cv2.putText(output, label, (center[0] - radius, center[1] - radius - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return output
    
    def get_mask(self, frame: np.ndarray) -> np.ndarray:
        """
        Get the red color mask for debugging.
        
        Args:
            frame: Input BGR image
            
        Returns:
            Binary mask of red regions
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, self.hsv_lower1, self.hsv_upper1)
        mask2 = cv2.inRange(hsv, self.hsv_lower2, self.hsv_upper2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        return mask
