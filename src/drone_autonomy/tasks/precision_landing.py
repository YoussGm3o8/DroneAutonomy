"""
Precision Landing Task - Competition Task 4

Land precisely on designated landing pad:
- Detect landing pad (typically marked)
- Center drone over pad
- Descend safely
- Land within tolerance
"""

import cv2
import numpy as np
from typing import Dict, Any, Optional, List

from .base_task import BaseTask, TaskStatus


class PrecisionLandingTask(BaseTask):
    """
    Precision Landing Task
    
    Objective:
    - Detect landing pad
    - Center drone over pad
    - Land within designated area
    - Complete landing safely
    
    Scoring:
    - Base 40 points for landing on pad
    - Accuracy bonus for centering (<1m: +20, <0.5m: +30)
    - Smoothness bonus for controlled descent
    - Time bonus for efficient landing
    """
    
    def __init__(
        self,
        task_id: str,
        config: Dict[str, Any],
        telemetry,
        logger=None
    ):
        """
        Initialize precision landing task
        
        Args:
            task_id: Unique task identifier
            config: Task configuration
            telemetry: MAVLink telemetry interface
            logger: Logger instance
        """
        super().__init__(
            task_id=task_id,
            task_name="Precision Landing",
            config=config,
            telemetry=telemetry,
            logger=logger
        )
        
        # Configuration
        self.landing_altitude = config.get('landing_altitude', 5.0)  # Start altitude
        self.descent_rate = config.get('descent_rate', 0.5)  # m/s
        self.centering_tolerance = config.get('centering_tolerance', 50)  # pixels
        self.landing_tolerance = config.get('landing_tolerance', 1.0)  # meters
        
        # State
        self.pad_detected = False
        self.pad_centered = False
        self.descent_started = False
        self.landing_complete = False
        self.centering_errors = []
        
        self.logger.info(f"Precision landing task initialized")
        self.logger.info(f"  Landing altitude: {self.landing_altitude}m")
        self.logger.info(f"  Descent rate: {self.descent_rate}m/s")
    
    def _on_start(self) -> bool:
        """Initialize precision landing"""
        self.pad_detected = False
        self.pad_centered = False
        self.descent_started = False
        self.landing_complete = False
        self.centering_errors = []
        
        self.logger.info("Starting precision landing")
        return True
    
    def _on_update(
        self,
        frame,
        depth_map,
        detections: List[Dict],
        target_detection: Optional[Dict]
    ) -> bool:
        """
        Update precision landing
        
        Args:
            frame: Current camera frame
            depth_map: Depth map (not used)
            detections: Object detections (not used)
            target_detection: Landing pad detection (red circle)
            
        Returns:
            True to continue, False when landing complete
        """
        # Check current altitude
        if self.telemetry:
            current_altitude = getattr(self.telemetry, 'altitude', 0.0)
        else:
            current_altitude = 0.0
        
        # Phase 1: Detect landing pad
        if not self.pad_detected and target_detection:
            self.pad_detected = True
            self.logger.info("Landing pad detected!")
        
        # Phase 2: Center over pad
        if self.pad_detected and target_detection:
            center_x = target_detection.get('center_x', 0)
            center_y = target_detection.get('center_y', 0)
            
            frame_center_x = frame.shape[1] // 2
            frame_center_y = frame.shape[0] // 2
            error_x = center_x - frame_center_x
            error_y = center_y - frame_center_y
            total_error = np.sqrt(error_x**2 + error_y**2)
            
            self.centering_errors.append(total_error)
            
            if total_error <= self.centering_tolerance:
                if not self.pad_centered:
                    self.pad_centered = True
                    self.descent_started = True
                    self.logger.info("Pad centered - starting descent")
        
        # Phase 3: Descend
        if self.descent_started:
            if current_altitude < 0.5:  # Near ground
                self.landing_complete = True
                self.logger.info("Landing complete!")
                self.status = TaskStatus.COMPLETED
                return False
        
        return True
    
    def _calculate_score(self) -> float:
        """Calculate precision landing score"""
        if not self.landing_complete:
            return 0.0
        
        # Base score for landing
        base_score = 40.0
        
        # Centering accuracy bonus
        if self.centering_errors:
            avg_error = np.mean(self.centering_errors)
            if avg_error < 30:  # Very precise
                centering_bonus = 30.0
            elif avg_error < 50:  # Precise
                centering_bonus = 20.0
            else:  # Acceptable
                centering_bonus = 10.0
        else:
            centering_bonus = 0.0
        
        # Time bonus
        time_bonus = max(0, (1.0 - self.elapsed_time / self.timeout) * 20.0)
        
        # Smoothness bonus (based on centering error variance)
        if self.centering_errors and len(self.centering_errors) > 10:
            error_variance = np.var(self.centering_errors)
            smoothness_bonus = max(0, 10.0 * (1.0 - error_variance / 1000.0))
        else:
            smoothness_bonus = 0.0
        
        total_score = base_score + centering_bonus + time_bonus + smoothness_bonus
        
        return min(total_score, 100.0)
    
    def _on_stop(self):
        """Cleanup precision landing"""
        self.logger.info(f"Precision landing complete")
        self.logger.info(f"Pad detected: {self.pad_detected}")
        self.logger.info(f"Landing complete: {self.landing_complete}")
