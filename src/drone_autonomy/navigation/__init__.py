"""
Autonomous Navigation Module
Handles obstacle avoidance, target approach, and mission execution
"""

from .autonomous_controller import AutonomousController
from .obstacle_avoidance import ObstacleAvoider, Obstacle, PathSegment, RiskLevel

__all__ = [
    'AutonomousController',
    'ObstacleAvoider',
    'Obstacle',
    'PathSegment',
    'RiskLevel'
]
