"""
Safety Arbitrator - Combines vision and sensor-based obstacle avoidance
Implements redundant safety through multi-source decision fusion
"""

import logging
from typing import Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass


class ArbitrationMode(Enum):
    """Arbitration strategies for combining inputs"""
    VISION_PRIMARY = "vision_primary"  # Vision first, sensors backup
    SENSOR_PRIMARY = "sensor_primary"  # Sensors first, vision backup
    PARALLEL_REDUNDANT = "parallel_redundant"  # Both active, most conservative wins
    SENSOR_FUSION = "sensor_fusion"  # Weighted combination of both


class SafetyPriority(Enum):
    """Safety priority levels"""
    NORMAL = "normal"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class ArbitrationDecision:
    """
    Result of arbitration process
    
    Attributes:
        command: Final avoidance command
        priority: Safety priority level
        source: Which system provided the command
        reason: Explanation of decision
        vision_active: Whether vision avoidance was active
        sensor_active: Whether sensor avoidance was active
    """
    command: Dict[str, Any]
    priority: SafetyPriority
    source: str
    reason: str
    vision_active: bool
    sensor_active: bool


class SafetyArbitrator:
    """
    Arbitrates between vision-based and sensor-based obstacle avoidance
    
    Features:
    - Multi-source input fusion
    - Configurable arbitration strategies
    - Priority-based decision making
    - Transparent reasoning
    - Health monitoring
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize safety arbitrator
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Arbitration mode
        mode_str = config.get('arbitration_mode', 'parallel_redundant')
        self.mode = ArbitrationMode(mode_str)
        
        # Weights for fusion mode
        self.vision_weight = config.get('vision_weight', 0.7)
        self.sensor_weight = config.get('sensor_weight', 0.3)
        
        # Emergency thresholds
        self.emergency_distance = config.get('emergency_distance', 1.0)  # meters
        self.critical_distance = config.get('critical_distance', 1.5)  # meters
        
        # Health monitoring
        self.vision_timeout = config.get('vision_timeout', 1.0)  # seconds
        self.sensor_timeout = config.get('sensor_timeout', 1.0)  # seconds
        
        # State
        self.last_vision_time = 0.0
        self.last_sensor_time = 0.0
        self.vision_healthy = True
        self.sensor_healthy = True
        
        self.logger.info(f"Safety Arbitrator initialized")
        self.logger.info(f"  Mode: {self.mode.value}")
        self.logger.info(f"  Vision weight: {self.vision_weight}")
        self.logger.info(f"  Sensor weight: {self.sensor_weight}")
    
    def arbitrate(
        self,
        vision_command: Optional[Dict[str, Any]],
        sensor_command: Optional[Dict[str, Any]],
        vision_healthy: bool = True,
        sensor_healthy: bool = True
    ) -> ArbitrationDecision:
        """
        Arbitrate between vision and sensor inputs
        
        Args:
            vision_command: Command from vision-based avoidance
            sensor_command: Command from proximity sensors
            vision_healthy: Vision system health status
            sensor_healthy: Sensor system health status
            
        Returns:
            Arbitration decision with final command
        """
        self.vision_healthy = vision_healthy
        self.sensor_healthy = sensor_healthy
        
        # Extract avoidance status
        vision_avoid = vision_command and vision_command.get('avoid', False)
        sensor_avoid = sensor_command and sensor_command.get('avoid', False)
        
        # Determine priority level
        priority = self._assess_priority(vision_command, sensor_command)
        
        # Apply arbitration strategy
        if self.mode == ArbitrationMode.VISION_PRIMARY:
            decision = self._vision_primary(vision_command, sensor_command, priority)
        
        elif self.mode == ArbitrationMode.SENSOR_PRIMARY:
            decision = self._sensor_primary(vision_command, sensor_command, priority)
        
        elif self.mode == ArbitrationMode.PARALLEL_REDUNDANT:
            decision = self._parallel_redundant(vision_command, sensor_command, priority)
        
        elif self.mode == ArbitrationMode.SENSOR_FUSION:
            decision = self._sensor_fusion(vision_command, sensor_command, priority)
        
        else:
            # Default to parallel redundant
            decision = self._parallel_redundant(vision_command, sensor_command, priority)
        
        # Log decision
        if decision.priority in [SafetyPriority.CRITICAL, SafetyPriority.EMERGENCY]:
            self.logger.warning(f"Arbitration: {decision.reason} (Priority: {decision.priority.value})")
        else:
            self.logger.debug(f"Arbitration: {decision.reason}")
        
        return decision
    
    def _assess_priority(
        self,
        vision_command: Optional[Dict],
        sensor_command: Optional[Dict]
    ) -> SafetyPriority:
        """Assess overall safety priority from both inputs"""
        
        # Check for emergency conditions (sensors override)
        if sensor_command and sensor_command.get('distance', float('inf')) < self.emergency_distance:
            return SafetyPriority.EMERGENCY
        
        # Check for critical conditions
        if sensor_command and sensor_command.get('distance', float('inf')) < self.critical_distance:
            return SafetyPriority.CRITICAL
        
        if vision_command and vision_command.get('clearance', float('inf')) < self.critical_distance:
            return SafetyPriority.CRITICAL
        
        # Check for warnings
        if sensor_command and sensor_command.get('avoid', False):
            return SafetyPriority.WARNING
        
        if vision_command and vision_command.get('avoid', False):
            if vision_command.get('clearance', float('inf')) < 2.0:
                return SafetyPriority.WARNING
            else:
                return SafetyPriority.CAUTION
        
        return SafetyPriority.NORMAL
    
    def _vision_primary(
        self,
        vision_command: Optional[Dict],
        sensor_command: Optional[Dict],
        priority: SafetyPriority
    ) -> ArbitrationDecision:
        """Vision is primary, sensors are backup"""
        
        # Emergency override: sensors always win
        if priority == SafetyPriority.EMERGENCY:
            return ArbitrationDecision(
                command=sensor_command or self._emergency_stop(),
                priority=priority,
                source="sensor_emergency",
                reason="Sensor detected emergency obstacle - hardware override",
                vision_active=False,
                sensor_active=True
            )
        
        # Vision available and healthy
        if vision_command and self.vision_healthy:
            return ArbitrationDecision(
                command=vision_command,
                priority=priority,
                source="vision",
                reason="Vision system active and healthy",
                vision_active=True,
                sensor_active=False
            )
        
        # Vision failed - fall back to sensors
        if sensor_command and self.sensor_healthy:
            return ArbitrationDecision(
                command=sensor_command,
                priority=priority,
                source="sensor_backup",
                reason="Vision unavailable - using sensor backup",
                vision_active=False,
                sensor_active=True
            )
        
        # Both failed - safe default
        return ArbitrationDecision(
            command={'avoid': False},
            priority=SafetyPriority.WARNING,
            source="failsafe",
            reason="Both systems unavailable - no avoidance active",
            vision_active=False,
            sensor_active=False
        )
    
    def _sensor_primary(
        self,
        vision_command: Optional[Dict],
        sensor_command: Optional[Dict],
        priority: SafetyPriority
    ) -> ArbitrationDecision:
        """Sensors are primary, vision is backup"""
        
        # Sensors available and healthy
        if sensor_command and self.sensor_healthy:
            return ArbitrationDecision(
                command=sensor_command,
                priority=priority,
                source="sensor",
                reason="Sensor system active and healthy",
                vision_active=False,
                sensor_active=True
            )
        
        # Sensors failed - fall back to vision
        if vision_command and self.vision_healthy:
            return ArbitrationDecision(
                command=vision_command,
                priority=priority,
                source="vision_backup",
                reason="Sensors unavailable - using vision backup",
                vision_active=True,
                sensor_active=False
            )
        
        # Both failed
        return ArbitrationDecision(
            command={'avoid': False},
            priority=SafetyPriority.WARNING,
            source="failsafe",
            reason="Both systems unavailable",
            vision_active=False,
            sensor_active=False
        )
    
    def _parallel_redundant(
        self,
        vision_command: Optional[Dict],
        sensor_command: Optional[Dict],
        priority: SafetyPriority
    ) -> ArbitrationDecision:
        """Both systems active - most conservative wins"""
        
        # Emergency: hardware sensors always override
        if priority == SafetyPriority.EMERGENCY:
            return ArbitrationDecision(
                command=sensor_command or self._emergency_stop(),
                priority=priority,
                source="sensor_emergency",
                reason="Emergency obstacle detected by sensors",
                vision_active=True,
                sensor_active=True
            )
        
        vision_avoid = vision_command and vision_command.get('avoid', False)
        sensor_avoid = sensor_command and sensor_command.get('avoid', False)
        
        # Both say avoid - use most conservative
        if vision_avoid and sensor_avoid:
            # Compare intensities
            vision_intensity = vision_command.get('intensity', 0.5)
            sensor_intensity = sensor_command.get('intensity', 0.5)
            
            if sensor_intensity >= vision_intensity:
                return ArbitrationDecision(
                    command=sensor_command,
                    priority=priority,
                    source="sensor_conservative",
                    reason="Both systems active - sensors more conservative",
                    vision_active=True,
                    sensor_active=True
                )
            else:
                return ArbitrationDecision(
                    command=vision_command,
                    priority=priority,
                    source="vision_conservative",
                    reason="Both systems active - vision more conservative",
                    vision_active=True,
                    sensor_active=True
                )
        
        # Only sensors say avoid
        elif sensor_avoid:
            return ArbitrationDecision(
                command=sensor_command,
                priority=priority,
                source="sensor_only",
                reason="Sensors detect obstacle - vision clear",
                vision_active=True,
                sensor_active=True
            )
        
        # Only vision says avoid
        elif vision_avoid:
            return ArbitrationDecision(
                command=vision_command,
                priority=priority,
                source="vision_only",
                reason="Vision detects obstacle - sensors clear",
                vision_active=True,
                sensor_active=True
            )
        
        # Neither says avoid
        else:
            return ArbitrationDecision(
                command={'avoid': False},
                priority=SafetyPriority.NORMAL,
                source="clear",
                reason="All systems clear - no obstacles",
                vision_active=True,
                sensor_active=True
            )
    
    def _sensor_fusion(
        self,
        vision_command: Optional[Dict],
        sensor_command: Optional[Dict],
        priority: SafetyPriority
    ) -> ArbitrationDecision:
        """Weighted combination of both inputs"""
        
        # Emergency override
        if priority == SafetyPriority.EMERGENCY:
            return ArbitrationDecision(
                command=sensor_command or self._emergency_stop(),
                priority=priority,
                source="emergency",
                reason="Emergency condition - sensor override",
                vision_active=True,
                sensor_active=True
            )
        
        # Both available - fuse commands
        if vision_command and sensor_command:
            fused_command = self._fuse_commands(vision_command, sensor_command)
            
            return ArbitrationDecision(
                command=fused_command,
                priority=priority,
                source="fused",
                reason=f"Fused vision ({self.vision_weight}) and sensors ({self.sensor_weight})",
                vision_active=True,
                sensor_active=True
            )
        
        # Only one available - use it
        elif vision_command:
            return ArbitrationDecision(
                command=vision_command,
                priority=priority,
                source="vision_only",
                reason="Sensors unavailable - vision only",
                vision_active=True,
                sensor_active=False
            )
        
        elif sensor_command:
            return ArbitrationDecision(
                command=sensor_command,
                priority=priority,
                source="sensor_only",
                reason="Vision unavailable - sensors only",
                vision_active=False,
                sensor_active=True
            )
        
        # Neither available
        else:
            return ArbitrationDecision(
                command={'avoid': False},
                priority=SafetyPriority.WARNING,
                source="failsafe",
                reason="No avoidance data available",
                vision_active=False,
                sensor_active=False
            )
    
    def _fuse_commands(self, vision_cmd: Dict, sensor_cmd: Dict) -> Dict:
        """Fuse two commands using weighted average"""
        fused = {
            'avoid': vision_cmd.get('avoid', False) or sensor_cmd.get('avoid', False)
        }
        
        # Fuse lateral command if present
        vision_lateral = vision_cmd.get('lateral', 0.0)
        sensor_lateral = sensor_cmd.get('right', 0.0)  # Convert to lateral
        
        fused['lateral'] = (
            vision_lateral * self.vision_weight +
            sensor_lateral * self.sensor_weight
        )
        
        # Fuse forward command
        vision_forward = vision_cmd.get('forward', 0.0)
        sensor_forward = sensor_cmd.get('forward', 0.0)
        
        fused['forward'] = (
            vision_forward * self.vision_weight +
            sensor_forward * self.sensor_weight
        )
        
        # Take minimum clearance (most conservative)
        vision_clearance = vision_cmd.get('clearance', float('inf'))
        sensor_distance = sensor_cmd.get('distance', float('inf'))
        fused['clearance'] = min(vision_clearance, sensor_distance)
        
        # Take maximum risk
        vision_risk = vision_cmd.get('risk', 'safe')
        sensor_risk = sensor_cmd.get('intensity', 0.0)
        
        risk_levels = ['safe', 'low', 'medium', 'high', 'critical']
        vision_risk_idx = risk_levels.index(vision_risk) if vision_risk in risk_levels else 0
        sensor_risk_idx = min(int(sensor_risk * 4), 4)  # Convert 0-1 to 0-4
        
        fused['risk'] = risk_levels[max(vision_risk_idx, sensor_risk_idx)]
        
        return fused
    
    def _emergency_stop(self) -> Dict:
        """Generate emergency stop command"""
        return {
            'avoid': True,
            'forward': 0.0,
            'lateral': 0.0,
            'emergency': True,
            'clearance': 0.0,
            'risk': 'emergency'
        }
