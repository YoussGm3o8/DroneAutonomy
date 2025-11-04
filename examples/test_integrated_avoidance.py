"""
Example: Integrated Avoidance System with Vision + Sensors

Demonstrates how to use both Tesla-style vision avoidance and ArduPilot
proximity sensors together with safety arbitration.
"""

import cv2
import numpy as np
import yaml
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from drone_autonomy.navigation import ObstacleAvoider
from drone_autonomy.mavlink.proximity import ProximityMonitor
from drone_autonomy.fusion.safety_arbitrator import SafetyArbitrator, ArbitrationMode

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration"""
    config_file = Path(__file__).parent.parent / 'config' / 'default_config.yaml'
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config


def simulate_vision_avoidance(frame, depth_map):
    """Simulate vision-based avoidance command"""
    # In real system, this would be:
    # avoider.detect_obstacles(depth_map)
    # avoider.generate_path_candidates(frame.shape, target)
    # command = avoider.get_avoidance_command()
    
    # Simulate obstacle detected by vision
    vision_command = {
        'avoid': True,
        'lateral': -0.3,  # Move left
        'forward': 0.5,
        'clearance': 1.8,  # meters
        'risk': 'medium'
    }
    
    return vision_command


def simulate_sensor_avoidance(telemetry):
    """Simulate sensor-based avoidance command"""
    # In real system, this would be:
    # proximity.update()
    # command = proximity.get_avoidance_command()
    
    # Simulate obstacle detected by forward sensor
    sensor_command = {
        'avoid': True,
        'forward': -0.5,  # Back up
        'right': 0.0,
        'distance': 1.2,  # meters
        'intensity': 0.8,
        'obstacle_direction': 'forward'
    }
    
    return sensor_command


def demo_vision_primary():
    """Demo: Vision primary mode"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 1: Vision Primary Mode")
    logger.info("="*60)
    
    config = {
        'arbitration_mode': 'vision_primary',
        'vision_weight': 0.7,
        'sensor_weight': 0.3,
        'emergency_distance': 1.0
    }
    
    arbitrator = SafetyArbitrator(config, logger)
    
    # Scenario: Both systems detect obstacle
    vision_cmd = {
        'avoid': True,
        'lateral': -0.3,
        'clearance': 2.0,
        'risk': 'low'
    }
    
    sensor_cmd = {
        'avoid': True,
        'forward': -0.3,
        'distance': 2.5,
        'intensity': 0.5
    }
    
    decision = arbitrator.arbitrate(vision_cmd, sensor_cmd)
    
    logger.info(f"Decision: {decision.source}")
    logger.info(f"  Reason: {decision.reason}")
    logger.info(f"  Priority: {decision.priority.value}")
    logger.info(f"  Command: {decision.command}")


def demo_parallel_redundant():
    """Demo: Parallel redundant mode"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 2: Parallel Redundant Mode (RECOMMENDED)")
    logger.info("="*60)
    
    config = {
        'arbitration_mode': 'parallel_redundant',
        'emergency_distance': 1.0,
        'critical_distance': 1.5
    }
    
    arbitrator = SafetyArbitrator(config, logger)
    
    # Scenario 1: Vision clear, sensor detects
    logger.info("\nScenario 1: Vision clear, sensor detects obstacle")
    vision_cmd = {'avoid': False}
    sensor_cmd = {
        'avoid': True,
        'forward': -0.5,
        'distance': 1.8,
        'intensity': 0.6
    }
    
    decision = arbitrator.arbitrate(vision_cmd, sensor_cmd)
    logger.info(f"  Decision: {decision.source} - {decision.reason}")
    logger.info(f"  Command: {decision.command}")
    
    # Scenario 2: Both detect, sensor more conservative
    logger.info("\nScenario 2: Both detect, sensor more conservative")
    vision_cmd = {
        'avoid': True,
        'lateral': -0.3,
        'intensity': 0.4,
        'clearance': 2.0
    }
    sensor_cmd = {
        'avoid': True,
        'forward': -0.7,
        'distance': 1.2,
        'intensity': 0.9
    }
    
    decision = arbitrator.arbitrate(vision_cmd, sensor_cmd)
    logger.info(f"  Decision: {decision.source} - {decision.reason}")
    logger.info(f"  Priority: {decision.priority.value}")
    
    # Scenario 3: Emergency override
    logger.info("\nScenario 3: Emergency condition (< 1.0m)")
    vision_cmd = {
        'avoid': True,
        'lateral': -0.2,
        'clearance': 1.5
    }
    sensor_cmd = {
        'avoid': True,
        'forward': -1.0,
        'distance': 0.8,  # Emergency!
        'intensity': 1.0
    }
    
    decision = arbitrator.arbitrate(vision_cmd, sensor_cmd)
    logger.info(f"  Decision: {decision.source} - {decision.reason}")
    logger.info(f"  Priority: {decision.priority.value} ⚠️")


def demo_sensor_fusion():
    """Demo: Sensor fusion mode"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 3: Sensor Fusion Mode")
    logger.info("="*60)
    
    config = {
        'arbitration_mode': 'sensor_fusion',
        'vision_weight': 0.7,
        'sensor_weight': 0.3,
        'emergency_distance': 1.0
    }
    
    arbitrator = SafetyArbitrator(config, logger)
    
    # Both systems active with different recommendations
    vision_cmd = {
        'avoid': True,
        'lateral': -0.4,  # Go left
        'forward': 0.3,
        'clearance': 1.8,
        'risk': 'medium'
    }
    
    sensor_cmd = {
        'avoid': True,
        'right': 0.2,  # Go right
        'forward': 0.5,
        'distance': 2.0,
        'intensity': 0.5
    }
    
    decision = arbitrator.arbitrate(vision_cmd, sensor_cmd)
    
    logger.info(f"Decision: {decision.source}")
    logger.info(f"  Vision command: lateral={vision_cmd['lateral']}, forward={vision_cmd['forward']}")
    logger.info(f"  Sensor command: right={sensor_cmd['right']}, forward={sensor_cmd['forward']}")
    logger.info(f"  Fused command: lateral={decision.command.get('lateral', 0):.2f}, "
               f"forward={decision.command.get('forward', 0):.2f}")
    logger.info(f"  Weights: Vision={config['vision_weight']}, Sensor={config['sensor_weight']}")


def demo_failsafe_scenarios():
    """Demo: System failure scenarios"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 4: Failsafe Scenarios")
    logger.info("="*60)
    
    config = {
        'arbitration_mode': 'parallel_redundant',
        'emergency_distance': 1.0
    }
    
    arbitrator = SafetyArbitrator(config, logger)
    
    # Scenario 1: Vision fails, sensors active
    logger.info("\nScenario 1: Vision system failure")
    vision_cmd = None  # Vision system down
    sensor_cmd = {
        'avoid': True,
        'forward': -0.5,
        'distance': 1.5
    }
    
    decision = arbitrator.arbitrate(vision_cmd, sensor_cmd, vision_healthy=False)
    logger.info(f"  Decision: {decision.source} - {decision.reason}")
    logger.info(f"  Vision active: {decision.vision_active}, Sensor active: {decision.sensor_active}")
    
    # Scenario 2: Sensors fail, vision active
    logger.info("\nScenario 2: Sensor system failure")
    vision_cmd = {
        'avoid': True,
        'lateral': -0.3,
        'clearance': 1.8
    }
    sensor_cmd = None  # Sensors down
    
    decision = arbitrator.arbitrate(vision_cmd, sensor_cmd, sensor_healthy=False)
    logger.info(f"  Decision: {decision.source} - {decision.reason}")
    logger.info(f"  Vision active: {decision.vision_active}, Sensor active: {decision.sensor_active}")
    
    # Scenario 3: Both systems fail
    logger.info("\nScenario 3: Both systems failure (Catastrophic)")
    vision_cmd = None
    sensor_cmd = None
    
    decision = arbitrator.arbitrate(
        vision_cmd, sensor_cmd,
        vision_healthy=False, sensor_healthy=False
    )
    logger.info(f"  Decision: {decision.source} - {decision.reason}")
    logger.info(f"  Priority: {decision.priority.value} ⚠️")


def demo_real_integration():
    """Demo: How to integrate in real code"""
    logger.info("\n" + "="*60)
    logger.info("DEMO 5: Real Integration Example")
    logger.info("="*60)
    
    logger.info("\nExample code for real integration:")
    
    code = '''
# In your main autonomous controller:

class AutonomousController:
    def __init__(self, config, telemetry, logger):
        # Initialize vision avoidance
        self.obstacle_avoider = ObstacleAvoider(
            config['obstacle_avoidance'], 
            logger
        )
        
        # Initialize proximity monitor (if enabled)
        if config.get('proximity', {}).get('enabled', False):
            self.proximity_monitor = ProximityMonitor(
                telemetry, 
                config['proximity'], 
                logger
            )
        else:
            self.proximity_monitor = None
        
        # Initialize safety arbitrator (if enabled)
        if config.get('safety_arbitration', {}).get('enabled', False):
            self.arbitrator = SafetyArbitrator(
                config['safety_arbitration'],
                logger
            )
        else:
            self.arbitrator = None
    
    def update(self, frame, depth_map, target_detection):
        # Vision-based avoidance
        obstacles = self.obstacle_avoider.detect_obstacles(depth_map)
        self.obstacle_avoider.generate_path_candidates(
            frame.shape, 
            target_detection.get('center') if target_detection else None
        )
        vision_command = self.obstacle_avoider.get_avoidance_command()
        
        # Sensor-based avoidance (if available)
        sensor_command = None
        if self.proximity_monitor:
            self.proximity_monitor.update()
            sensor_command = self.proximity_monitor.get_avoidance_command()
        
        # Arbitrate if both systems active
        if self.arbitrator and sensor_command:
            decision = self.arbitrator.arbitrate(
                vision_command,
                sensor_command,
                vision_healthy=True,
                sensor_healthy=self.proximity_monitor.get_sensor_health()
            )
            
            final_command = decision.command
            logger.info(f"Arbitration: {decision.reason}")
        else:
            # Vision only
            final_command = vision_command
        
        return final_command
'''
    
    print(code)


def main():
    """Run all demos"""
    logger.info("="*60)
    logger.info("Integrated Avoidance System Demonstration")
    logger.info("Vision (Tesla-Style) + Sensors (ArduPilot) + Arbitration")
    logger.info("="*60)
    
    try:
        demo_vision_primary()
        demo_parallel_redundant()
        demo_sensor_fusion()
        demo_failsafe_scenarios()
        demo_real_integration()
        
        logger.info("\n" + "="*60)
        logger.info("All demos completed successfully!")
        logger.info("="*60)
        
        logger.info("\nRecommendations:")
        logger.info("  1. Use PARALLEL_REDUNDANT mode for best safety")
        logger.info("  2. Install TFmini-S lidar for hardware backup ($40)")
        logger.info("  3. Enable arbitration in config when sensors ready")
        logger.info("  4. Test both systems independently before fusion")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)


if __name__ == '__main__':
    main()
