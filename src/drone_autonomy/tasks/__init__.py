"""
Competition Tasks Module

Provides robust task execution capabilities for drone competitions including:
- Target search and identification
- Waypoint navigation
- Obstacle avoidance
- Precision landing
- Object delivery
- Surveillance patterns
- Autonomous wet-capture with deliverable upload
- Landmark-based positioning
- Fire reconnaissance with equipment delivery
"""

from .base_task import BaseTask, TaskStatus, TaskResult
from .task_manager import TaskManager
from .target_search import TargetSearchTask
from .waypoint_navigation import WaypointNavigationTask
from .obstacle_course import ObstacleCourseTask
from .precision_landing import PrecisionLandingTask
from .autonomous_wet_capture import AutonomousWetCaptureTask
from .landmark_description import (
    LandmarkBasedDescriptionGenerator,
    BuildingDimensions,
    TargetDescription,
    LandmarkType,
)
from .actuators import WaterActuator, AutoUploader
from .fire_reconnaissance import (
    FireReconnaissance,
    DroneType,
    MissionState,
    FlightBoundary,
    BuildingConfig,
    Equipment,
    TargetDetection,
)

__all__ = [
    'BaseTask',
    'TaskStatus',
    'TaskResult',
    'TaskManager',
    'TargetSearchTask',
    'WaypointNavigationTask',
    'ObstacleCourseTask',
    'PrecisionLandingTask',
    'AutonomousWetCaptureTask',
    'LandmarkBasedDescriptionGenerator',
    'BuildingDimensions',
    'TargetDescription',
    'LandmarkType',
    'WaterActuator',
    'AutoUploader',
    'FireReconnaissance',
    'DroneType',
    'MissionState',
    'FlightBoundary',
    'BuildingConfig',
    'Equipment',
    'TargetDetection',
]
