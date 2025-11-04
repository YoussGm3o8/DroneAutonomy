"""
Test HEARTBEAT Filtering Fix

This script verifies that the telemetry correctly filters HEARTBEAT messages
to only process those from the target vehicle, ignoring ground stations.
"""

import sys
import time
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from drone_autonomy.mavlink.telemetry import MAVLinkTelemetry

# Configure logging - use DEBUG to see filtering messages
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG to see ignored HEARTBEATs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_heartbeat_filtering():
    """Test that HEARTBEAT filtering prevents mode oscillation."""
    logger.info("=" * 70)
    logger.info("HEARTBEAT Filtering Test")
    logger.info("=" * 70)
    logger.info("")
    logger.info("This test verifies that mode oscillation is fixed.")
    logger.info("Set the mode to GUIDED in Mission Planner and it should stay stable.")
    logger.info("")
    
    # Create telemetry
    config = {
        'connection_string': 'udp:127.0.0.1:14550',
        'heartbeat_timeout': 10,
    }
    
    logger.info("Connecting to ArduPilot SITL...")
    telemetry = MAVLinkTelemetry(config)
    
    if not telemetry.connect():
        logger.error("❌ Failed to connect")
        return False
    
    logger.info("✓ Connected")
    logger.info(f"Target system ID: {telemetry.connection.target_system}")
    logger.info(f"Target component ID: {telemetry.connection.target_component}")
    logger.info("")
    
    # Read initial state
    data = telemetry.read_telemetry()
    logger.info(f"Initial state:")
    logger.info(f"  Armed:       {telemetry.armed}")
    logger.info(f"  Flight mode: {telemetry.flight_mode}")
    logger.info("")
    
    logger.info("=" * 70)
    logger.info("Monitoring for 30 seconds - Mode should NOT oscillate")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Instructions:")
    logger.info("  1. Set mode to GUIDED in Mission Planner")
    logger.info("  2. Mode should change once and stay stable")
    logger.info("  3. No rapid oscillation between GUIDED/STABILIZE")
    logger.info("")
    
    start_time = time.time()
    last_status_time = start_time
    mode_changes = []
    armed_changes = []
    
    try:
        while time.time() - start_time < 30:
            elapsed = time.time() - start_time
            
            # Read telemetry
            data = telemetry.read_telemetry()
            
            if data:
                # Check for changes
                if telemetry.armed_changed:
                    armed_status = "ARMED" if telemetry.armed else "DISARMED"
                    logger.info(f"[{elapsed:6.2f}s] 🔔 ARMED STATE CHANGED: {armed_status}")
                    armed_changes.append((elapsed, armed_status))
                    telemetry.clear_armed_changed()
                
                if telemetry.flight_mode_changed:
                    logger.info(f"[{elapsed:6.2f}s] 🔔 FLIGHT MODE CHANGED: {telemetry.flight_mode}")
                    mode_changes.append((elapsed, telemetry.flight_mode))
                    telemetry.clear_flight_mode_changed()
                
                # Periodic status
                if time.time() - last_status_time >= 5:
                    armed_str = "ARMED" if telemetry.armed else "DISARMED"
                    logger.info(f"[{elapsed:6.2f}s] Status: {armed_str} | Mode: {telemetry.flight_mode}")
                    last_status_time = time.time()
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Test interrupted by user")
    
    # Analysis
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test Results")
    logger.info("=" * 70)
    logger.info(f"Duration:         30 seconds")
    logger.info(f"Mode changes:     {len(mode_changes)}")
    logger.info(f"Armed changes:    {len(armed_changes)}")
    logger.info("")
    
    if mode_changes:
        logger.info("Mode Change History:")
        for elapsed, mode in mode_changes:
            logger.info(f"  [{elapsed:6.2f}s] {mode}")
        logger.info("")
    
    # Check for oscillation (more than 2-3 rapid changes)
    if len(mode_changes) > 3:
        rapid_changes = 0
        for i in range(1, len(mode_changes)):
            time_diff = mode_changes[i][0] - mode_changes[i-1][0]
            if time_diff < 2.0:  # Changes within 2 seconds
                rapid_changes += 1
        
        if rapid_changes > 2:
            logger.warning("⚠️  WARNING: Rapid mode oscillation detected!")
            logger.warning(f"   Found {rapid_changes} changes within 2 seconds")
            logger.warning("   HEARTBEAT filtering may not be working correctly")
            success = False
        else:
            logger.info("✅ PASS: No rapid oscillation detected")
            success = True
    elif len(mode_changes) == 0:
        logger.info("✅ PASS: Mode stable (no changes)")
        success = True
    else:
        logger.info("✅ PASS: Mode changes appear normal")
        success = True
    
    # Disconnect
    logger.info("")
    telemetry.disconnect()
    
    return success


def main():
    """Main test."""
    success = test_heartbeat_filtering()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
