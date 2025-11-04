"""
MAVLink Proximity Sensor Monitor
Interfaces with ArduPilot proximity sensors (rangefinders, lidar) for obstacle detection
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SensorDirection(Enum):
    """Proximity sensor directions (MAVLink standard)"""
    FORWARD = 0
    BACK = 1
    RIGHT = 2
    LEFT = 3
    UP = 4
    DOWN = 5
    FORWARD_RIGHT = 6
    BACK_RIGHT = 7
    BACK_LEFT = 8
    FORWARD_LEFT = 9


@dataclass
class ProximityReading:
    """
    Single proximity sensor reading
    
    Attributes:
        direction: Sensor direction
        distance: Distance in meters
        min_distance: Sensor minimum range
        max_distance: Sensor maximum range
        valid: Whether reading is valid
        timestamp: Reading timestamp
    """
    direction: SensorDirection
    distance: float
    min_distance: float
    max_distance: float
    valid: bool
    timestamp: float


class ProximityMonitor:
    """
    Monitor proximity sensors from ArduPilot
    
    Features:
    - Read rangefinder/lidar distances via MAVLink
    - Track multiple sensor directions
    - Detect critical obstacles
    - Provide sensor health status
    """
    
    def __init__(self, telemetry, config: Dict, logger: Optional[logging.Logger] = None):
        """
        Initialize proximity monitor
        
        Args:
            telemetry: MAVLink telemetry interface
            config: Configuration dictionary
            logger: Logger instance
        """
        self.telemetry = telemetry
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Thresholds
        self.critical_distance = config.get('critical_distance', 1.5)  # meters
        self.warning_distance = config.get('warning_distance', 2.5)  # meters
        
        # Sensor configuration
        self.enabled_directions = config.get('enabled_directions', [
            SensorDirection.FORWARD,
            SensorDirection.LEFT,
            SensorDirection.RIGHT,
            SensorDirection.DOWN
        ])
        
        # State
        self.last_readings: Dict[SensorDirection, ProximityReading] = {}
        self.sensor_timeout = config.get('sensor_timeout', 1.0)  # seconds
        
        self.logger.info(f"Proximity Monitor initialized")
        self.logger.info(f"  Critical distance: {self.critical_distance}m")
        self.logger.info(f"  Warning distance: {self.warning_distance}m")
        self.logger.info(f"  Enabled directions: {[d.name for d in self.enabled_directions]}")
    
    def update(self) -> Dict[SensorDirection, ProximityReading]:
        """
        Update proximity readings from MAVLink
        
        Returns:
            Dictionary of current readings by direction
        """
        # Request DISTANCE_SENSOR messages from ArduPilot
        # Message ID 132: DISTANCE_SENSOR
        try:
            # Get latest distance sensor messages
            distance_sensors = self.telemetry.get_distance_sensors()
            
            for sensor_data in distance_sensors:
                direction = SensorDirection(sensor_data.orientation)
                
                if direction in self.enabled_directions:
                    reading = ProximityReading(
                        direction=direction,
                        distance=sensor_data.current_distance / 100.0,  # cm to meters
                        min_distance=sensor_data.min_distance / 100.0,
                        max_distance=sensor_data.max_distance / 100.0,
                        valid=sensor_data.current_distance > 0,
                        timestamp=sensor_data.time_boot_ms / 1000.0
                    )
                    
                    self.last_readings[direction] = reading
        
        except Exception as e:
            self.logger.warning(f"Failed to read proximity sensors: {e}")
        
        return self.last_readings
    
    def get_distance(self, direction: SensorDirection) -> Optional[float]:
        """
        Get distance for specific direction
        
        Args:
            direction: Sensor direction
            
        Returns:
            Distance in meters, or None if not available
        """
        reading = self.last_readings.get(direction)
        if reading and reading.valid:
            return reading.distance
        return None
    
    def get_all_distances(self) -> Dict[str, float]:
        """
        Get all valid distances
        
        Returns:
            Dictionary of direction name to distance
        """
        distances = {}
        for direction, reading in self.last_readings.items():
            if reading.valid:
                distances[direction.name.lower()] = reading.distance
        return distances
    
    def has_critical_obstacle(self) -> bool:
        """
        Check if any sensor reports critical distance
        
        Returns:
            True if critical obstacle detected
        """
        for reading in self.last_readings.values():
            if reading.valid and reading.distance < self.critical_distance:
                return True
        return False
    
    def has_warning_obstacle(self) -> bool:
        """
        Check if any sensor reports warning distance
        
        Returns:
            True if warning obstacle detected
        """
        for reading in self.last_readings.values():
            if reading.valid and reading.distance < self.warning_distance:
                return True
        return False
    
    def get_closest_obstacle(self) -> Optional[Tuple[SensorDirection, float]]:
        """
        Get closest obstacle direction and distance
        
        Returns:
            Tuple of (direction, distance) or None
        """
        valid_readings = [r for r in self.last_readings.values() if r.valid]
        
        if not valid_readings:
            return None
        
        closest = min(valid_readings, key=lambda r: r.distance)
        return (closest.direction, closest.distance)
    
    def get_sensor_health(self) -> Dict[str, bool]:
        """
        Get health status of all sensors
        
        Returns:
            Dictionary of direction name to health status
        """
        health = {}
        
        for direction in self.enabled_directions:
            reading = self.last_readings.get(direction)
            
            # Sensor is healthy if:
            # 1. Has recent reading
            # 2. Reading is valid
            # 3. Distance is within sensor range
            is_healthy = False
            
            if reading:
                is_healthy = (
                    reading.valid and
                    reading.min_distance <= reading.distance <= reading.max_distance
                )
            
            health[direction.name.lower()] = is_healthy
        
        return health
    
    def get_avoidance_command(self) -> Optional[Dict[str, float]]:
        """
        Generate simple avoidance command based on proximity sensors
        
        Returns:
            Command dictionary or None if no avoidance needed
        """
        # Check for obstacles
        closest = self.get_closest_obstacle()
        
        if not closest:
            return None
        
        direction, distance = closest
        
        if distance >= self.warning_distance:
            return None  # No avoidance needed
        
        # Calculate avoidance intensity
        if distance < self.critical_distance:
            intensity = 1.0  # Maximum avoidance
        else:
            # Scale from 0 to 1 between warning and critical
            intensity = 1.0 - (distance - self.critical_distance) / (self.warning_distance - self.critical_distance)
        
        # Generate command based on direction
        command = {
            'avoid': True,
            'intensity': intensity,
            'obstacle_direction': direction.name.lower(),
            'distance': distance
        }
        
        # Direction-specific avoidance
        if direction == SensorDirection.FORWARD:
            command['forward'] = -intensity * 0.5  # Back up
        elif direction == SensorDirection.BACK:
            command['forward'] = intensity * 0.5  # Move forward
        elif direction == SensorDirection.LEFT:
            command['right'] = intensity * 0.5  # Move right
        elif direction == SensorDirection.RIGHT:
            command['right'] = -intensity * 0.5  # Move left
        elif direction == SensorDirection.DOWN:
            command['up'] = intensity * 0.3  # Climb
        
        return command
    
    def log_status(self):
        """Log current sensor status"""
        distances = self.get_all_distances()
        health = self.get_sensor_health()
        
        self.logger.info("Proximity Sensor Status:")
        for direction in self.enabled_directions:
            dir_name = direction.name.lower()
            dist = distances.get(dir_name, None)
            healthy = health.get(dir_name, False)
            
            status = "✓" if healthy else "✗"
            dist_str = f"{dist:.2f}m" if dist is not None else "N/A"
            
            self.logger.info(f"  {status} {direction.name}: {dist_str}")
        
        closest = self.get_closest_obstacle()
        if closest:
            direction, distance = closest
            self.logger.info(f"  Closest: {direction.name} at {distance:.2f}m")
