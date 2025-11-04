"""
GUI Module for Drone Autonomy System

Provides a comprehensive graphical interface for:
- Task selection and execution
- Live video streaming with overlays
- Saved media gallery (images/videos)
- Results viewer (descriptions, scores, logs)
- Configuration management
- Real-time telemetry monitoring
- Task 1: Fire Reconnaissance control panel
"""

from .main_window import MainWindow
from .video_widget import VideoWidget
from .task_control import TaskControlPanel
from .media_gallery import MediaGallery
from .results_viewer import ResultsViewer
from .telemetry_display import TelemetryDisplay
from .settings_dialog import SettingsDialog
from .task1_fire_recon_panel import Task1FireReconPanel
from .drone_control_panel import DroneControlPanel
from .avoidance_control_panel import AvoidanceControlPanel
from .mavlink_command_panel import MAVLinkCommandPanel

__all__ = [
    'MainWindow',
    'VideoWidget',
    'TaskControlPanel',
    'MediaGallery',
    'ResultsViewer',
    'TelemetryDisplay',
    'SettingsDialog',
    'Task1FireReconPanel',
    'DroneControlPanel',
    'AvoidanceControlPanel',
    'MAVLinkCommandPanel',
]
