"""
DroneAutonomy - Real-time drone autonomy system with monocular vision pipeline.

This package provides a comprehensive solution for autonomous perception and decision support
for obstacle avoidance and target detection using a single monocular camera, integrating 
state estimation, depth perception, and object/marker detection suitable for non-GPS and 
GPS-degraded flight.
"""

__version__ = "0.1.0"
__author__ = "DroneAutonomy Team"

from .video.stream import VideoStream
from .detection.yolo_detector import YOLODetector
from .detection.target_detector import TargetDetector
from .depth.depth_estimator import DepthEstimator
from .mavlink.telemetry import MAVLinkTelemetry
from .fusion.decision_layer import DecisionLayer

__all__ = [
    "VideoStream",
    "YOLODetector",
    "TargetDetector",
    "DepthEstimator",
    "MAVLinkTelemetry",
    "DecisionLayer",
]
