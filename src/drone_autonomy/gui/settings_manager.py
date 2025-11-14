"""
Settings Manager for Drone Autonomy GUI

Handles persistent storage of user settings using JSON format.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any
import logging


class SettingsManager:
    """
    Manages persistent storage of application settings
    """
    
    def __init__(self, settings_file: str = "config/gui_settings.json"):
        """
        Initialize settings manager
        
        Args:
            settings_file: Path to settings JSON file (relative to project root)
        """
        self.logger = logging.getLogger(__name__)
        self.settings_file = Path(settings_file)
        
        # Ensure config directory exists
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Default settings
        self.default_settings = {
            'depth': {
                'model': 'depth_anything_v2_vits_tensorrt_fp16',
                'device': 'cuda',
                'output_width': 518,  # Native resolution for best performance
                'output_height': 518,
            },
            'detection': {
                'confidence_threshold': 0.5,
                'nms_threshold': 0.4,
                'imgsz': 640,
            },
            'performance': {
                'max_fps': 30,
                'enable_depth': True,
                'enable_detection': True,
            },
            'display': {
                'show_fps': False,
                'default_view': 'Full Overlay',
                'depth_opacity': 50,
            },
            'window': {
                'width': 1600,
                'height': 900,
                'x': 100,
                'y': 100,
            }
        }
    
    def load_settings(self) -> Dict[str, Any]:
        """
        Load settings from file, or return defaults if file doesn't exist
        
        Returns:
            Dictionary of settings
        """
        if not self.settings_file.exists():
            self.logger.info(f"Settings file not found, using defaults: {self.settings_file}")
            return self.default_settings.copy()
        
        try:
            with open(self.settings_file, 'r') as f:
                loaded_settings = json.load(f)
            
            # Merge with defaults to ensure all keys exist
            merged_settings = self._merge_with_defaults(loaded_settings)
            
            self.logger.info(f"Settings loaded from: {self.settings_file}")
            return merged_settings
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing settings file: {e}")
            self.logger.info("Using default settings")
            return self.default_settings.copy()
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            return self.default_settings.copy()
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save settings to file
        
        Args:
            settings: Dictionary of settings to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            self.logger.info(f"Settings saved to: {self.settings_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            return False
    
    def _merge_with_defaults(self, loaded_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge loaded settings with defaults to ensure all keys exist
        
        Args:
            loaded_settings: Settings loaded from file
            
        Returns:
            Merged settings dictionary
        """
        merged = self.default_settings.copy()
        
        for category, values in loaded_settings.items():
            if category in merged and isinstance(values, dict):
                # Update category with loaded values
                merged[category].update(values)
            else:
                # Add new category
                merged[category] = values
        
        return merged
    
    def get_default_settings(self) -> Dict[str, Any]:
        """
        Get default settings
        
        Returns:
            Dictionary of default settings
        """
        return self.default_settings.copy()
    
    def reset_to_defaults(self) -> bool:
        """
        Reset settings to defaults and save
        
        Returns:
            True if successful, False otherwise
        """
        return self.save_settings(self.default_settings)
