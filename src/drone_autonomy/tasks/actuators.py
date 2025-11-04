"""
Water Actuator and Upload Interfaces

Provides interfaces for water system actuation and automatic deliverable upload.
"""

import logging
from typing import Optional
from pathlib import Path
import shutil


class WaterActuator:
    """
    Water system actuator interface
    
    Controls water dispensing system for wet-capture tasks.
    """
    
    def __init__(self, config: dict, logger: Optional[logging.Logger] = None):
        """
        Initialize water actuator
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger("WaterActuator")
        
        self.pin = config.get('gpio_pin', 17)  # GPIO pin for relay/servo
        self.active = False
        
        self.logger.info(f"Water actuator initialized on pin {self.pin}")
    
    def reset(self):
        """Reset actuator to inactive state"""
        self.active = False
        self.logger.info("Water actuator reset")
    
    def activate(self):
        """Activate water system"""
        if not self.active:
            self.active = True
            self.logger.info("💧 Water system activated")
            # In real implementation: GPIO.output(self.pin, GPIO.HIGH)
    
    def deactivate(self):
        """Deactivate water system"""
        if self.active:
            self.active = False
            self.logger.info("Water system deactivated")
            # In real implementation: GPIO.output(self.pin, GPIO.LOW)
    
    def is_active(self) -> bool:
        """Check if water system is active"""
        return self.active


class AutoUploader:
    """
    Automatic deliverable uploader
    
    Uploads photos and descriptions to competition server for judge confirmation.
    """
    
    def __init__(self, config: dict, logger: Optional[logging.Logger] = None):
        """
        Initialize auto uploader
        
        Args:
            config: Configuration dictionary with server details
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger("AutoUploader")
        
        self.server_url = config.get('server_url', 'http://localhost:8000')
        self.api_key = config.get('api_key', '')
        self.team_id = config.get('team_id', 'team_001')
        
        # Staging directory for failed uploads
        self.staging_dir = Path(config.get('staging_dir', 'logs/upload_staging'))
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Auto uploader initialized")
        self.logger.info(f"Server: {self.server_url}")
        self.logger.info(f"Team: {self.team_id}")
    
    def upload_file(self, filepath: str, category: str = 'photo') -> bool:
        """
        Upload file to competition server
        
        Args:
            filepath: Path to file to upload
            category: File category ('photo', 'description', 'log')
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            filepath = Path(filepath)
            
            if not filepath.exists():
                self.logger.error(f"File not found: {filepath}")
                return False
            
            self.logger.info(f"Uploading {category}: {filepath.name}")
            
            # In real implementation, use requests to POST to server:
            # with open(filepath, 'rb') as f:
            #     files = {'file': f}
            #     data = {
            #         'team_id': self.team_id,
            #         'category': category,
            #         'api_key': self.api_key,
            #     }
            #     response = requests.post(
            #         f"{self.server_url}/api/upload",
            #         files=files,
            #         data=data,
            #         timeout=30
            #     )
            #     return response.status_code == 200
            
            # Simulation: Copy to staging directory
            staging_file = self.staging_dir / f"{category}_{filepath.name}"
            shutil.copy2(filepath, staging_file)
            
            self.logger.info(f"✓ Upload successful: {filepath.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Upload failed: {e}", exc_info=True)
            return False
    
    def upload_batch(self, filepaths: list, category: str = 'photo') -> dict:
        """
        Upload multiple files
        
        Args:
            filepaths: List of file paths
            category: File category
            
        Returns:
            Dictionary with success/failure counts
        """
        results = {'success': 0, 'failed': 0, 'failed_files': []}
        
        for filepath in filepaths:
            if self.upload_file(filepath, category):
                results['success'] += 1
            else:
                results['failed'] += 1
                results['failed_files'].append(filepath)
        
        self.logger.info(f"Batch upload complete: {results['success']}/{len(filepaths)} successful")
        
        return results
    
    def retry_failed_uploads(self) -> int:
        """
        Retry uploading files in staging directory
        
        Returns:
            Number of successful retries
        """
        staged_files = list(self.staging_dir.glob('*'))
        
        if not staged_files:
            self.logger.info("No staged files to retry")
            return 0
        
        self.logger.info(f"Retrying {len(staged_files)} staged files...")
        
        successful = 0
        for filepath in staged_files:
            # Extract category from filename
            category = filepath.name.split('_')[0] if '_' in filepath.name else 'photo'
            
            if self.upload_file(str(filepath), category):
                successful += 1
                filepath.unlink()  # Delete after successful upload
        
        self.logger.info(f"Retry complete: {successful}/{len(staged_files)} successful")
        
        return successful
