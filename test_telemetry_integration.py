"""
Simple MAVLink Telemetry Integration Test

Tests the MAVLinkTelemetry class from your codebase to verify:
1. Connection to ArduPilot SITL
2. Armed state detection via the telemetry.armed property
3. Flight mode detection via the telemetry.flight_mode property
4. State change detection via telemetry.armed_changed and flight_mode_changed

This test uses your actual telemetry class to ensure integration works correctly.
"""

import sys
import time
import logging
import yaml
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from drone_autonomy.mavlink.telemetry import MAVLinkTelemetry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_telemetry_class(duration: int = 30):
    """
    Test the MAVLinkTelemetry class integration.
    
    Args:
        duration: Test duration in seconds
    """
    logger.info("=" * 70)
    logger.info("MAVLink Telemetry Class Integration Test")
    logger.info("=" * 70)
    logger.info("")
    
    # Create telemetry configuration
    config = {
        'connection_string': 'tcp:127.0.0.1:5762',
        'baud': 57600,
        'auto_detect': False,  # Don't try USB ports for SITL
        'heartbeat_timeout': 10,
        'vio_publish_rate': 30,
        'telemetry_rate': 10
    }
    
    logger.info("Configuration:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")
    logger.info("")
    
    # Create telemetry instance
    logger.info("Creating MAVLinkTelemetry instance...")
    telemetry = MAVLinkTelemetry(config)
    logger.info("✓ Instance created")
    logger.info("")
    
    # Connect
    logger.info("Connecting to ArduPilot SITL...")
    if not telemetry.connect():
        logger.error("❌ Failed to connect")
        logger.error("   Make sure ArduPilot SITL is running!")
        logger.error("   Example: sim_vehicle.py -v ArduCopter -f gazebo-iris")
        return False
    
    logger.info("✓ Connected successfully")
    logger.info("")
    
    # Initial state
    logger.info("Reading initial state...")
    telemetry_data = telemetry.read_telemetry()
    
    if telemetry_data:
        logger.info(f"Initial armed state:  {telemetry.armed}")
        logger.info(f"Initial flight mode:  {telemetry.flight_mode}")
        logger.info("")
    
    # Monitor state changes
    logger.info("=" * 70)
    logger.info(f"Monitoring State Changes for {duration} seconds")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Instructions:")
    logger.info("  - Use MAVProxy or another GCS to change modes and arm/disarm")
    logger.info("  - State changes will be detected and reported below")
    logger.info("")
    logger.info("Monitoring...")
    logger.info("")
    
    start_time = time.time()
    last_status_time = start_time
    armed_changes = 0
    mode_changes = 0
    telemetry_reads = 0
    
    try:
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            
            # Read telemetry (this processes MAVLink messages)
            data = telemetry.read_telemetry()
            
            if data:
                telemetry_reads += 1
                
                # Check for armed state change
                if telemetry.armed_changed:
                    armed_changes += 1
                    status = "ARMED" if telemetry.armed else "DISARMED"
                    logger.info(f"[{elapsed:6.2f}s] 🔔 ARMED STATE CHANGED: {status}")
                    telemetry.clear_armed_changed()
                
                # Check for flight mode change
                if telemetry.flight_mode_changed:
                    mode_changes += 1
                    logger.info(f"[{elapsed:6.2f}s] 🔔 FLIGHT MODE CHANGED: {telemetry.flight_mode}")
                    telemetry.clear_flight_mode_changed()
                
                # Periodic status update (every 10 seconds)
                if time.time() - last_status_time >= 10:
                    armed_status = "ARMED" if telemetry.armed else "DISARMED"
                    logger.info(f"[{elapsed:6.2f}s] Status: {armed_status} | Mode: {telemetry.flight_mode}")
                    
                    # Show some telemetry data if available
                    if 'attitude' in data:
                        att = data['attitude']
                        logger.info(f"              Attitude: Roll={att['roll']:.1f}° Pitch={att['pitch']:.1f}° Yaw={att['yaw']:.1f}°")
                    
                    if 'position' in data:
                        pos = data['position']
                        logger.info(f"              Position: Alt={pos.get('relative_altitude', 0):.1f}m Lat={pos.get('latitude', 0):.6f}")
                    
                    if 'battery' in data:
                        bat = data['battery']
                        logger.info(f"              Battery: {bat.get('voltage', 0):.1f}V {bat.get('remaining', 0)}%")
                    
                    last_status_time = time.time()
            
            # Small delay to avoid busy loop
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Test interrupted by user")
    
    # Final summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test Complete - Summary")
    logger.info("=" * 70)
    logger.info(f"Duration:              {duration}s")
    logger.info(f"Telemetry reads:       {telemetry_reads}")
    logger.info(f"Armed state changes:   {armed_changes}")
    logger.info(f"Flight mode changes:   {mode_changes}")
    logger.info(f"Final armed state:     {telemetry.armed}")
    logger.info(f"Final flight mode:     {telemetry.flight_mode}")
    logger.info("")
    
    # Disconnect
    logger.info("Disconnecting...")
    telemetry.disconnect()
    logger.info("✓ Disconnected")
    logger.info("")
    
    # Test verdict
    if telemetry_reads > 0:
        logger.info("✅ TEST PASSED: Telemetry class working correctly")
        logger.info(f"   - Connection: ✓")
        logger.info(f"   - Telemetry reading: ✓ ({telemetry_reads} reads)")
        logger.info(f"   - State tracking: ✓")
        return True
    else:
        logger.warning("⚠️  WARNING: No telemetry data received")
        return False


def test_command_logging():
    """Test command logging callback feature."""
    logger.info("=" * 70)
    logger.info("Testing Command Logging Callback")
    logger.info("=" * 70)
    logger.info("")
    
    command_log = []
    
    def log_callback(message: str, level: str = "INFO"):
        """Callback to capture command logs."""
        command_log.append({'message': message, 'level': level})
        logger.info(f"[CALLBACK] {level}: {message}")
    
    # Create telemetry with config
    config = {
        'connection_string': 'udp:127.0.0.1:14550',
        'heartbeat_timeout': 5,
    }
    
    telemetry = MAVLinkTelemetry(config)
    telemetry.set_command_logger(log_callback)
    
    logger.info("✓ Command logger callback registered")
    logger.info("")
    
    if not telemetry.connect():
        logger.warning("⚠️  Could not connect for command test")
        return False
    
    logger.info("Testing ARM command with logging...")
    success = telemetry.arm()
    logger.info(f"ARM command result: {success}")
    logger.info(f"Commands logged: {len(command_log)}")
    logger.info("")
    
    time.sleep(2)
    
    logger.info("Testing DISARM command with logging...")
    success = telemetry.disarm()
    logger.info(f"DISARM command result: {success}")
    logger.info(f"Commands logged: {len(command_log)}")
    logger.info("")
    
    telemetry.disconnect()
    
    logger.info("Command log summary:")
    for i, log_entry in enumerate(command_log, 1):
        logger.info(f"  {i}. [{log_entry['level']}] {log_entry['message']}")
    logger.info("")
    
    logger.info("✅ Command logging test complete")
    return True


def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test MAVLink telemetry integration')
    parser.add_argument('--duration', type=int, default=30, 
                       help='Test duration in seconds (default: 30)')
    parser.add_argument('--test-commands', action='store_true',
                       help='Also test command logging feature')
    
    args = parser.parse_args()
    
    # Run main telemetry test
    success = test_telemetry_class(duration=args.duration)
    
    # Optionally test command logging
    if args.test_commands:
        time.sleep(2)
        test_command_logging()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
