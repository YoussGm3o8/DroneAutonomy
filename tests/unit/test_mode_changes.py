"""
Enhanced MAVLink Mode Change Test

Tests mode changes and verifies they are properly detected.
Includes detailed debugging output to diagnose mode change issues.
"""

import sys
import time
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from drone_autonomy.mavlink.telemetry import MAVLinkTelemetry

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG to see all details
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_mode_changes():
    """Test mode changes with detailed debugging."""
    logger.info("=" * 70)
    logger.info("Enhanced Mode Change Test")
    logger.info("=" * 70)
    logger.info("")
    
    # Create telemetry configuration
    config = {
        'connection_string': 'udp:127.0.0.1:14550',
        'heartbeat_timeout': 10,
    }
    
    logger.info("Creating telemetry instance...")
    telemetry = MAVLinkTelemetry(config)
    
    logger.info("Connecting to ArduPilot SITL...")
    if not telemetry.connect():
        logger.error("❌ Failed to connect")
        return False
    
    logger.info("✓ Connected")
    logger.info("")
    
    # Read initial state
    logger.info("Reading initial telemetry...")
    data = telemetry.read_telemetry()
    
    logger.info(f"Initial state:")
    logger.info(f"  Armed:       {telemetry.armed}")
    logger.info(f"  Flight mode: {telemetry.flight_mode}")
    logger.info("")
    
    # Test sequence of mode changes
    modes_to_test = ["GUIDED", "LOITER", "ALT_HOLD", "STABILIZE"]
    
    logger.info("=" * 70)
    logger.info("Testing Mode Changes")
    logger.info("=" * 70)
    logger.info("")
    
    for target_mode in modes_to_test:
        logger.info("-" * 70)
        logger.info(f"TEST: Changing mode to {target_mode}")
        logger.info("-" * 70)
        
        # Clear any previous change flags
        telemetry.clear_flight_mode_changed()
        
        # Send mode change command
        logger.info(f"Sending mode change command: {target_mode}")
        success = telemetry.set_mode(target_mode)
        
        if not success:
            logger.error(f"❌ Failed to send mode change command")
            continue
        
        logger.info(f"✓ Command sent")
        logger.info(f"Waiting for mode change confirmation...")
        
        # Wait up to 5 seconds for mode change
        start_time = time.time()
        timeout = 5.0
        mode_changed = False
        
        while time.time() - start_time < timeout:
            # Read telemetry (processes MAVLink messages)
            data = telemetry.read_telemetry()
            
            # Check current mode
            current_mode = telemetry.flight_mode
            
            # Check if mode changed
            if telemetry.flight_mode_changed:
                logger.info(f"✅ MODE CHANGED: {current_mode}")
                mode_changed = True
                telemetry.clear_flight_mode_changed()
                
                # Check if it's the mode we requested
                if current_mode == target_mode:
                    logger.info(f"✅ Successfully changed to {target_mode}")
                else:
                    logger.warning(f"⚠️  Mode changed but not to target!")
                    logger.warning(f"   Expected: {target_mode}")
                    logger.warning(f"   Got:      {current_mode}")
                break
            
            # Show current state every 0.5 seconds
            elapsed = time.time() - start_time
            if int(elapsed * 2) != int((elapsed - 0.1) * 2):  # Every 0.5s
                logger.info(f"  [{elapsed:.1f}s] Current mode: {current_mode} (waiting for {target_mode})")
            
            time.sleep(0.1)
        
        if not mode_changed:
            logger.error(f"❌ TIMEOUT: Mode did not change after {timeout}s")
            logger.error(f"   Current mode: {telemetry.flight_mode}")
            logger.error(f"   Target mode:  {target_mode}")
            logger.error("")
            logger.error("Possible causes:")
            logger.error("  1. Vehicle may have pre-arm checks preventing mode change")
            logger.error("  2. Command acknowledgment may have failed")
            logger.error("  3. HEARTBEAT messages not being received")
            logger.error("  4. Mode not available in current vehicle state")
        
        logger.info("")
        
        # Wait a bit before next test
        time.sleep(2)
    
    # Disconnect
    logger.info("")
    logger.info("Disconnecting...")
    telemetry.disconnect()
    
    return True


def test_raw_heartbeat_monitoring():
    """Monitor raw HEARTBEAT messages to debug mode detection."""
    logger.info("=" * 70)
    logger.info("Raw HEARTBEAT Monitoring Test")
    logger.info("=" * 70)
    logger.info("")
    logger.info("This test monitors raw HEARTBEAT messages directly")
    logger.info("Change modes manually in MAVProxy/GCS to see raw data")
    logger.info("")
    
    from pymavlink import mavutil
    
    logger.info("Connecting...")
    conn = mavutil.mavlink_connection('udp:127.0.0.1:14550', timeout=10)
    
    logger.info("Waiting for heartbeat...")
    msg = conn.wait_heartbeat(timeout=10)
    
    if not msg:
        logger.error("❌ No heartbeat received")
        return False
    
    logger.info("✓ Heartbeat received")
    logger.info("")
    logger.info("Monitoring HEARTBEATs for 30 seconds...")
    logger.info("Change modes manually to see updates")
    logger.info("")
    
    # ArduPilot Copter modes
    copter_modes = {
        0: "STABILIZE", 1: "ACRO", 2: "ALT_HOLD", 3: "AUTO",
        4: "GUIDED", 5: "LOITER", 6: "RTL", 7: "CIRCLE",
        9: "LAND", 11: "DRIFT", 13: "SPORT", 14: "FLIP",
        15: "AUTOTUNE", 16: "POSHOLD", 17: "BRAKE"
    }
    
    last_mode = None
    last_armed = None
    start_time = time.time()
    heartbeat_count = 0
    
    try:
        while time.time() - start_time < 30:
            msg = conn.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
            
            if msg:
                heartbeat_count += 1
                
                # Decode mode
                mode_id = msg.custom_mode
                mode_name = copter_modes.get(mode_id, f"UNKNOWN({mode_id})")
                armed = bool(msg.base_mode & 128)
                
                # Log if changed
                if mode_name != last_mode or armed != last_armed:
                    elapsed = time.time() - start_time
                    armed_str = "ARMED" if armed else "DISARMED"
                    
                    logger.info(f"[{elapsed:5.1f}s] HEARTBEAT #{heartbeat_count}")
                    logger.info(f"          Mode:        {mode_name} (custom_mode={mode_id})")
                    logger.info(f"          Armed:       {armed_str} (base_mode={msg.base_mode})")
                    logger.info(f"          Type:        {msg.type}")
                    logger.info(f"          Autopilot:   {msg.autopilot}")
                    logger.info("")
                    
                    last_mode = mode_name
                    last_armed = armed
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    
    logger.info("")
    logger.info(f"Received {heartbeat_count} heartbeats in 30 seconds")
    logger.info("")
    
    conn.close()
    return True


def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test MAVLink mode changes')
    parser.add_argument('--raw', action='store_true',
                       help='Monitor raw HEARTBEAT messages')
    
    args = parser.parse_args()
    
    if args.raw:
        test_raw_heartbeat_monitoring()
    else:
        test_mode_changes()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
