"""MAVLink telemetry and visual odometry interface."""

import logging
import time
import numpy as np
from typing import Optional, Tuple, List, Dict, Any
from pymavlink import mavutil
import serial.tools.list_ports
from scipy.spatial.transform import Rotation


# MAVLink protocol constants
BATTERY_NO_VOLTAGE = 65535  # Sentinel value for missing voltage
BATTERY_NO_CURRENT = -1     # Sentinel value for missing current
BATTERY_NO_REMAINING = -1   # Sentinel value for missing remaining percentage

# Coordinate conversions
RAD_TO_DEG = 57.29577951308232  # 180 / pi
DEG_TO_RAD = 0.017453292519943  # pi / 180

# MAVLink armed state flag
MAV_MODE_FLAG_SAFETY_ARMED = 128  # 0x80


class MAVLinkTelemetry:
    """
    MAVLink telemetry interface for visual odometry and telemetry communication.
    
    Provides UDP-based and USB serial communication with ArduPilot for VIO integration
    and ground station telemetry. Automatically detects available connections.
    """
    
    def __init__(self, config: dict):
        """
        Initialize MAVLink telemetry.
        
        Args:
            config: MAVLink configuration dictionary containing:
                - connection_string: MAVLink connection URI (default: 'udp:127.0.0.1:14550')
                - baud: Serial baud rate (default: 57600)
                - auto_detect: Auto-detect USB ports (default: True)
                - heartbeat_timeout: Heartbeat timeout in seconds (default: 5)
                - vio_publish_rate: VIO message rate in Hz (default: 30)
                - telemetry_rate: Telemetry read rate in Hz (default: 10)
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.connection = None
        self.is_connected = False
        
        self.connection_string = config.get('connection_string', 'udp:127.0.0.1:14550')
        self.vio_publish_rate = config.get('vio_publish_rate', 30)
        self.telemetry_rate = config.get('telemetry_rate', 10)
        self.baud = config.get('baud', 57600)
        self.auto_detect = config.get('auto_detect', True)
        self.heartbeat_timeout = config.get('heartbeat_timeout', 5)
        
        self.last_vio_publish = 0
        self.last_telemetry_read = 0
        
        # Vehicle telemetry state
        self.attitude = None
        self.position = None
        self.velocity = None
        self.gps_status = None
        self.battery_status = None
        
        # Arm/Mode state tracking with change detection
        self._armed = False              # Current armed state
        self._armed_changed = False      # Flag for state change
        self._last_arm_change_time = 0   # Timestamp of last change
        
        self._flight_mode = "UNKNOWN"    # Current flight mode
        self._flight_mode_changed = False  # Flag for state change
        self._last_mode_change_time = 0    # Timestamp of last change
        self._mode_decode_cache = {}       # Cache for mode decoding
        
        # Command logging callback (for GUI/external logging)
        self._command_logger = None  # Optional callback: Callable[[str, str], None]
    
    # ========== Properties for State Access ==========
    
    @property
    def armed(self) -> bool:
        """Get current armed state."""
        return self._armed
    
    @property
    def armed_changed(self) -> bool:
        """Check if armed state changed since last read."""
        return self._armed_changed
    
    def clear_armed_changed(self):
        """Clear the armed changed flag after processing."""
        self._armed_changed = False
    
    @property
    def flight_mode(self) -> str:
        """Get current flight mode name."""
        return self._flight_mode
    
    @property
    def flight_mode_changed(self) -> bool:
        """Check if flight mode changed since last read."""
        return self._flight_mode_changed
    
    def clear_flight_mode_changed(self):
        """Clear the flight mode changed flag after processing."""
        self._flight_mode_changed = False
    
    def set_command_logger(self, callback):
        """
        Set a callback function for logging MAVLink commands.
        
        The callback will be invoked whenever a command is sent to the vehicle.
        Useful for GUI components that want to display command activity in logs.
        
        Args:
            callback: Function with signature callback(message: str, level: str = "INFO")
                     Set to None to disable logging.
        """
        self._command_logger = callback
    
    def _log_command(self, message: str, level: str = "INFO"):
        """Log a command action through the registered callback."""
        if self._command_logger is not None:
            try:
                self._command_logger(message, level)
            except Exception as e:
                self.logger.warning(f"Error in command logger callback: {e}")
    
    # ========== Private Helper Methods ==========
    
        """
        Find available USB serial ports that might be flight controllers.
        
        Returns:
            List of serial port device paths
        """
        usb_ports = []
        try:
            ports = serial.tools.list_ports.comports()
            for port in ports:
                # Look for common flight controller USB identifiers
                if any(keyword in port.description.lower() for keyword in 
                       ['usb', 'serial', 'ch340', 'ftdi', 'cp210', 'pixhawk', 'ardupilot']):
                    usb_ports.append(port.device)
                    self.logger.info(f"Found potential flight controller port: {port.device} - {port.description}")
        except Exception as e:
            self.logger.error(f"Error scanning USB ports: {e}")
        
        return usb_ports
    
    def _try_connection(self, connection_string: str, timeout: int = 5) -> Optional[mavutil.mavlink_connection]:
        """
        Try to establish a MAVLink connection with heartbeat verification.
        
        Args:
            connection_string: MAVLink connection string
            timeout: Heartbeat timeout in seconds
            
        Returns:
            MAVLink connection object if successful, None otherwise
        """
        conn = None
        try:
            self.logger.info(f"Attempting connection: {connection_string}")
            conn = mavutil.mavlink_connection(connection_string, timeout=timeout)
            
            if conn is None:
                self.logger.debug(f"Failed to create connection object for {connection_string}")
                return None
            
            # Wait for heartbeat with timeout
            self.logger.info(f"Waiting for heartbeat (timeout: {timeout}s)...")
            msg = conn.wait_heartbeat(timeout=timeout)
            
            if msg is None:
                self.logger.debug(f"No heartbeat received within {timeout}s for {connection_string}")
                if conn:
                    conn.close()
                return None
            
            self.logger.info(f"✓ Heartbeat received from system {conn.target_system}, component {conn.target_component}")
            return conn
            
        except Exception as e:
            self.logger.debug(f"Connection failed for {connection_string}: {e}")
            if conn:
                try:
                    conn.close()
                except:
                    pass
            return None
        
    def connect(self) -> bool:
        """
        Connect to MAVLink vehicle.
        Tries configured connection first, then auto-detects USB ports if enabled.
        
        Returns:
            True if connected successfully, False otherwise
        """
        connection_attempts = []
        
        # Try configured connection first
        connection_attempts.append(self.connection_string)
        
        # If auto-detect is enabled, add USB ports to try
        if self.auto_detect:
            usb_ports = self._find_usb_ports()
            for port in usb_ports:
                connection_attempts.append(f"{port}:{self.baud}")
        
        # Try each connection
        for conn_str in connection_attempts:
            self.logger.info(f"Trying connection: {conn_str}")
            conn = self._try_connection(conn_str, timeout=self.heartbeat_timeout)
            if conn is not None:
                # Verify connection is actually working by checking target_system
                if conn.target_system == 0:
                    self.logger.warning(f"Connection established but no valid system ID (got 0)")
                    conn.close()
                    continue
                
                self.connection = conn
                self.is_connected = True
                self.logger.info(f"✓ Successfully connected to system {conn.target_system} via: {conn_str}")
                
                # Request data streams from autopilot
                self._request_data_streams()
                
                return True
        
        self.logger.error("✗ Failed to connect to MAVLink vehicle on any available port")
        return False
    
    def _request_data_streams(self):
        """
        Request data streams from autopilot at specified rates.
        This tells ArduPilot/PX4 to start sending telemetry messages.
        """
        if not self.is_connected or self.connection is None:
            return
        
        try:
            # Request all data streams at appropriate rates
            # MAV_DATA_STREAM constants from pymavlink
            streams = [
                (1, 4),   # MAV_DATA_STREAM_ALL - Not recommended, but fallback
                (2, 4),   # MAV_DATA_STREAM_RAW_SENSORS - IMU, GPS, etc.
                (3, 3),   # MAV_DATA_STREAM_EXTENDED_STATUS - Battery, mode, etc.
                (6, 3),   # MAV_DATA_STREAM_POSITION - GPS position
                (10, 10), # MAV_DATA_STREAM_EXTRA1 - Attitude (10 Hz)
                (11, 10), # MAV_DATA_STREAM_EXTRA2 - VFR_HUD (10 Hz)
                (12, 2),  # MAV_DATA_STREAM_EXTRA3 - Additional data
            ]
            
            for stream_id, rate_hz in streams:
                self.connection.mav.request_data_stream_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    stream_id,
                    rate_hz,
                    1  # start_stop: 1 = start, 0 = stop
                )
            
            self.logger.info("✓ Requested telemetry data streams from autopilot")
            
        except Exception as e:
            self.logger.warning(f"Failed to request data streams: {e}")
    
    def _decode_flight_mode(self, base_mode: int, custom_mode: int) -> str:
        """
        Decode flight mode from MAVLink HEARTBEAT message.
        
        Args:
            base_mode: Base mode flags
            custom_mode: Vehicle-specific mode number
            
        Returns:
            Human-readable flight mode string
        """
        # ArduPilot Copter modes
        copter_modes = {
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
        
        return copter_modes.get(custom_mode, f"UNKNOWN({custom_mode})")
    
    def publish_visual_odometry(self, position: np.ndarray, orientation: np.ndarray, 
                                velocity: Optional[np.ndarray] = None,
                                covariance: Optional[np.ndarray] = None) -> bool:
        """
        Publish visual odometry to ArduPilot.
        
        Args:
            position: Position vector [x, y, z] in meters (NED frame)
            orientation: Quaternion [w, x, y, z] or numpy array with shape (4,)
            velocity: Velocity vector [vx, vy, vz] in m/s (optional, default: zeros)
            covariance: 6x6 covariance matrix (optional, default: identity * 0.1)
            
        Returns:
            True if published successfully, False otherwise
        """
        if not self.is_connected or self.connection is None:
            return False
        
        current_time = time.time()
        
        # Rate limiting
        if current_time - self.last_vio_publish < 1.0 / self.vio_publish_rate:
            return True
        
        try:
            # Validate inputs
            if position is None or len(position) < 3:
                self.logger.warning("Invalid position vector for VIO")
                return False
            
            if orientation is None or len(orientation) < 4:
                self.logger.warning("Invalid orientation quaternion for VIO")
                return False
            
            # Convert quaternion [w, x, y, z] to Euler angles [roll, pitch, yaw]
            # scipy expects [x, y, z, w] format, so reorder
            q_scipy = np.array([orientation[1], orientation[2], orientation[3], orientation[0]])
            try:
                rotation = Rotation.from_quat(q_scipy)
                euler_angles = rotation.as_euler('xyz', degrees=False)  # [roll, pitch, yaw]
                roll, pitch, yaw = euler_angles
            except Exception as e:
                self.logger.error(f"Failed to convert quaternion to Euler angles: {e}")
                self.logger.debug(f"Quaternion was: {orientation}")
                return False
            
            # Convert to MAVLink time (microseconds)
            time_usec = int(current_time * 1e6)
            
            # Prepare velocity (use zeros if not provided)
            if velocity is None:
                velocity = np.array([0.0, 0.0, 0.0])
            else:
                velocity = np.array(velocity)
                if len(velocity) < 3:
                    self.logger.warning("Velocity vector has fewer than 3 components, padding with zeros")
                    velocity = np.pad(velocity, (0, 3 - len(velocity)), 'constant')
            
            # Prepare covariance (use scaled identity if not provided)
            if covariance is None:
                covariance = np.eye(6) * 0.1  # 0.1 m^2 and 0.1 rad^2 uncertainty
            else:
                covariance = np.array(covariance)
                if covariance.shape != (6, 6):
                    self.logger.warning(f"Expected 6x6 covariance, got {covariance.shape}, using identity")
                    covariance = np.eye(6) * 0.1
            
            # Flatten covariance and take only upper triangle (21 elements)
            covariance_flat = covariance.flatten()[:21]
            
            # Send VISION_POSITION_ESTIMATE message
            # Message format: time_usec, x, y, z, roll, pitch, yaw, covariance
            self.connection.mav.vision_position_estimate_send(
                time_usec,
                float(position[0]),      # x (North)
                float(position[1]),      # y (East)
                float(position[2]),      # z (Down)
                float(roll),             # roll (rad)
                float(pitch),            # pitch (rad)
                float(yaw),              # yaw (rad)
                list(covariance_flat)    # covariance upper triangle
            )
            
            self.last_vio_publish = current_time
            return True
            
        except Exception as e:
            self.logger.error(f"Error publishing visual odometry: {e}")
            return False
    
    def read_telemetry(self) -> Dict[str, Any]:
        """
        Read and process all available telemetry messages from vehicle.
        
        Updates internal state variables and returns current telemetry snapshot.
        Detects state changes (arm/disarm, mode changes) for event-driven handling.
        
        Returns:
            Dictionary containing all current telemetry data with keys:
            - attitude: [roll, pitch, yaw] in degrees, [rollspeed, pitchspeed, yawspeed] in rad/s
            - position: [lat, lon, alt, relative_alt] in degrees and meters
            - velocity: [ground_speed, vertical_speed, airspeed] in m/s
            - gps: [fix_type, satellites, eph, epv] - eph/epv in meters
            - battery: [voltage_v, current_a, remaining_%]
            - flight_mode: string (e.g., "GUIDED", "STABILIZE")
            - armed: boolean
            - armed_changed: boolean (state changed since last call)
            - flight_mode_changed: boolean (state changed since last call)
            - system_id, component_id: MAVLink identifiers
        """
        if not self.is_connected or self.connection is None:
            return {}
        
        try:
            # Process ALL available messages (non-blocking loop)
            # This ensures we don't fall behind on message processing
            while True:
                msg = self.connection.recv_match(blocking=False)
                
                if msg is None:
                    break  # No more messages available
                
                msg_type = msg.get_type()
                
                try:
                    # Parse different message types and update internal state
                    if msg_type == 'ATTITUDE':
                        self.attitude = {
                            'roll': msg.roll,
                            'pitch': msg.pitch,
                            'yaw': msg.yaw,
                            'rollspeed': msg.rollspeed,
                            'pitchspeed': msg.pitchspeed,
                            'yawspeed': msg.yawspeed
                        }
                    
                    elif msg_type == 'GLOBAL_POSITION_INT':
                        self.position = {
                            'lat': msg.lat / 1e7,
                            'lon': msg.lon / 1e7,
                            'alt': msg.alt / 1000.0,  # Convert mm to meters
                            'relative_alt': msg.relative_alt / 1000.0  # Convert mm to meters
                        }
                    
                    elif msg_type == 'LOCAL_POSITION_NED':
                        self.velocity = {
                            'vx': msg.vx,
                            'vy': msg.vy,
                            'vz': msg.vz
                        }
                    
                    elif msg_type == 'GPS_RAW_INT':
                        # Note: eph and epv are in centimeters, convert to meters
                        self.gps_status = {
                            'fix_type': msg.fix_type,
                            'satellites_visible': msg.satellites_visible,
                            'eph': msg.eph / 100.0,  # cm to meters
                            'epv': msg.epv / 100.0   # cm to meters
                        }
                    
                    elif msg_type == 'SYS_STATUS':
                        # Battery status with proper validation
                        voltage = msg.voltage_battery
                        current = msg.current_battery
                        remaining = msg.battery_remaining
                        
                        # Convert to physical units with validation
                        battery_voltage = 0.0
                        if voltage != BATTERY_NO_VOLTAGE and voltage > 0:
                            battery_voltage = voltage / 1000.0  # Convert mV to V
                            # Sanity check: typical battery voltages 7-50V
                            if battery_voltage < 5.0 or battery_voltage > 60.0:
                                self.logger.warning(f"Unrealistic battery voltage: {battery_voltage}V")
                                battery_voltage = 0.0
                        
                        battery_current = 0.0
                        if current != BATTERY_NO_CURRENT and current >= 0:
                            battery_current = current / 100.0  # Convert centi-amps to amps
                            # Sanity check: typical drone currents 0-200A
                            if battery_current > 300.0:
                                self.logger.warning(f"Unrealistic battery current: {battery_current}A")
                                battery_current = 0.0
                        
                        battery_remaining = 0
                        if remaining != BATTERY_NO_REMAINING and 0 <= remaining <= 100:
                            battery_remaining = remaining
                        
                        self.battery_status = {
                            'voltage': battery_voltage,
                            'current': battery_current,
                            'remaining': battery_remaining
                        }
                    
                    elif msg_type == 'HEARTBEAT':
                        # CRITICAL FIX: Only process HEARTBEAT from the target vehicle
                        # Ground stations (Mission Planner, MAVProxy, etc.) also send HEARTBEATs
                        # which can cause mode oscillation if not filtered out
                        
                        # Get source system ID from message
                        # pymavlink stores this in get_srcSystem() method
                        try:
                            msg_sysid = msg.get_srcSystem()
                            msg_compid = msg.get_srcComponent()
                            
                            # Check if this HEARTBEAT is from our target vehicle
                            if msg_sysid != self.connection.target_system:
                                # Ignore HEARTBEATs from other systems (GCS, companion computers, etc.)
                                self.logger.debug(f"Ignoring HEARTBEAT from system {msg_sysid} (target is {self.connection.target_system})")
                                continue
                        except (AttributeError, TypeError):
                            # If we can't determine source, process it (fail-safe)
                            # This shouldn't happen with proper pymavlink but be defensive
                            pass
                        
                        # Decode and track flight mode with change detection
                        new_mode = self._decode_flight_mode(msg.base_mode, msg.custom_mode)
                        if new_mode != self._flight_mode:
                            self.logger.info(f"Flight mode changed: {self._flight_mode} → {new_mode}")
                            self._flight_mode = new_mode
                            self._flight_mode_changed = True
                            self._last_mode_change_time = time.time()
                        # Don't update if no change - preserve current value
                        
                        # Extract and track armed state with change detection
                        # MAV_MODE_FLAG_SAFETY_ARMED = 128 (0x80)
                        new_armed = bool(msg.base_mode & MAV_MODE_FLAG_SAFETY_ARMED)
                        if new_armed != self._armed:
                            action = "ARMED" if new_armed else "DISARMED"
                            self.logger.info(f"Vehicle {action}")
                            self._armed = new_armed
                            self._armed_changed = True
                            self._last_arm_change_time = time.time()
                        # Don't update if no change - preserve current value
                
                except AttributeError as e:
                    # Message doesn't have expected field
                    self.logger.debug(f"Missing field in {msg_type} message: {e}")
                except Exception as e:
                    # Other parsing errors
                    self.logger.warning(f"Error parsing {msg_type} message: {e}")
            
            # Build result dictionary with all current telemetry
            result = {}
            
            if self.attitude:
                result['attitude'] = {
                    'roll': self.attitude.get('roll', 0) * RAD_TO_DEG,
                    'pitch': self.attitude.get('pitch', 0) * RAD_TO_DEG,
                    'yaw': self.attitude.get('yaw', 0) * RAD_TO_DEG,
                    'heading': ((self.attitude.get('yaw', 0) * RAD_TO_DEG) + 360) % 360,  # 0-360
                    'rollspeed': self.attitude.get('rollspeed', 0),
                    'pitchspeed': self.attitude.get('pitchspeed', 0),
                    'yawspeed': self.attitude.get('yawspeed', 0)
                }
            
            if self.position:
                result['position'] = {
                    'latitude': self.position.get('lat', 0),
                    'longitude': self.position.get('lon', 0),
                    'altitude': self.position.get('alt', 0),
                    'relative_altitude': self.position.get('relative_alt', 0)
                }
            
            if self.velocity:
                vx = self.velocity.get('vx', 0)
                vy = self.velocity.get('vy', 0)
                vz = self.velocity.get('vz', 0)
                
                # Only calculate speeds if we have valid velocity data
                result['velocity'] = {
                    'ground_speed': (vx**2 + vy**2)**0.5,
                    'vertical_speed': -vz,  # NED: positive down, display: positive up
                    'airspeed': (vx**2 + vy**2)**0.5  # Approximation (no airspeed sensor)
                }
            
            if self.gps_status:
                result['gps'] = {
                    'fix_type': self.gps_status.get('fix_type', 0),
                    'satellites': self.gps_status.get('satellites_visible', 0),
                    'eph': self.gps_status.get('eph', 0),  # Horizontal error in meters
                    'epv': self.gps_status.get('epv', 0)   # Vertical error in meters
                }
            
            if self.battery_status:
                result['battery'] = {
                    'voltage': self.battery_status.get('voltage', 0),
                    'current': self.battery_status.get('current', 0),
                    'remaining': self.battery_status.get('remaining', 0)
                }
            
            # Flight mode and armed state (always include, may be 'UNKNOWN'/False if no heartbeat yet)
            result['flight_mode'] = self._flight_mode
            result['mode'] = self._flight_mode  # Backwards compatibility
            result['armed'] = self._armed
            result['armed_changed'] = self._armed_changed
            result['flight_mode_changed'] = self._flight_mode_changed
            
            # DEBUG: Log what we're returning
            print(f"[Telemetry] read_telemetry returning: armed={self._armed}, mode={self._flight_mode}, armed_changed={self._armed_changed}, mode_changed={self._flight_mode_changed}")
            
            # Connection info
            if self.connection:
                result['system_id'] = self.connection.target_system
                result['component_id'] = self.connection.target_component
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error reading telemetry: {e}", exc_info=True)
            print(f"[Telemetry] ERROR in read_telemetry: {e}")
            return {}
    
    def get_flattened_telemetry(self) -> Dict[str, Any]:
        """
        Get telemetry data in a flattened format for GUI display.
        
        Returns a flat dictionary with all telemetry values at the root level,
        making it easier for UI components to access data without navigating
        nested structures.
        
        Returns:
            Flat dictionary with all telemetry values. If read fails, returns
            last known good state to prevent GUI flickering.
        """
        telemetry = self.read_telemetry()
        
        # If read_telemetry returns empty (error or not connected), 
        # return empty dict - GUI will handle gracefully
        if not telemetry:
            return {}
        
        flat = {}
        
        # Flatten attitude data
        if 'attitude' in telemetry:
            att = telemetry['attitude']
            flat['roll'] = att.get('roll', 0)
            flat['pitch'] = att.get('pitch', 0)
            flat['yaw'] = att.get('yaw', 0)
            flat['heading'] = att.get('heading', 0)
            flat['rollspeed'] = att.get('rollspeed', 0)
            flat['pitchspeed'] = att.get('pitchspeed', 0)
            flat['yawspeed'] = att.get('yawspeed', 0)
        
        # Flatten position data
        if 'position' in telemetry:
            pos = telemetry['position']
            flat['latitude'] = pos.get('latitude', 0)
            flat['longitude'] = pos.get('longitude', 0)
            flat['altitude'] = pos.get('altitude', 0)
            flat['relative_altitude'] = pos.get('relative_altitude', 0)
        
        # Flatten velocity data
        if 'velocity' in telemetry:
            vel = telemetry['velocity']
            flat['ground_speed'] = vel.get('ground_speed', 0)
            flat['vertical_speed'] = vel.get('vertical_speed', 0)
            flat['airspeed'] = vel.get('airspeed', 0)
        
        # Flatten GPS data
        if 'gps' in telemetry:
            gps = telemetry['gps']
            flat['gps_fix_type'] = gps.get('fix_type', 0)
            flat['gps_satellites'] = gps.get('satellites', 0)
            flat['gps_eph'] = gps.get('eph', 0)
            flat['gps_epv'] = gps.get('epv', 0)
        
        # Flatten battery data
        if 'battery' in telemetry:
            bat = telemetry['battery']
            flat['battery_voltage'] = bat.get('voltage', 0)
            flat['battery_current'] = bat.get('current', 0)
            flat['battery_remaining'] = bat.get('remaining', 0)
        
        # Copy root-level values (these ALWAYS exist when connected)
        flat['flight_mode'] = telemetry.get('flight_mode', 'UNKNOWN')
        flat['mode'] = telemetry.get('mode', 'UNKNOWN')
        flat['armed'] = telemetry.get('armed', False)
        flat['armed_changed'] = telemetry.get('armed_changed', False)
        flat['flight_mode_changed'] = telemetry.get('flight_mode_changed', False)
        flat['system_id'] = telemetry.get('system_id', 0)
        flat['component_id'] = telemetry.get('component_id', 0)
        
        # Clear the change flags after reading them (consumed by this call)
        # This prevents the same change from being reported multiple times
        if telemetry.get('armed_changed', False):
            self.clear_armed_changed()
        if telemetry.get('flight_mode_changed', False):
            self.clear_flight_mode_changed()
        
        return flat

    
    def send_velocity_ned(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0):
        """
        Send velocity command in NED frame (North-East-Down)
        
        Args:
            vx: Velocity in North direction (m/s)
            vy: Velocity in East direction (m/s)
            vz: Velocity in Down direction (m/s, positive = down)
            yaw_rate: Yaw rate (rad/s)
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot send velocity: not connected to MAVLink")
            return
        
        try:
            # SET_POSITION_TARGET_LOCAL_NED message with velocity fields
            self.connection.mav.set_position_target_local_ned_send(
                0,  # time_boot_ms (not used)
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_FRAME_LOCAL_NED,
                0b0000111111000111,  # type_mask (velocity enabled, position/accel disabled)
                0, 0, 0,  # x, y, z positions (not used)
                vx, vy, vz,  # x, y, z velocity in m/s
                0, 0, 0,  # x, y, z acceleration (not used)
                0, yaw_rate  # yaw, yaw_rate
            )
        except Exception as e:
            self.logger.error(f"Error sending velocity command: {e}")
    
    def send_velocity_body(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0):
        """
        Send velocity command in body frame (forward-right-down)
        
        Args:
            vx: Forward velocity (m/s, positive = forward)
            vy: Right velocity (m/s, positive = right)
            vz: Down velocity (m/s, positive = down)
            yaw_rate: Yaw rate (rad/s, positive = clockwise)
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot send velocity: not connected to MAVLink")
            return
        
        try:
            # SET_POSITION_TARGET_LOCAL_NED with body frame
            self.connection.mav.set_position_target_local_ned_send(
                0,  # time_boot_ms
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_FRAME_BODY_NED,  # Body frame
                0b0000111111000111,  # type_mask (velocity enabled)
                0, 0, 0,  # positions (not used)
                vx, vy, vz,  # velocities
                0, 0, 0,  # accelerations (not used)
                0, yaw_rate  # yaw, yaw_rate
            )
        except Exception as e:
            self.logger.error(f"Error sending body velocity command: {e}")
    
    def send_position_target(self, x: float, y: float, z: float, yaw: float = 0.0):
        """
        Send position target command in NED frame
        
        Args:
            x: North position (m)
            y: East position (m)
            z: Down position (m, negative = altitude)
            yaw: Yaw angle (rad)
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot send position: not connected to MAVLink")
            return
        
        try:
            # SET_POSITION_TARGET_LOCAL_NED with position fields
            self.connection.mav.set_position_target_local_ned_send(
                0,  # time_boot_ms
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_FRAME_LOCAL_NED,
                0b0000111111111000,  # type_mask (position enabled, velocity/accel disabled)
                x, y, z,  # positions
                0, 0, 0,  # velocities (not used)
                0, 0, 0,  # accelerations (not used)
                yaw, 0  # yaw, yaw_rate
            )
        except Exception as e:
            self.logger.error(f"Error sending position command: {e}")
    
    def arm(self) -> bool:
        """
        Send arm command to vehicle.
        
        Note: This sends the command but the actual arm state is determined by HEARTBEAT
        messages from the vehicle. Use the `armed` property and `armed_changed` flag
        to detect when the vehicle actually arms.
        
        Returns:
            True if arm command sent successfully, False otherwise
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot arm: not connected to MAVLink")
            return False
        
        try:
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,  # confirmation
                1,  # 1 = arm
                0, 0, 0, 0, 0, 0  # unused parameters
            )
            self.logger.info("Arm command sent to vehicle")
            self._log_command("ARM command sent to vehicle", "SUCCESS")
            return True
        except Exception as e:
            self.logger.error(f"Error sending arm command: {e}")
            return False
    
    def disarm(self) -> bool:
        """
        Send disarm command to vehicle.
        
        Note: This sends the command but the actual disarm state is determined by HEARTBEAT
        messages from the vehicle. Use the `armed` property and `armed_changed` flag
        to detect when the vehicle actually disarms.
        
        Returns:
            True if disarm command sent successfully, False otherwise
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot disarm: not connected to MAVLink")
            return False
        
        try:
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,  # confirmation
                0,  # 0 = disarm
                0, 0, 0, 0, 0, 0  # unused parameters
            )
            self.logger.info("Disarm command sent to vehicle")
            self._log_command("DISARM command sent to vehicle", "WARNING")
            return True
        except Exception as e:
            self.logger.error(f"Error sending disarm command: {e}")
            return False
    
    def set_mode(self, mode: str) -> bool:
        """
        Send flight mode change command to vehicle.

        Note: This sends the command but the actual mode is determined by HEARTBEAT
        messages from the vehicle. Use the `flight_mode` property and `flight_mode_changed`
        flag to detect when the vehicle actually changes modes.

        Args:
            mode: Flight mode name (e.g., "GUIDED", "LOITER", "RTL", "STABILIZE")
                 Case-insensitive. See copter_modes dict for valid options.

        Returns:
            True if mode command sent successfully, False otherwise
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot set mode: not connected to MAVLink")
            return False

        # ArduPilot Copter mode mapping (reverse lookup)
        copter_modes = {
            "STABILIZE": 0, "ACRO": 1, "ALT_HOLD": 2, "AUTO": 3,
            "GUIDED": 4, "LOITER": 5, "RTL": 6, "CIRCLE": 7,
            "LAND": 9, "DRIFT": 11, "SPORT": 13, "FLIP": 14,
            "AUTOTUNE": 15, "POSHOLD": 16, "BRAKE": 17, "THROW": 18,
            "AVOID_ADSB": 19, "GUIDED_NOGPS": 20, "SMART_RTL": 21,
            "FLOWHOLD": 22, "FOLLOW": 23, "ZIGZAG": 24,
            "SYSTEMID": 25, "AUTOROTATE": 26, "AUTO_RTL": 27
        }

        mode_upper = mode.upper()
        if mode_upper not in copter_modes:
            self.logger.error(f"Unknown flight mode: {mode}")
            self.logger.info(f"Valid modes: {', '.join(copter_modes.keys())}")
            return False

        mode_id = copter_modes[mode_upper]

        try:
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_CMD_DO_SET_MODE,
                0,  # confirmation
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,  # base mode
                mode_id,  # custom mode
                0, 0, 0, 0, 0  # unused parameters
            )
            self.logger.info(f"Mode change command sent: {mode}")
            self._log_command(f"Flight mode changed to {mode}", "INFO")
            return True
        except Exception as e:
            self.logger.error(f"Error sending mode change command: {e}")
            return False

    def takeoff(self, altitude: float) -> bool:
        """
        Command vehicle to take off to specified altitude.

        Args:
            altitude: Target altitude in meters (AGL - Above Ground Level)

        Returns:
            True if takeoff command sent successfully, False otherwise
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot takeoff: not connected to MAVLink")
            return False

        try:
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                0,  # confirmation
                0, 0, 0, 0,  # params 1-4 (not used for copter)
                0, 0,  # lat, lon (not used for copter)
                altitude  # altitude
            )
            self.logger.info(f"Takeoff command sent: {altitude}m")
            self._log_command(f"TAKEOFF to {altitude}m", "SUCCESS")
            return True
        except Exception as e:
            self.logger.error(f"Error sending takeoff command: {e}")
            return False

    def land(self) -> bool:
        """
        Command vehicle to land at current position.

        Returns:
            True if land command sent successfully, False otherwise
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot land: not connected to MAVLink")
            return False

        try:
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_CMD_NAV_LAND,
                0,  # confirmation
                0, 0, 0, 0,  # params 1-4
                0, 0, 0  # lat, lon, alt (current position)
            )
            self.logger.info("Land command sent")
            self._log_command("LAND command sent", "WARNING")
            return True
        except Exception as e:
            self.logger.error(f"Error sending land command: {e}")
            return False

    def return_to_launch(self) -> bool:
        """
        Command vehicle to return to launch position (RTL).

        Returns:
            True if RTL command sent successfully, False otherwise
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot RTL: not connected to MAVLink")
            return False

        try:
            # Set mode to RTL
            return self.set_mode("RTL")
        except Exception as e:
            self.logger.error(f"Error sending RTL command: {e}")
            return False

    def goto_position_global(self, lat: float, lon: float, alt: float) -> bool:
        """
        Command vehicle to fly to global position (GPS coordinates).

        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            alt: Altitude in meters (AMSL - Above Mean Sea Level)

        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot goto position: not connected to MAVLink")
            return False

        try:
            # Send position target in global frame
            self.connection.mav.set_position_target_global_int_send(
                0,  # time_boot_ms
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                0b0000111111111000,  # type_mask (position only)
                int(lat * 1e7),  # lat in degE7
                int(lon * 1e7),  # lon in degE7
                alt,  # altitude
                0, 0, 0,  # velocities
                0, 0, 0,  # accelerations
                0, 0  # yaw, yaw_rate
            )
            self.logger.info(f"Goto position command sent: lat={lat}, lon={lon}, alt={alt}")
            self._log_command(f"GOTO position: ({lat:.6f}, {lon:.6f}) @ {alt}m", "INFO")
            return True
        except Exception as e:
            self.logger.error(f"Error sending goto position command: {e}")
            return False

    def set_yaw(self, yaw_deg: float, yaw_rate_degs: float = 10.0, relative: bool = False) -> bool:
        """
        Command vehicle to rotate to specified yaw angle.

        Args:
            yaw_deg: Target yaw angle in degrees (0-360)
            yaw_rate_degs: Yaw rate in degrees per second (default: 10.0)
            relative: If True, yaw is relative to current heading. If False, absolute (default: False)

        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot set yaw: not connected to MAVLink")
            return False

        try:
            # Direction: 1 = clockwise, -1 = counter-clockwise (auto-select shortest path = 0)
            direction = 0

            # Relative flag: 0 = absolute, 1 = relative
            is_relative = 1 if relative else 0

            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                0,  # confirmation
                yaw_deg,  # target yaw angle
                yaw_rate_degs,  # yaw rate
                direction,  # direction (-1 ccw, 1 cw, 0 auto)
                is_relative,  # relative (0 = absolute, 1 = relative)
                0, 0, 0  # unused
            )
            rel_str = "relative" if relative else "absolute"
            self.logger.info(f"Set yaw command sent: {yaw_deg}° ({rel_str})")
            self._log_command(f"SET YAW to {yaw_deg}° ({rel_str})", "INFO")
            return True
        except Exception as e:
            self.logger.error(f"Error sending set yaw command: {e}")
            return False

    def set_home_position(self, lat: Optional[float] = None, lon: Optional[float] = None, alt: Optional[float] = None) -> bool:
        """
        Set home position for the vehicle.

        Args:
            lat: Latitude in degrees (None = use current position)
            lon: Longitude in degrees (None = use current position)
            alt: Altitude in meters AMSL (None = use current position)

        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot set home: not connected to MAVLink")
            return False

        try:
            if lat is None or lon is None or alt is None:
                # Set home to current position
                self.connection.mav.command_long_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    mavutil.mavlink.MAV_CMD_DO_SET_HOME,
                    0,  # confirmation
                    1,  # 1 = use current position
                    0, 0, 0, 0, 0, 0
                )
                self.logger.info("Set home to current position")
                self._log_command("SET HOME to current position", "INFO")
            else:
                # Set home to specified position
                self.connection.mav.command_long_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    mavutil.mavlink.MAV_CMD_DO_SET_HOME,
                    0,  # confirmation
                    0,  # 0 = use specified position
                    0, 0, 0,
                    lat, lon, alt
                )
                self.logger.info(f"Set home to: lat={lat}, lon={lon}, alt={alt}")
                self._log_command(f"SET HOME to ({lat:.6f}, {lon:.6f}) @ {alt}m", "INFO")
            return True
        except Exception as e:
            self.logger.error(f"Error sending set home command: {e}")
            return False

    def emergency_stop(self) -> bool:
        """
        Emergency stop - immediately disarm motors (USE WITH CAUTION!).
        This will cause the drone to fall if in flight.

        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot emergency stop: not connected to MAVLink")
            return False

        try:
            # Force disarm (param2 = 21196 is the magic number for force disarm)
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,  # confirmation
                0,  # 0 = disarm
                21196,  # force flag
                0, 0, 0, 0, 0
            )
            self.logger.warning("EMERGENCY STOP command sent")
            self._log_command("⚠️ EMERGENCY STOP - MOTORS DISARMED", "ERROR")
            return True
        except Exception as e:
            self.logger.error(f"Error sending emergency stop command: {e}")
            return False

    def pause(self) -> bool:
        """
        Pause current mission/movement (switch to BRAKE mode if available, otherwise LOITER).

        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot pause: not connected to MAVLink")
            return False

        try:
            # Try BRAKE mode first (better for immediate stop)
            success = self.set_mode("BRAKE")
            if not success:
                # Fallback to LOITER
                success = self.set_mode("LOITER")
                if success:
                    self.logger.info("Paused (switched to LOITER mode)")
                    self._log_command("PAUSE - switched to LOITER", "WARNING")
            else:
                self.logger.info("Paused (switched to BRAKE mode)")
                self._log_command("PAUSE - switched to BRAKE", "WARNING")
            return success
        except Exception as e:
            self.logger.error(f"Error sending pause command: {e}")
            return False

    def resume_guided(self) -> bool:
        """
        Resume guided mode for autonomous control.

        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot resume: not connected to MAVLink")
            return False

        return self.set_mode("GUIDED")

    def send_velocity_with_yaw(self, vx: float, vy: float, vz: float, yaw_deg: float, frame: str = "body") -> bool:
        """
        Send velocity command with explicit yaw angle (improved version).

        Args:
            vx: Velocity in x-direction (m/s)
            vy: Velocity in y-direction (m/s)
            vz: Velocity in z-direction (m/s, positive = down)
            yaw_deg: Yaw angle in degrees (0-360)
            frame: "body" for body frame, "ned" for NED frame

        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.is_connected or self.connection is None:
            self.logger.warning("Cannot send velocity: not connected to MAVLink")
            return False

        try:
            # Convert yaw to radians
            yaw_rad = yaw_deg * DEG_TO_RAD

            # Select frame
            if frame.lower() == "body":
                mav_frame = mavutil.mavlink.MAV_FRAME_BODY_NED
            else:
                mav_frame = mavutil.mavlink.MAV_FRAME_LOCAL_NED

            # SET_POSITION_TARGET_LOCAL_NED with velocity and yaw
            self.connection.mav.set_position_target_local_ned_send(
                0,  # time_boot_ms
                self.connection.target_system,
                self.connection.target_component,
                mav_frame,
                0b0000111111000111,  # type_mask (velocity enabled, yaw enabled)
                0, 0, 0,  # positions (not used)
                vx, vy, vz,  # velocities
                0, 0, 0,  # accelerations (not used)
                yaw_rad, 0  # yaw (rad), yaw_rate (not used)
            )
            return True
        except Exception as e:
            self.logger.error(f"Error sending velocity with yaw command: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MAVLink vehicle."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        self.is_connected = False
        self.logger.info("Disconnected from MAVLink")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
