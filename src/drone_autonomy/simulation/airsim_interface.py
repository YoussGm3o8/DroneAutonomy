"""AirSim simulation integration for testing and validation."""

import logging
import numpy as np
from typing import Optional, Tuple


class AirSimInterface:
    """
    AirSim simulation interface for drone testing.
    
    Provides integration with AirSim for safe testing and dataset creation.
    """
    
    def __init__(self, config: dict):
        """
        Initialize AirSim interface.
        
        Args:
            config: Simulation configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.is_connected = False
        
        self.airsim_ip = config.get('ip', '127.0.0.1')
        self.airsim_port = config.get('port', 41451)
        self.camera_name = config.get('camera_name', '0')
        
    def connect(self) -> bool:
        """
        Connect to AirSim.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            # Import airsim only when needed
            import airsim
            
            self.logger.info(f"Connecting to AirSim at {self.airsim_ip}:{self.airsim_port}")
            self.client = airsim.MultirotorClient(ip=self.airsim_ip, port=self.airsim_port)
            self.client.confirmConnection()
            self.client.enableApiControl(True)
            self.client.armDisarm(True)
            
            self.is_connected = True
            self.logger.info("Connected to AirSim")
            return True
            
        except ImportError:
            self.logger.error("AirSim package not installed. Install with: pip install airsim")
            return False
        except Exception as e:
            self.logger.error(f"Error connecting to AirSim: {e}")
            return False
    
    def get_camera_image(self, camera_name: Optional[str] = None) -> Optional[np.ndarray]:
        """
        Get camera image from AirSim.
        
        Args:
            camera_name: Camera name (uses default from config if not specified)
            
        Returns:
            BGR image or None
        """
        if not self.is_connected or self.client is None:
            return None
        
        if camera_name is None:
            camera_name = self.camera_name
        
        try:
            import airsim
            
            # Request image
            responses = self.client.simGetImages([
                airsim.ImageRequest(camera_name, airsim.ImageType.Scene, False, False)
            ])
            
            if responses and len(responses) > 0:
                response = responses[0]
                
                # Convert to numpy array
                img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)
                img_rgb = img1d.reshape(response.height, response.width, 3)
                
                # Convert RGB to BGR
                img_bgr = img_rgb[:, :, ::-1]
                
                return img_bgr
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting camera image: {e}")
            return None
    
    def get_imu_data(self) -> Optional[dict]:
        """
        Get IMU data from AirSim.
        
        Returns:
            Dictionary with IMU data or None
        """
        if not self.is_connected or self.client is None:
            return None
        
        try:
            imu_data = self.client.getImuData()
            
            return {
                'linear_acceleration': np.array([
                    imu_data.linear_acceleration.x_val,
                    imu_data.linear_acceleration.y_val,
                    imu_data.linear_acceleration.z_val
                ]),
                'angular_velocity': np.array([
                    imu_data.angular_velocity.x_val,
                    imu_data.angular_velocity.y_val,
                    imu_data.angular_velocity.z_val
                ]),
                'orientation': np.array([
                    imu_data.orientation.w_val,
                    imu_data.orientation.x_val,
                    imu_data.orientation.y_val,
                    imu_data.orientation.z_val
                ])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting IMU data: {e}")
            return None
    
    def get_ground_truth_pose(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Get ground truth pose from AirSim.
        
        Returns:
            Tuple of (position, orientation_quaternion)
        """
        if not self.is_connected or self.client is None:
            return None, None
        
        try:
            state = self.client.getMultirotorState()
            
            position = np.array([
                state.kinematics_estimated.position.x_val,
                state.kinematics_estimated.position.y_val,
                state.kinematics_estimated.position.z_val
            ])
            
            orientation = np.array([
                state.kinematics_estimated.orientation.w_val,
                state.kinematics_estimated.orientation.x_val,
                state.kinematics_estimated.orientation.y_val,
                state.kinematics_estimated.orientation.z_val
            ])
            
            return position, orientation
            
        except Exception as e:
            self.logger.error(f"Error getting ground truth pose: {e}")
            return None, None
    
    def takeoff(self, timeout_sec: float = 5.0):
        """
        Takeoff in AirSim.
        
        Args:
            timeout_sec: Timeout in seconds
        """
        if self.is_connected and self.client is not None:
            try:
                self.client.takeoffAsync(timeout_sec=timeout_sec).join()
                self.logger.info("Takeoff completed")
            except Exception as e:
                self.logger.error(f"Error during takeoff: {e}")
    
    def land(self, timeout_sec: float = 5.0):
        """
        Land in AirSim.
        
        Args:
            timeout_sec: Timeout in seconds
        """
        if self.is_connected and self.client is not None:
            try:
                self.client.landAsync(timeout_sec=timeout_sec).join()
                self.logger.info("Landing completed")
            except Exception as e:
                self.logger.error(f"Error during landing: {e}")
    
    def reset(self):
        """Reset AirSim simulation."""
        if self.is_connected and self.client is not None:
            try:
                self.client.reset()
                self.logger.info("Simulation reset")
            except Exception as e:
                self.logger.error(f"Error resetting simulation: {e}")
    
    def disconnect(self):
        """Disconnect from AirSim."""
        if self.client is not None:
            try:
                self.client.armDisarm(False)
                self.client.enableApiControl(False)
            except:
                pass
            self.client = None
        self.is_connected = False
        self.logger.info("Disconnected from AirSim")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
