"""
Base Task Class for Competition Tasks

Provides a robust foundation for all competition tasks with:
- State management
- Error handling
- Performance metrics
- Safety checks
- Logging and telemetry
"""

import time
import logging
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    PAUSED = "paused"


@dataclass
class TaskResult:
    """
    Result of task execution
    
    Attributes:
        status: Final task status
        success: Whether task completed successfully
        score: Task score (0-100)
        duration: Execution time in seconds
        data: Task-specific result data
        errors: List of errors encountered
        warnings: List of warnings
        metrics: Performance metrics
    """
    status: TaskStatus
    success: bool
    score: float = 0.0
    duration: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'status': self.status.value,
            'success': self.success,
            'score': self.score,
            'duration': self.duration,
            'data': self.data,
            'errors': self.errors,
            'warnings': self.warnings,
            'metrics': self.metrics,
        }
    
    def to_json(self) -> str:
        """Convert result to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class BaseTask:
    """
    Base class for all competition tasks
    
    Features:
    - Lifecycle management (start, update, stop)
    - Safety checks and timeouts
    - Performance monitoring
    - Error handling and recovery
    - Telemetry integration
    - Result reporting
    """
    
    def __init__(
        self,
        task_id: str,
        task_name: str,
        config: Dict[str, Any],
        telemetry,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize base task
        
        Args:
            task_id: Unique task identifier
            task_name: Human-readable task name
            config: Task configuration dictionary
            telemetry: MAVLink telemetry interface
            logger: Logger instance (optional)
        """
        self.task_id = task_id
        self.task_name = task_name
        self.config = config
        self.telemetry = telemetry
        self.logger = logger or logging.getLogger(f"Task.{task_name}")
        
        # State
        self.status = TaskStatus.PENDING
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.elapsed_time: float = 0.0
        
        # Configuration
        self.timeout = config.get('timeout', 300.0)  # Default 5 minutes
        self.max_retries = config.get('max_retries', 3)
        self.retry_count = 0
        
        # Safety limits
        self.max_altitude = config.get('max_altitude', 20.0)  # meters
        self.min_altitude = config.get('min_altitude', 0.5)  # meters
        self.max_speed = config.get('max_speed', 5.0)  # m/s
        self.safety_distance = config.get('safety_distance', 2.0)  # meters from obstacles
        
        # Metrics
        self.metrics = {
            'frames_processed': 0,
            'decisions_made': 0,
            'warnings_issued': 0,
            'errors_encountered': 0,
        }
        
        # Logging
        self.log_dir = Path(config.get('log_dir', 'logs/tasks'))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Task initialized: {task_name} (ID: {task_id})")
        self.logger.info(f"Timeout: {self.timeout}s, Max retries: {self.max_retries}")
    
    def start(self) -> bool:
        """
        Start task execution
        
        Returns:
            True if task started successfully, False otherwise
        """
        try:
            if self.status != TaskStatus.PENDING:
                self.logger.warning(f"Cannot start task in {self.status.value} state")
                return False
            
            self.logger.info(f"Starting task: {self.task_name}")
            self.status = TaskStatus.RUNNING
            self.start_time = time.time()
            
            # Perform safety checks
            if not self._safety_check():
                self.logger.error("Safety check failed")
                self.status = TaskStatus.FAILED
                return False
            
            # Call task-specific initialization
            if not self._on_start():
                self.logger.error("Task initialization failed")
                self.status = TaskStatus.FAILED
                return False
            
            self.logger.info(f"Task started successfully: {self.task_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting task: {e}", exc_info=True)
            self.status = TaskStatus.FAILED
            self.metrics['errors_encountered'] += 1
            return False
    
    def update(
        self,
        frame,
        depth_map,
        detections: List[Dict],
        target_detection: Optional[Dict] = None
    ) -> bool:
        """
        Update task with new sensor data
        
        Args:
            frame: Current camera frame
            depth_map: Depth estimation map
            detections: List of object detections
            target_detection: Target circle detection (if any)
            
        Returns:
            True if task should continue, False if complete/failed
        """
        try:
            # Check if task is running
            if self.status != TaskStatus.RUNNING:
                return False
            
            # Update elapsed time
            self.elapsed_time = time.time() - self.start_time
            
            # Check timeout
            if self.elapsed_time > self.timeout:
                self.logger.warning(f"Task timeout after {self.elapsed_time:.1f}s")
                self.status = TaskStatus.FAILED
                return False
            
            # Safety checks
            if not self._safety_check():
                self.logger.error("Safety check failed during update")
                self.status = TaskStatus.ABORTED
                return False
            
            # Call task-specific update
            continue_task = self._on_update(frame, depth_map, detections, target_detection)
            
            self.metrics['frames_processed'] += 1
            
            return continue_task
            
        except Exception as e:
            self.logger.error(f"Error during task update: {e}", exc_info=True)
            self.metrics['errors_encountered'] += 1
            
            # Retry logic
            if self.retry_count < self.max_retries:
                self.retry_count += 1
                self.logger.info(f"Retrying task (attempt {self.retry_count}/{self.max_retries})")
                return True
            else:
                self.logger.error("Max retries exceeded")
                self.status = TaskStatus.FAILED
                return False
    
    def stop(self, reason: str = "Completed") -> TaskResult:
        """
        Stop task execution and return result
        
        Args:
            reason: Reason for stopping
            
        Returns:
            TaskResult with execution details
        """
        try:
            self.logger.info(f"Stopping task: {self.task_name} - Reason: {reason}")
            
            # Call task-specific cleanup
            self._on_stop()
            
            # Calculate duration
            self.end_time = time.time()
            if self.start_time:
                self.elapsed_time = self.end_time - self.start_time
            
            # Set final status if not already set
            if self.status == TaskStatus.RUNNING:
                self.status = TaskStatus.COMPLETED
            
            # Generate result
            result = self._generate_result()
            
            # Save results
            self._save_result(result)
            
            self.logger.info(f"Task stopped: {self.task_name} - Status: {result.status.value}")
            self.logger.info(f"Score: {result.score:.1f}, Duration: {result.duration:.2f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error stopping task: {e}", exc_info=True)
            return TaskResult(
                status=TaskStatus.FAILED,
                success=False,
                errors=[str(e)]
            )
    
    def abort(self, reason: str = "Aborted by user"):
        """
        Abort task execution immediately
        
        Args:
            reason: Abort reason
        """
        self.logger.warning(f"Aborting task: {reason}")
        self.status = TaskStatus.ABORTED
        self.stop(reason)
    
    def pause(self):
        """Pause task execution"""
        if self.status == TaskStatus.RUNNING:
            self.logger.info("Pausing task")
            self.status = TaskStatus.PAUSED
    
    def resume(self):
        """Resume task execution"""
        if self.status == TaskStatus.PAUSED:
            self.logger.info("Resuming task")
            self.status = TaskStatus.RUNNING
    
    # ===== Virtual methods to be overridden by subclasses =====
    
    def _on_start(self) -> bool:
        """
        Task-specific initialization
        
        Returns:
            True if initialization successful, False otherwise
        """
        return True
    
    def _on_update(
        self,
        frame,
        depth_map,
        detections: List[Dict],
        target_detection: Optional[Dict]
    ) -> bool:
        """
        Task-specific update logic
        
        Returns:
            True to continue task, False to complete
        """
        return True
    
    def _on_stop(self):
        """Task-specific cleanup"""
        pass
    
    def _calculate_score(self) -> float:
        """
        Calculate task score (0-100)
        
        Returns:
            Score value
        """
        return 0.0
    
    # ===== Helper methods =====
    
    def _safety_check(self) -> bool:
        """
        Perform safety checks
        
        Returns:
            True if safe to continue, False otherwise
        """
        try:
            # Check telemetry connection
            if not self.telemetry:
                self.logger.warning("No telemetry connection")
                return True  # Continue without telemetry for simulation
            
            # Check altitude limits
            altitude = getattr(self.telemetry, 'altitude', None)
            if altitude is not None:
                if altitude > self.max_altitude:
                    self.logger.error(f"Altitude too high: {altitude:.1f}m > {self.max_altitude}m")
                    return False
                if altitude < self.min_altitude:
                    self.logger.error(f"Altitude too low: {altitude:.1f}m < {self.min_altitude}m")
                    return False
            
            # Check battery level
            battery = getattr(self.telemetry, 'battery_percent', None)
            if battery is not None and battery < 20:
                self.logger.warning(f"Low battery: {battery}%")
                self.metrics['warnings_issued'] += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"Safety check error: {e}", exc_info=True)
            return False
    
    def _generate_result(self) -> TaskResult:
        """
        Generate task result
        
        Returns:
            TaskResult object
        """
        success = self.status == TaskStatus.COMPLETED
        score = self._calculate_score() if success else 0.0
        
        return TaskResult(
            status=self.status,
            success=success,
            score=score,
            duration=self.elapsed_time,
            metrics=self.metrics.copy(),
            data={
                'task_id': self.task_id,
                'task_name': self.task_name,
                'start_time': datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
                'end_time': datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            }
        )
    
    def _save_result(self, result: TaskResult):
        """
        Save task result to file
        
        Args:
            result: TaskResult to save
        """
        try:
            result_file = self.log_dir / f"{self.task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(result_file, 'w') as f:
                f.write(result.to_json())
            self.logger.info(f"Result saved to: {result_file}")
        except Exception as e:
            self.logger.error(f"Error saving result: {e}", exc_info=True)
