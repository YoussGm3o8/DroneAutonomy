"""Configuration management for DroneAutonomy."""

import yaml
import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """Configuration manager for the drone autonomy system."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self.config = self._load_default_config()
        
        if config_path and os.path.exists(config_path):
            self.load(config_path)
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            'video': {
                'gstreamer_pipeline': 'udpsrc port=5600 ! application/x-rtp ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! appsink',
                'width': 1280,
                'height': 720,
                'fps': 30,
                'backend': 'gstreamer'
            },
            'camera': {
                'fx': 500.0,
                'fy': 500.0,
                'cx': 640.0,
                'cy': 360.0,
                'k1': 0.0,
                'k2': 0.0,
                'p1': 0.0,
                'p2': 0.0
            },
            'vio': {
                'enabled': True,
                'type': 'vins-mono',  # or 'orb-slam3'
                'imu_rate': 200,
                'output_rate': 30
            },
            'depth': {
                'model': 'depth_anything_v2_vits',
                'device': 'cuda',
                'input_size': (640, 480),
                'output_scale': 0.5
            },
            'detection': {
                'yolo_model': 'yolov8n.pt',
                'confidence_threshold': 0.5,
                'nms_threshold': 0.4,
                'device': 'cuda',
                'use_tensorrt': False,
                'classes': ['person', 'car', 'truck', 'obstacle']
            },
            'target_detection': {
                'hsv_lower': [0, 100, 100],
                'hsv_upper': [10, 255, 255],
                'min_radius': 10,
                'max_radius': 200,
                'circle_threshold': 0.7
            },
            'mavlink': {
                'connection_string': 'udp:127.0.0.1:14550',
                'baud': 57600,
                'auto_detect': True,
                'heartbeat_timeout': 5,
                'vio_publish_rate': 30,
                'telemetry_rate': 10
            },
            'fusion': {
                'depth_weight': 0.6,
                'detection_weight': 0.4,
                'min_confidence': 0.6,
                'proximity_threshold': 2.0  # meters
            },
            'simulation': {
                'enabled': False,
                'airsim_ip': '127.0.0.1',
                'airsim_port': 41451
            },
            'logging': {
                'level': 'INFO',
                'save_video': False,
                'save_detections': True,
                'log_dir': 'logs'
            }
        }
    
    def load(self, config_path: str):
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
        """
        with open(config_path, 'r') as f:
            user_config = yaml.safe_load(f)
        
        # Deep merge user config with default config
        self._deep_merge(self.config, user_config)
    
    def save(self, config_path: str):
        """
        Save current configuration to YAML file.
        
        Args:
            config_path: Path to save YAML configuration file
        """
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
    
    def _deep_merge(self, base: Dict, update: Dict):
        """
        Deep merge update dict into base dict.
        
        Args:
            base: Base dictionary to merge into
            update: Dictionary with updates
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default=None):
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'video.width')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """
        Set configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'video.width')
            value: Value to set
        """
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
