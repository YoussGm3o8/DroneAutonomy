"""
MAVLink Connection Test Script

Tests the MAVLink connection to verify:
1. Connection establishment with ArduPilot SITL
2. Heartbeat reception
3. Arm/Disarm state detection and changes
4. Flight mode detection and changes
5. Telemetry data reception

Usage:
    python test_mavlink_connection.py [connection_string]

Example:
    python test_mavlink_connection.py
    python test_mavlink_connection.py udp:127.0.0.1:14550
    python test_mavlink_connection.py tcp:127.0.0.1:5762
"""

import sys
import time
import logging
from typing import Optional
from pymavlink import mavutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class MAVLinkConnectionTest:
    """Test MAVLink connection and state detection."""
    
    # ArduPilot Copter flight modes
    COPTER_MODES = {
        0: "STABILIZE",
        1: "ACRO",
        2: "ALT_HOLD",
        3: "AUTO",
        4: "GUIDED",
        5: "LOITER",
        6: "RTL",
        7: "CIRCLE",
        9: "LAND",
        11: "DRIFT",
        13: "SPORT",
        14: "FLIP",
        15: "AUTOTUNE",
        16: "POSHOLD",
        17: "BRAKE",
        18: "THROW",
        19: "AVOID_ADSB",
        20: "GUIDED_NOGPS",
        21: "SMART_RTL",
        22: "FLOWHOLD",
        23: "FOLLOW",
        24: "ZIGZAG",
        25: "SYSTEMID",
        26: "AUTOROTATE",
        27: "AUTO_RTL"
    }
    
    # MAVLink mode flags
    MAV_MODE_FLAG_SAFETY_ARMED = 128  # 0x80
    
    def __init__(self, connection_string: str = 'udp:127.0.0.1:14550'):
        """Initialize test with connection string."""
        self.connection_string = connection_string
        self.connection: Optional[mavutil.mavlink_connection] = None
        self.armed = False
        self.flight_mode = "UNKNOWN"
        self.armed_count = 0
        self.disarmed_count = 0
        self.mode_changes = []
        
    def decode_flight_mode(self, base_mode: int, custom_mode: int) -> str:
        """Decode flight mode from HEARTBEAT message."""
        return self.COPTER_MODES.get(custom_mode, f"UNKNOWN({custom_mode})")
    
    def connect(self, timeout: int = 10) -> bool:
        """
        Connect to MAVLink vehicle.
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            True if connected successfully
        """
        logger.info("=" * 70)
        logger.info("MAVLink Connection Test")
        logger.info("=" * 70)
        logger.info(f"Connection string: {self.connection_string}")
        logger.info(f"Timeout: {timeout}s")
        logger.info("")
        
        try:
            logger.info("Creating MAVLink connection...")
            self.connection = mavutil.mavlink_connection(
                self.connection_string,
                timeout=timeout
            )
            
            if self.connection is None:
                logger.error("❌ Failed to create connection object")
                return False
            
            logger.info("✓ Connection object created")
            logger.info(f"Waiting for heartbeat (timeout: {timeout}s)...")
            
            # Wait for heartbeat
            msg = self.connection.wait_heartbeat(timeout=timeout)
            
            if msg is None:
                logger.error(f"❌ No heartbeat received within {timeout}s")
                logger.error("   Make sure ArduPilot SITL is running!")
                return False
            
            logger.info("✓ Heartbeat received!")
            logger.info("")
            logger.info("Connection Details:")
            logger.info(f"  - System ID:     {self.connection.target_system}")
            logger.info(f"  - Component ID:  {self.connection.target_component}")
            logger.info(f"  - Type:          {msg.type} (MAV_TYPE)")
            logger.info(f"  - Autopilot:     {msg.autopilot}")
            logger.info("")
            
            # Decode initial state from heartbeat
            self.armed = bool(msg.base_mode & self.MAV_MODE_FLAG_SAFETY_ARMED)
            self.flight_mode = self.decode_flight_mode(msg.base_mode, msg.custom_mode)
            
            armed_status = "ARMED" if self.armed else "DISARMED"
            logger.info(f"Initial State:")
            logger.info(f"  - Armed:        {armed_status}")
            logger.info(f"  - Flight Mode:  {self.flight_mode}")
            logger.info(f"  - Base Mode:    {msg.base_mode} (0x{msg.base_mode:02X})")
            logger.info(f"  - Custom Mode:  {msg.custom_mode}")
            logger.info("")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    def request_data_streams(self):
        """Request telemetry data streams from autopilot."""
        if not self.connection:
            return
        
        logger.info("Requesting data streams...")
        
        try:
            # Request data streams at 4 Hz
            streams_to_request = [
                (mavutil.mavlink.MAV_DATA_STREAM_ALL, 4),
                (mavutil.mavlink.MAV_DATA_STREAM_POSITION, 4),
                (mavutil.mavlink.MAV_DATA_STREAM_EXTRA1, 4),
                (mavutil.mavlink.MAV_DATA_STREAM_EXTRA2, 4),
            ]
            
            for stream_id, rate in streams_to_request:
                self.connection.mav.request_data_stream_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    stream_id,
                    rate,
                    1  # Start sending
                )
            
            logger.info("✓ Data stream requests sent")
            logger.info("")
            
        except Exception as e:
            logger.warning(f"⚠ Failed to request data streams: {e}")
    
    def test_arm_command(self):
        """Test sending ARM command."""
        if not self.connection:
            return
        
        logger.info("Testing ARM command...")
        
        try:
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,  # confirmation
                1,  # param1: 1 to arm
                0, 0, 0, 0, 0, 0  # other params unused
            )
            logger.info("✓ ARM command sent")
            
        except Exception as e:
            logger.error(f"❌ Failed to send ARM command: {e}")
    
    def test_disarm_command(self):
        """Test sending DISARM command."""
        if not self.connection:
            return
        
        logger.info("Testing DISARM command...")
        
        try:
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,  # confirmation
                0,  # param1: 0 to disarm
                0, 0, 0, 0, 0, 0  # other params unused
            )
            logger.info("✓ DISARM command sent")
            
        except Exception as e:
            logger.error(f"❌ Failed to send DISARM command: {e}")
    
    def test_mode_change(self, mode_name: str):
        """Test changing flight mode."""
        if not self.connection:
            return
        
        # Find mode number
        mode_number = None
        for num, name in self.COPTER_MODES.items():
            if name == mode_name:
                mode_number = num
                break
        
        if mode_number is None:
            logger.error(f"❌ Unknown mode: {mode_name}")
            return
        
        logger.info(f"Testing mode change to {mode_name}...")
        
        try:
            self.connection.mav.set_mode_send(
                self.connection.target_system,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                mode_number
            )
            logger.info(f"✓ Mode change command sent ({mode_name})")
            
        except Exception as e:
            logger.error(f"❌ Failed to send mode change: {e}")
    
    def monitor_state_changes(self, duration: int = 30):
        """
        Monitor arm state and flight mode changes.
        
        Args:
            duration: Monitoring duration in seconds
        """
        if not self.connection:
            return
        
        logger.info("=" * 70)
        logger.info(f"Monitoring State Changes for {duration} seconds")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Instructions:")
        logger.info("  - Use MAVProxy or another GCS to change modes and arm/disarm")
        logger.info("  - Or wait for automated test commands")
        logger.info("")
        
        start_time = time.time()
        heartbeat_count = 0
        last_heartbeat_time = start_time
        message_counts = {}
        
        # Track state
        previous_armed = self.armed
        previous_mode = self.flight_mode
        
        try:
            while time.time() - start_time < duration:
                elapsed = time.time() - start_time
                
                # Receive message (non-blocking)
                msg = self.connection.recv_match(blocking=False, timeout=0.1)
                
                if msg is None:
                    time.sleep(0.01)
                    continue
                
                msg_type = msg.get_type()
                
                # Count message types
                message_counts[msg_type] = message_counts.get(msg_type, 0) + 1
                
                # Process HEARTBEAT for state changes
                if msg_type == 'HEARTBEAT':
                    heartbeat_count += 1
                    last_heartbeat_time = time.time()
                    
                    # Check armed state
                    new_armed = bool(msg.base_mode & self.MAV_MODE_FLAG_SAFETY_ARMED)
                    if new_armed != previous_armed:
                        action = "ARMED" if new_armed else "DISARMED"
                        logger.info(f"[{elapsed:6.2f}s] 🔔 ARMED STATE CHANGED: {action}")
                        
                        if new_armed:
                            self.armed_count += 1
                        else:
                            self.disarmed_count += 1
                        
                        previous_armed = new_armed
                        self.armed = new_armed
                    
                    # Check flight mode
                    new_mode = self.decode_flight_mode(msg.base_mode, msg.custom_mode)
                    if new_mode != previous_mode:
                        logger.info(f"[{elapsed:6.2f}s] 🔔 MODE CHANGED: {previous_mode} → {new_mode}")
                        self.mode_changes.append({
                            'time': elapsed,
                            'from': previous_mode,
                            'to': new_mode
                        })
                        previous_mode = new_mode
                        self.flight_mode = new_mode
                
                # Log important messages
                elif msg_type == 'COMMAND_ACK':
                    command = msg.command
                    result = msg.result
                    result_text = "SUCCESS" if result == 0 else f"FAILED({result})"
                    logger.info(f"[{elapsed:6.2f}s] 📋 Command ACK: {command} - {result_text}")
                
                elif msg_type == 'STATUSTEXT':
                    severity = msg.severity
                    text = msg.text
                    logger.info(f"[{elapsed:6.2f}s] 💬 Status: [{severity}] {text}")
                
                # Show periodic status
                if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                    if int(elapsed) % 10 == int(time.time() - start_time) % 10:
                        armed_status = "ARMED" if self.armed else "DISARMED"
                        logger.info(f"[{elapsed:6.2f}s] Status: {armed_status} | Mode: {self.flight_mode} | Heartbeats: {heartbeat_count}")
        
        except KeyboardInterrupt:
            logger.info("")
            logger.info("Monitoring interrupted by user")
        
        # Check heartbeat health
        time_since_heartbeat = time.time() - last_heartbeat_time
        logger.info("")
        logger.info("=" * 70)
        logger.info("Monitoring Complete - Summary")
        logger.info("=" * 70)
        logger.info(f"Duration:              {duration}s")
        logger.info(f"Heartbeats received:   {heartbeat_count}")
        logger.info(f"Last heartbeat:        {time_since_heartbeat:.1f}s ago")
        logger.info(f"Armed events:          {self.armed_count}")
        logger.info(f"Disarmed events:       {self.disarmed_count}")
        logger.info(f"Mode changes:          {len(self.mode_changes)}")
        logger.info(f"Final state:           {'ARMED' if self.armed else 'DISARMED'} | {self.flight_mode}")
        logger.info("")
        
        if self.mode_changes:
            logger.info("Mode Change History:")
            for change in self.mode_changes:
                logger.info(f"  [{change['time']:6.2f}s] {change['from']} → {change['to']}")
            logger.info("")
        
        logger.info("Message Type Statistics:")
        for msg_type, count in sorted(message_counts.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {msg_type:25s}: {count:4d}")
        logger.info("")
        
        # Verdict
        if heartbeat_count > 0 and time_since_heartbeat < 5:
            logger.info("✅ TEST PASSED: Connection is healthy")
        else:
            logger.warning("⚠️  WARNING: Connection may have issues")
    
    def run_automated_test(self):
        """Run automated test sequence with commands."""
        logger.info("=" * 70)
        logger.info("Automated Test Sequence")
        logger.info("=" * 70)
        logger.info("")
        
        # Test 1: Monitor initial state
        logger.info("Test 1: Initial state monitoring (5s)")
        self.monitor_state_changes(duration=5)
        
        # Test 2: Change to GUIDED mode
        logger.info("")
        logger.info("Test 2: Changing to GUIDED mode")
        self.test_mode_change("GUIDED")
        time.sleep(2)
        self.monitor_state_changes(duration=3)
        
        # Test 3: ARM the vehicle
        logger.info("")
        logger.info("Test 3: Arming vehicle")
        self.test_arm_command()
        time.sleep(2)
        self.monitor_state_changes(duration=3)
        
        # Test 4: Change to LOITER mode
        logger.info("")
        logger.info("Test 4: Changing to LOITER mode")
        self.test_mode_change("LOITER")
        time.sleep(2)
        self.monitor_state_changes(duration=3)
        
        # Test 5: DISARM the vehicle
        logger.info("")
        logger.info("Test 5: Disarming vehicle")
        self.test_disarm_command()
        time.sleep(2)
        self.monitor_state_changes(duration=3)
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("Automated Test Complete")
        logger.info("=" * 70)
    
    def disconnect(self):
        """Close connection."""
        if self.connection:
            logger.info("")
            logger.info("Closing connection...")
            self.connection.close()
            logger.info("✓ Connection closed")


def main():
    """Main test function."""
    # Parse connection string from command line
    connection_string = 'udp:127.0.0.1:14550'
    if len(sys.argv) > 1:
        connection_string = sys.argv[1]
    
    # Create test instance
    test = MAVLinkConnectionTest(connection_string)
    
    # Connect
    if not test.connect(timeout=10):
        logger.error("Failed to connect. Exiting.")
        return 1
    
    # Request data streams
    test.request_data_streams()
    
    # Wait for streams to start
    time.sleep(2)
    
    # Run automated test
    try:
        test.run_automated_test()
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Test interrupted by user")
    finally:
        test.disconnect()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
