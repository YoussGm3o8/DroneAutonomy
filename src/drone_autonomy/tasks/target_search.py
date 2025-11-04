"""
Target Search Task - Competition Task 1

Robust implementation of target search and identification:
- Systematic area coverage
- Red circular target detection
- GPS coordinate logging
- Photo documentation
- Score calculation based on accuracy and time
"""

import cv2
import numpy as np
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import csv

from .base_task import BaseTask, TaskStatus


class TargetSearchTask(BaseTask):
    """
    Target Search and Identification Task
    
    Objective:
    - Search designated area for red circular targets
    - Center camera on each detected target
    - Log GPS coordinates and take photo
    - Complete within time limit
    
    Scoring:
    - 20 points per target found
    - +10 bonus for centering accuracy (<30 pixel error)
    - +5 bonus for quick identification (<5 seconds)
    - -5 penalty for false positives
    - Time bonus: (1 - time_used/time_limit) * 10
    """
    
    def __init__(
        self,
        task_id: str,
        config: Dict[str, Any],
        telemetry,
        logger=None
    ):
        """
        Initialize target search task
        
        Args:
            task_id: Unique task identifier
            config: Task configuration
            telemetry: MAVLink telemetry interface
            logger: Logger instance
        """
        super().__init__(
            task_id=task_id,
            task_name="Target Search and Identification",
            config=config,
            telemetry=telemetry,
            logger=logger
        )
        
        # Task-specific config
        self.target_count_required = config.get('target_count_required', 3)
        self.search_altitude = config.get('search_altitude', 5.0)  # meters
        self.centering_accuracy = config.get('centering_accuracy', 30)  # pixels
        self.identification_time_bonus = config.get('identification_time_bonus', 5.0)  # seconds
        self.false_positive_penalty = config.get('false_positive_penalty', 5.0)
        
        # State
        self.targets_found = []
        self.current_target = None
        self.target_lock_start_time = None
        self.search_start_time = None
        
        # CSV logging
        self.csv_file = self.log_dir / f"targets_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self._init_csv()
        
        self.logger.info(f"Target search task initialized")
        self.logger.info(f"  Required targets: {self.target_count_required}")
        self.logger.info(f"  Search altitude: {self.search_altitude}m")
        self.logger.info(f"  Centering accuracy: {self.centering_accuracy} pixels")
    
    def _init_csv(self):
        """Initialize CSV file for target logging"""
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp',
                'target_id',
                'latitude',
                'longitude',
                'altitude',
                'heading',
                'centering_error_x',
                'centering_error_y',
                'detection_time',
                'photo_path',
                'score'
            ])
    
    def _on_start(self) -> bool:
        """Initialize target search"""
        try:
            self.search_start_time = time.time()
            self.targets_found = []
            
            self.logger.info("Starting target search...")
            self.logger.info(f"Searching for {self.target_count_required} targets")
            
            # Create photo directory
            self.photo_dir = self.log_dir / f"photos_{self.task_id}"
            self.photo_dir.mkdir(parents=True, exist_ok=True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting target search: {e}", exc_info=True)
            return False
    
    def _on_update(
        self,
        frame,
        depth_map,
        detections: List[Dict],
        target_detection: Optional[Dict]
    ) -> bool:
        """
        Update target search with new sensor data
        
        Args:
            frame: Current camera frame
            depth_map: Depth estimation map
            detections: Object detections (not used in this task)
            target_detection: Red circular target detection
            
        Returns:
            True to continue, False when all targets found
        """
        try:
            # Check if we've found all required targets
            if len(self.targets_found) >= self.target_count_required:
                self.logger.info(f"All {self.target_count_required} targets found!")
                self.status = TaskStatus.COMPLETED
                return False
            
            # Check for target detection
            if target_detection:
                self._process_target_detection(frame, target_detection)
            else:
                # No target visible - continue search pattern
                if self.current_target:
                    self.logger.info("Target lost - resuming search")
                    self.current_target = None
                    self.target_lock_start_time = None
            
            # Update metrics
            self.metrics['frames_processed'] += 1
            
            # Check if we should continue
            return len(self.targets_found) < self.target_count_required
            
        except Exception as e:
            self.logger.error(f"Error in target search update: {e}", exc_info=True)
            self.metrics['errors_encountered'] += 1
            return True  # Continue despite error
    
    def _process_target_detection(self, frame, target_detection: Dict):
        """
        Process detected target
        
        Args:
            frame: Current camera frame
            target_detection: Target detection dictionary
        """
        try:
            # Extract target info
            center_x = target_detection.get('center_x', 0)
            center_y = target_detection.get('center_y', 0)
            radius = target_detection.get('radius', 0)
            confidence = target_detection.get('confidence', 0.0)
            
            # Calculate centering error
            frame_center_x = frame.shape[1] // 2
            frame_center_y = frame.shape[0] // 2
            error_x = center_x - frame_center_x
            error_y = center_y - frame_center_y
            total_error = np.sqrt(error_x**2 + error_y**2)
            
            # Check if this is a new target or existing one
            if self.current_target is None:
                # New target detected
                self.current_target = {
                    'center_x': center_x,
                    'center_y': center_y,
                    'radius': radius,
                    'confidence': confidence,
                }
                self.target_lock_start_time = time.time()
                self.logger.info(f"New target detected at ({center_x}, {center_y}), radius: {radius}")
            
            # Check if target is centered enough to log
            if total_error <= self.centering_accuracy:
                # Target is well centered - log it
                detection_time = time.time() - self.target_lock_start_time if self.target_lock_start_time else 0.0
                
                # Check if we've already logged this target (avoid duplicates)
                is_duplicate = self._is_duplicate_target(center_x, center_y)
                
                if not is_duplicate:
                    self._log_target(frame, center_x, center_y, error_x, error_y, detection_time)
                    self.logger.info(f"✓ Target {len(self.targets_found)}/{self.target_count_required} logged")
                    self.logger.info(f"  Centering error: {total_error:.1f} pixels")
                    self.logger.info(f"  Detection time: {detection_time:.2f}s")
                    
                    # Reset current target to search for next one
                    self.current_target = None
                    self.target_lock_start_time = None
                else:
                    self.logger.info("Duplicate target ignored")
            else:
                # Target not centered yet
                if self.target_lock_start_time:
                    elapsed = time.time() - self.target_lock_start_time
                    self.logger.debug(f"Centering target... error: {total_error:.1f}px, time: {elapsed:.1f}s")
        
        except Exception as e:
            self.logger.error(f"Error processing target detection: {e}", exc_info=True)
            self.metrics['errors_encountered'] += 1
    
    def _is_duplicate_target(self, center_x: int, center_y: int) -> bool:
        """
        Check if target at given location has already been logged
        
        Args:
            center_x: Target X coordinate
            center_y: Target Y coordinate
            
        Returns:
            True if duplicate, False if new target
        """
        duplicate_threshold = 100  # pixels
        
        for target in self.targets_found:
            tx = target.get('center_x', 0)
            ty = target.get('center_y', 0)
            distance = np.sqrt((center_x - tx)**2 + (center_y - ty)**2)
            
            if distance < duplicate_threshold:
                return True
        
        return False
    
    def _log_target(
        self,
        frame,
        center_x: int,
        center_y: int,
        error_x: float,
        error_y: float,
        detection_time: float
    ):
        """
        Log target with GPS coordinates and photo
        
        Args:
            frame: Current camera frame
            center_x: Target X coordinate
            center_y: Target Y coordinate
            error_x: Centering error X
            error_y: Centering error Y
            detection_time: Time to detect and center
        """
        try:
            # Get GPS coordinates from telemetry
            latitude = getattr(self.telemetry, 'latitude', 0.0) if self.telemetry else 0.0
            longitude = getattr(self.telemetry, 'longitude', 0.0) if self.telemetry else 0.0
            altitude = getattr(self.telemetry, 'altitude', 0.0) if self.telemetry else 0.0
            heading = getattr(self.telemetry, 'heading', 0.0) if self.telemetry else 0.0
            
            # Generate unique target ID
            target_id = len(self.targets_found) + 1
            timestamp = datetime.now()
            
            # Save photo
            photo_filename = f"target_{target_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            photo_path = self.photo_dir / photo_filename
            cv2.imwrite(str(photo_path), frame)
            
            # Calculate target score
            target_score = self._calculate_target_score(error_x, error_y, detection_time)
            
            # Log to CSV
            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp.isoformat(),
                    target_id,
                    latitude,
                    longitude,
                    altitude,
                    heading,
                    error_x,
                    error_y,
                    detection_time,
                    str(photo_path),
                    target_score
                ])
            
            # Store target info
            target_info = {
                'target_id': target_id,
                'timestamp': timestamp,
                'center_x': center_x,
                'center_y': center_y,
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude,
                'heading': heading,
                'error_x': error_x,
                'error_y': error_y,
                'detection_time': detection_time,
                'photo_path': str(photo_path),
                'score': target_score,
            }
            
            self.targets_found.append(target_info)
            
            self.logger.info(f"Target logged: GPS({latitude:.6f}, {longitude:.6f}), Score: {target_score:.1f}")
            
        except Exception as e:
            self.logger.error(f"Error logging target: {e}", exc_info=True)
            self.metrics['errors_encountered'] += 1
    
    def _calculate_target_score(
        self,
        error_x: float,
        error_y: float,
        detection_time: float
    ) -> float:
        """
        Calculate score for individual target
        
        Args:
            error_x: Centering error X
            error_y: Centering error Y
            detection_time: Time to detect and center
            
        Returns:
            Score for this target
        """
        base_score = 20.0
        
        # Centering accuracy bonus
        total_error = np.sqrt(error_x**2 + error_y**2)
        if total_error < self.centering_accuracy:
            centering_bonus = 10.0 * (1.0 - total_error / self.centering_accuracy)
            base_score += centering_bonus
        
        # Quick identification bonus
        if detection_time < self.identification_time_bonus:
            time_bonus = 5.0
            base_score += time_bonus
        
        return min(base_score, 35.0)  # Max 35 points per target
    
    def _calculate_score(self) -> float:
        """
        Calculate overall task score
        
        Returns:
            Task score (0-100)
        """
        if not self.targets_found:
            return 0.0
        
        # Sum individual target scores
        target_scores = sum(t['score'] for t in self.targets_found)
        
        # Completion bonus
        if len(self.targets_found) >= self.target_count_required:
            completion_bonus = 10.0
        else:
            # Partial credit
            completion_ratio = len(self.targets_found) / self.target_count_required
            completion_bonus = 10.0 * completion_ratio
        
        # Time bonus
        if self.search_start_time:
            time_used = self.elapsed_time
            time_bonus = max(0, (1.0 - time_used / self.timeout) * 10.0)
        else:
            time_bonus = 0.0
        
        total_score = target_scores + completion_bonus + time_bonus
        
        self.logger.info(f"Score breakdown:")
        self.logger.info(f"  Target scores: {target_scores:.1f}")
        self.logger.info(f"  Completion bonus: {completion_bonus:.1f}")
        self.logger.info(f"  Time bonus: {time_bonus:.1f}")
        self.logger.info(f"  Total: {total_score:.1f}/100")
        
        return min(total_score, 100.0)
    
    def _on_stop(self):
        """Cleanup target search"""
        self.logger.info(f"Target search complete")
        self.logger.info(f"Targets found: {len(self.targets_found)}/{self.target_count_required}")
        self.logger.info(f"Results saved to: {self.csv_file}")
