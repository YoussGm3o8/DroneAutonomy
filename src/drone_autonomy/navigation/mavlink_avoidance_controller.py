"""
MAVLink-Integrated Obstacle Avoidance Controller

This module combines real-time obstacle detection with MAVLink command execution
to provide autonomous object avoidance for drones.

Features:
- Real-time depth-based obstacle detection
- Path planning and trajectory generation
- MAVLink velocity command execution
- Safety monitoring and emergency stop
- Integration with visual odometry
"""

import logging
import time
import numpy as np
from typing import Optional, Dict, Any, Tuple
from enum import Enum

from ..navigation.obstacle_avoidance import ObstacleAvoider, RiskLevel
from ..mavlink.telemetry import MAVLinkTelemetry


class AvoidanceState(Enum):
    """Controller states"""
    IDLE = "idle"
    MONITORING = "monitoring"
    AVOIDING = "avoiding"
    EMERGENCY_STOP = "emergency_stop"
    PAUSED = "paused"


class MAVLinkAvoidanceController:
    """
    MAVLink-integrated obstacle avoidance controller.

    This controller monitors depth maps for obstacles, generates avoidance paths,
    and executes them using MAVLink velocity commands.
    """

    def __init__(
        self,
        mavlink: MAVLinkTelemetry,
        avoider: ObstacleAvoider,
        config: Dict[str, Any],
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize MAVLink avoidance controller.

        Args:
            mavlink: MAVLink telemetry interface
            avoider: Obstacle avoidance system
            config: Configuration dictionary
            logger: Logger instance
        """
        self.mavlink = mavlink
        self.avoider = avoider
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        # Control parameters
        self.max_velocity = config.get('max_velocity', 2.0)  # m/s
        self.avoidance_velocity = config.get('avoidance_velocity', 1.0)  # m/s
        self.emergency_distance = config.get('emergency_distance', 1.0)  # m
        self.update_rate = config.get('update_rate', 10)  # Hz
        self.lateral_gain = config.get('lateral_gain', 1.5)  # Lateral correction gain

        # Safety parameters
        self.enable_emergency_stop = config.get('enable_emergency_stop', True)
        self.min_altitude = config.get('min_altitude', 1.0)  # m
        self.max_altitude = config.get('max_altitude', 50.0)  # m

        # State
        self.state = AvoidanceState.IDLE
        self.enabled = False
        self.last_update_time = 0
        self.last_command_time = 0

        # Statistics
        self.stats = {
            'obstacles_detected': 0,
            'avoidance_maneuvers': 0,
            'emergency_stops': 0,
            'total_runtime': 0
        }

        self.logger.info("MAVLink Avoidance Controller initialized")
        self.logger.info(f"  Max velocity: {self.max_velocity} m/s")
        self.logger.info(f"  Avoidance velocity: {self.avoidance_velocity} m/s")
        self.logger.info(f"  Emergency distance: {self.emergency_distance} m")

    def start(self) -> bool:
        """
        Start the avoidance controller.

        Returns:
            True if started successfully, False otherwise
        """
        if not self.mavlink.is_connected:
            self.logger.error("Cannot start: MAVLink not connected")
            return False

        # Ensure vehicle is in GUIDED mode
        if self.mavlink.flight_mode != "GUIDED":
            self.logger.info("Switching to GUIDED mode...")
            if not self.mavlink.set_mode("GUIDED"):
                self.logger.error("Failed to switch to GUIDED mode")
                return False
            time.sleep(1)  # Wait for mode change

        self.enabled = True
        self.state = AvoidanceState.MONITORING
        self.last_update_time = time.time()
        self.logger.info("Avoidance controller started - monitoring for obstacles")
        return True

    def stop(self):
        """Stop the avoidance controller."""
        self.enabled = False
        self.state = AvoidanceState.IDLE
        self.logger.info("Avoidance controller stopped")

    def pause(self):
        """Pause the avoidance controller (hold position)."""
        if self.enabled:
            self.mavlink.pause()
            self.state = AvoidanceState.PAUSED
            self.logger.info("Avoidance controller paused")

    def resume(self):
        """Resume the avoidance controller."""
        if self.state == AvoidanceState.PAUSED:
            self.mavlink.resume_guided()
            self.state = AvoidanceState.MONITORING
            self.logger.info("Avoidance controller resumed")

    def emergency_stop(self):
        """Execute emergency stop."""
        self.logger.warning("EMERGENCY STOP triggered")
        self.mavlink.pause()  # Use BRAKE/LOITER instead of motor disarm
        self.state = AvoidanceState.EMERGENCY_STOP
        self.stats['emergency_stops'] += 1

    def update(
        self,
        depth_map: np.ndarray,
        current_velocity: Optional[Tuple[float, float, float]] = None,
        target_position: Optional[Tuple[int, int]] = None
    ) -> Dict[str, Any]:
        """
        Update controller with new sensor data and execute avoidance.

        Args:
            depth_map: Current depth map from depth estimator
            current_velocity: Current velocity (vx, vy, vz) in m/s (optional)
            target_position: Target position (x, y) in image coords if following target

        Returns:
            Status dictionary with controller state and metrics
        """
        if not self.enabled or self.state == AvoidanceState.IDLE:
            return {'active': False, 'state': self.state.value}

        current_time = time.time()
        dt = current_time - self.last_update_time

        # Rate limiting
        if dt < 1.0 / self.update_rate:
            return {'active': True, 'state': self.state.value, 'rate_limited': True}

        self.last_update_time = current_time

        try:
            # 1. Detect obstacles from depth map
            obstacles = self.avoider.detect_obstacles(depth_map)
            self.stats['obstacles_detected'] = len(obstacles)

            # 2. Check for critical obstacles (emergency condition)
            critical_obstacles = [
                obs for obs in obstacles
                if obs.distance < self.emergency_distance
            ]

            if critical_obstacles and self.enable_emergency_stop:
                self.logger.error(f"Critical obstacle at {critical_obstacles[0].distance:.2f}m - EMERGENCY STOP")
                self.emergency_stop()
                return {
                    'active': True,
                    'state': self.state.value,
                    'emergency': True,
                    'obstacle_distance': critical_obstacles[0].distance
                }

            # 3. Determine if avoidance is needed
            should_avoid = self.avoider.should_avoid()

            if should_avoid and self.state != AvoidanceState.EMERGENCY_STOP:
                # Generate avoidance paths
                frame_shape = depth_map.shape if depth_map is not None else (480, 640)
                paths = self.avoider.generate_path_candidates(frame_shape, target_position)

                # Execute avoidance maneuver
                self._execute_avoidance()
                self.state = AvoidanceState.AVOIDING
                self.stats['avoidance_maneuvers'] += 1

                return {
                    'active': True,
                    'state': self.state.value,
                    'avoiding': True,
                    'num_obstacles': len(obstacles),
                    'selected_path_safe': self.avoider.selected_path.is_safe if self.avoider.selected_path else False
                }

            else:
                # No obstacles - continue normal operation
                if self.state == AvoidanceState.AVOIDING:
                    self.state = AvoidanceState.MONITORING
                    self.logger.info("Avoidance complete - resuming monitoring")

                # Send nominal forward velocity if monitoring
                if current_velocity is None:
                    self._send_nominal_velocity()

                return {
                    'active': True,
                    'state': self.state.value,
                    'avoiding': False,
                    'num_obstacles': len(obstacles)
                }

        except Exception as e:
            self.logger.error(f"Error in avoidance controller update: {e}", exc_info=True)
            return {
                'active': True,
                'state': self.state.value,
                'error': str(e)
            }

    def _execute_avoidance(self):
        """Execute avoidance maneuver based on selected path."""
        if not self.avoider.selected_path:
            self.logger.warning("No path selected - sending stop command")
            self.mavlink.send_velocity_body(0, 0, 0, 0)
            return

        # Get avoidance command from path planner
        avoidance_cmd = self.avoider.get_avoidance_command()

        if not avoidance_cmd.get('avoid', False):
            return

        # Extract lateral command (-1 to 1)
        lateral = avoidance_cmd.get('lateral', 0.0)

        # Convert to body-frame velocity
        # Forward velocity reduced during avoidance
        vx_body = self.avoidance_velocity * 0.5  # Slow forward during avoidance
        vy_body = lateral * self.lateral_gain  # Lateral correction
        vz_body = 0.0  # Maintain altitude
        yaw_rate = lateral * 0.5  # Yaw in direction of avoidance

        # Safety limits
        vx_body = np.clip(vx_body, 0, self.max_velocity)
        vy_body = np.clip(vy_body, -self.max_velocity, self.max_velocity)

        # Send velocity command
        self.mavlink.send_velocity_body(vx_body, vy_body, vz_body, yaw_rate)
        self.last_command_time = time.time()

        self.logger.debug(
            f"Avoidance command: vx={vx_body:.2f}, vy={vy_body:.2f}, "
            f"clearance={avoidance_cmd.get('clearance', 0):.2f}m"
        )

    def _send_nominal_velocity(self):
        """Send nominal forward velocity when no obstacles detected."""
        # Slow forward velocity during monitoring
        vx_body = self.avoidance_velocity
        vy_body = 0.0
        vz_body = 0.0
        yaw_rate = 0.0

        self.mavlink.send_velocity_body(vx_body, vy_body, vz_body, yaw_rate)
        self.last_command_time = time.time()

    def manual_avoid_left(self, intensity: float = 1.0):
        """
        Manually command avoidance to the left.

        Args:
            intensity: Avoidance intensity 0.0-1.0
        """
        vx_body = self.avoidance_velocity * 0.5
        vy_body = -self.lateral_gain * intensity  # Negative = left
        vz_body = 0.0
        yaw_rate = -0.3 * intensity

        self.mavlink.send_velocity_body(vx_body, vy_body, vz_body, yaw_rate)
        self.logger.info(f"Manual avoidance LEFT (intensity: {intensity:.1f})")

    def manual_avoid_right(self, intensity: float = 1.0):
        """
        Manually command avoidance to the right.

        Args:
            intensity: Avoidance intensity 0.0-1.0
        """
        vx_body = self.avoidance_velocity * 0.5
        vy_body = self.lateral_gain * intensity  # Positive = right
        vz_body = 0.0
        yaw_rate = 0.3 * intensity

        self.mavlink.send_velocity_body(vx_body, vy_body, vz_body, yaw_rate)
        self.logger.info(f"Manual avoidance RIGHT (intensity: {intensity:.1f})")

    def manual_stop(self):
        """Manually stop the vehicle."""
        self.mavlink.send_velocity_body(0, 0, 0, 0)
        self.logger.info("Manual STOP command")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current controller status.

        Returns:
            Status dictionary
        """
        return {
            'enabled': self.enabled,
            'state': self.state.value,
            'mavlink_connected': self.mavlink.is_connected,
            'flight_mode': self.mavlink.flight_mode,
            'obstacles_detected': self.stats['obstacles_detected'],
            'avoidance_maneuvers': self.stats['avoidance_maneuvers'],
            'emergency_stops': self.stats['emergency_stops'],
            'avoidance_active': self.avoider.avoidance_active,
            'selected_path_safe': (
                self.avoider.selected_path.is_safe
                if self.avoider.selected_path else None
            )
        }

    def get_visualization_frame(self, frame: np.ndarray, depth_map: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Get frame with obstacle avoidance visualization overlay.

        Args:
            frame: Input video frame
            depth_map: Optional depth map for visualization

        Returns:
            Frame with visualization overlay
        """
        return self.avoider.visualize(frame, depth_map)

    def reset_statistics(self):
        """Reset controller statistics."""
        self.stats = {
            'obstacles_detected': 0,
            'avoidance_maneuvers': 0,
            'emergency_stops': 0,
            'total_runtime': 0
        }
        self.logger.info("Controller statistics reset")
