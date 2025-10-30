"""MAVLink telemetry and visual odometry interface."""

import logging
import time
import numpy as np
from typing import Optional, Tuple
from pymavlink import mavutil


class MAVLinkTelemetry:
    """
    MAVLink telemetry interface for visual odometry and telemetry communication.
    
    Provides UDP-based communication with ArduPilot for VIO integration and
    ground station telemetry.
    """
    
    def __init__(self, config: dict):
        """
        Initialize MAVLink telemetry.
        
        Args:
            config: MAVLink configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.connection = None
        self.is_connected = False
        
        self.connection_string = config.get('connection_string', 'udp:127.0.0.1:14550')
        self.vio_publish_rate = config.get('vio_publish_rate', 30)
        self.telemetry_rate = config.get('telemetry_rate', 10)
        
        self.last_vio_publish = 0
        self.last_telemetry_read = 0
        
        # Vehicle state
        self.attitude = None
        self.position = None
        self.velocity = None
        self.gps_status = None
        
    def connect(self) -> bool:
        """
        Connect to MAVLink vehicle.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            self.logger.info(f"Connecting to MAVLink: {self.connection_string}")
            self.connection = mavutil.mavlink_connection(self.connection_string)
            
            # Wait for heartbeat
            self.logger.info("Waiting for heartbeat...")
            self.connection.wait_heartbeat(timeout=10)
            
            self.is_connected = True
            self.logger.info(f"Connected to system {self.connection.target_system}, component {self.connection.target_component}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to MAVLink: {e}")
            return False
    
    def publish_visual_odometry(self, position: np.ndarray, orientation: np.ndarray, 
                                velocity: Optional[np.ndarray] = None,
                                covariance: Optional[np.ndarray] = None) -> bool:
        """
        Publish visual odometry to ArduPilot.
        
        Args:
            position: Position vector [x, y, z] in meters (NED frame)
            orientation: Quaternion [w, x, y, z]
            velocity: Velocity vector [vx, vy, vz] in m/s (optional)
            covariance: 6x6 covariance matrix (optional)
            
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
            # Convert to MAVLink time (microseconds)
            time_usec = int(current_time * 1e6)
            
            # Prepare velocity (use zeros if not provided)
            if velocity is None:
                velocity = np.zeros(3)
            
            # Prepare covariance (use identity if not provided)
            if covariance is None:
                covariance = np.eye(6).flatten()
            else:
                covariance = covariance.flatten()
            
            # Send VISION_POSITION_ESTIMATE message
            self.connection.mav.vision_position_estimate_send(
                time_usec,
                float(position[0]),
                float(position[1]),
                float(position[2]),
                float(orientation[1]),  # roll
                float(orientation[2]),  # pitch
                float(orientation[3]),  # yaw
                list(covariance[:21])  # Only 21 elements for upper triangle
            )
            
            self.last_vio_publish = current_time
            return True
            
        except Exception as e:
            self.logger.error(f"Error publishing visual odometry: {e}")
            return False
    
    def read_telemetry(self) -> dict:
        """
        Read telemetry from vehicle.
        
        Returns:
            Dictionary with telemetry data
        """
        if not self.is_connected or self.connection is None:
            return {}
        
        try:
            # Try to receive a message (non-blocking)
            msg = self.connection.recv_match(blocking=False)
            
            if msg is not None:
                msg_type = msg.get_type()
                
                # Parse different message types
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
                        'alt': msg.alt / 1000.0,
                        'relative_alt': msg.relative_alt / 1000.0
                    }
                
                elif msg_type == 'LOCAL_POSITION_NED':
                    self.velocity = {
                        'vx': msg.vx,
                        'vy': msg.vy,
                        'vz': msg.vz
                    }
                
                elif msg_type == 'GPS_RAW_INT':
                    self.gps_status = {
                        'fix_type': msg.fix_type,
                        'satellites_visible': msg.satellites_visible,
                        'eph': msg.eph,
                        'epv': msg.epv
                    }
            
            return {
                'attitude': self.attitude,
                'position': self.position,
                'velocity': self.velocity,
                'gps_status': self.gps_status
            }
            
        except Exception as e:
            self.logger.error(f"Error reading telemetry: {e}")
            return {}
    
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
