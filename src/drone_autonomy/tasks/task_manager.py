"""
Task Manager for Competition

Manages execution of multiple tasks including:
- Task scheduling and sequencing
- State transitions
- Performance monitoring
- Result aggregation
- Competition scoring
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path

from .base_task import BaseTask, TaskStatus, TaskResult


@dataclass
class CompetitionResult:
    """
    Overall competition result
    
    Attributes:
        total_score: Total competition score
        tasks_completed: Number of tasks completed successfully
        tasks_failed: Number of failed tasks
        total_duration: Total competition time
        task_results: Individual task results
        overall_rank: Competition rank (if applicable)
    """
    total_score: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_duration: float = 0.0
    task_results: List[TaskResult] = field(default_factory=list)
    overall_rank: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_score': self.total_score,
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed,
            'total_duration': self.total_duration,
            'task_results': [tr.to_dict() for tr in self.task_results],
            'overall_rank': self.overall_rank,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class TaskManager:
    """
    Manages execution of competition tasks
    
    Features:
    - Sequential task execution
    - Automatic state management
    - Score calculation
    - Results aggregation
    - Safety monitoring
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        telemetry,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize task manager
        
        Args:
            config: Configuration dictionary
            telemetry: MAVLink telemetry interface
            logger: Logger instance (optional)
        """
        self.config = config
        self.telemetry = telemetry
        self.logger = logger or logging.getLogger("TaskManager")
        
        # Task queue
        self.tasks: List[BaseTask] = []
        self.current_task: Optional[BaseTask] = None
        self.current_task_index: int = 0
        
        # Results
        self.task_results: List[TaskResult] = []
        self.competition_start_time: Optional[float] = None
        self.competition_end_time: Optional[float] = None
        
        # Configuration
        self.max_tasks = config.get('max_tasks', 10)
        self.auto_advance = config.get('auto_advance', True)
        self.stop_on_failure = config.get('stop_on_failure', False)
        
        # Logging
        self.log_dir = Path(config.get('log_dir', 'logs/competition'))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("TaskManager initialized")
        self.logger.info(f"Max tasks: {self.max_tasks}, Auto-advance: {self.auto_advance}")
    
    def add_task(self, task: BaseTask) -> bool:
        """
        Add task to queue
        
        Args:
            task: Task to add
            
        Returns:
            True if added successfully, False otherwise
        """
        if len(self.tasks) >= self.max_tasks:
            self.logger.error(f"Cannot add task: maximum {self.max_tasks} tasks allowed")
            return False
        
        self.tasks.append(task)
        self.logger.info(f"Task added: {task.task_name} ({len(self.tasks)}/{self.max_tasks})")
        return True
    
    def start_competition(self) -> bool:
        """
        Start competition execution
        
        Returns:
            True if competition started, False otherwise
        """
        if not self.tasks:
            self.logger.error("No tasks in queue")
            return False
        
        self.logger.info("=" * 80)
        self.logger.info("STARTING COMPETITION")
        self.logger.info(f"Total tasks: {len(self.tasks)}")
        self.logger.info("=" * 80)
        
        self.competition_start_time = datetime.now().timestamp()
        self.current_task_index = 0
        
        # Start first task
        return self.start_next_task()
    
    def start_next_task(self) -> bool:
        """
        Start next task in queue
        
        Returns:
            True if task started, False if no more tasks
        """
        if self.current_task_index >= len(self.tasks):
            self.logger.info("All tasks completed")
            return False
        
        self.current_task = self.tasks[self.current_task_index]
        self.logger.info(f"\n{'=' * 80}")
        self.logger.info(f"Starting Task {self.current_task_index + 1}/{len(self.tasks)}: {self.current_task.task_name}")
        self.logger.info(f"{'=' * 80}\n")
        
        return self.current_task.start()
    
    def update(
        self,
        frame,
        depth_map,
        detections: List[Dict],
        target_detection: Optional[Dict] = None
    ) -> bool:
        """
        Update current task with sensor data
        
        Args:
            frame: Current camera frame
            depth_map: Depth estimation map
            detections: List of object detections
            target_detection: Target circle detection (if any)
            
        Returns:
            True if task/competition continues, False if complete
        """
        if not self.current_task:
            return False
        
        # Update current task
        task_continues = self.current_task.update(frame, depth_map, detections, target_detection)
        
        # Check if task is complete
        if not task_continues or self.current_task.status != TaskStatus.RUNNING:
            # Task complete or failed
            result = self.current_task.stop()
            self.task_results.append(result)
            
            self.logger.info(f"\nTask {self.current_task_index + 1} complete:")
            self.logger.info(f"  Status: {result.status.value}")
            self.logger.info(f"  Score: {result.score:.1f}/100")
            self.logger.info(f"  Duration: {result.duration:.2f}s\n")
            
            # Check if should continue to next task
            if result.status == TaskStatus.FAILED and self.stop_on_failure:
                self.logger.error("Task failed - stopping competition")
                return False
            
            # Advance to next task
            self.current_task_index += 1
            
            if self.current_task_index < len(self.tasks):
                if self.auto_advance:
                    return self.start_next_task()
                else:
                    self.logger.info("Waiting for manual task advancement...")
                    return False
            else:
                # All tasks complete
                return False
        
        return True
    
    def stop_competition(self) -> CompetitionResult:
        """
        Stop competition and generate results
        
        Returns:
            CompetitionResult with aggregated scores
        """
        self.logger.info("\n" + "=" * 80)
        self.logger.info("COMPETITION COMPLETE")
        self.logger.info("=" * 80)
        
        # Stop current task if running
        if self.current_task and self.current_task.status == TaskStatus.RUNNING:
            result = self.current_task.stop("Competition ended")
            self.task_results.append(result)
        
        self.competition_end_time = datetime.now().timestamp()
        total_duration = self.competition_end_time - self.competition_start_time if self.competition_start_time else 0.0
        
        # Calculate totals
        total_score = sum(r.score for r in self.task_results)
        tasks_completed = sum(1 for r in self.task_results if r.success)
        tasks_failed = sum(1 for r in self.task_results if not r.success)
        
        # Generate competition result
        competition_result = CompetitionResult(
            total_score=total_score,
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed,
            total_duration=total_duration,
            task_results=self.task_results,
        )
        
        # Log summary
        self.logger.info(f"\nCompetition Summary:")
        self.logger.info(f"  Total Score: {total_score:.1f}")
        self.logger.info(f"  Tasks Completed: {tasks_completed}/{len(self.tasks)}")
        self.logger.info(f"  Tasks Failed: {tasks_failed}/{len(self.tasks)}")
        self.logger.info(f"  Total Duration: {total_duration:.2f}s")
        self.logger.info(f"\nIndividual Task Scores:")
        for i, result in enumerate(self.task_results):
            self.logger.info(f"  Task {i+1}: {result.score:.1f}/100 ({result.status.value})")
        
        # Save results
        self._save_competition_result(competition_result)
        
        return competition_result
    
    def abort_competition(self, reason: str = "Aborted"):
        """
        Abort competition immediately
        
        Args:
            reason: Abort reason
        """
        self.logger.warning(f"Aborting competition: {reason}")
        
        # Stop current task
        if self.current_task and self.current_task.status == TaskStatus.RUNNING:
            self.current_task.abort(reason)
        
        # Generate results with current state
        return self.stop_competition()
    
    def _save_competition_result(self, result: CompetitionResult):
        """
        Save competition result to file
        
        Args:
            result: CompetitionResult to save
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_file = self.log_dir / f"competition_{timestamp}.json"
            
            with open(result_file, 'w') as f:
                f.write(result.to_json())
            
            self.logger.info(f"\nCompetition results saved to: {result_file}")
        except Exception as e:
            self.logger.error(f"Error saving competition result: {e}", exc_info=True)
