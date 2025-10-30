"""Monocular depth estimation using MiDaS."""

import torch
import cv2
import numpy as np
import logging
from typing import Tuple, Optional


class DepthEstimator:
    """
    Monocular depth estimator using MiDaS.
    
    Provides dense or semi-dense relative depth estimation for near-field
    obstacle awareness.
    """
    
    def __init__(self, config: dict):
        """
        Initialize depth estimator.
        
        Args:
            config: Depth estimation configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.transform = None
        self.device = config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu')
        self.input_size = config.get('input_size', (384, 384))
        self.output_scale = config.get('output_scale', 0.5)
        
    def load_model(self) -> bool:
        """
        Load MiDaS depth estimation model.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            model_type = self.config.get('model', 'MiDaS_small')
            
            # Load MiDaS model
            if model_type == 'MiDaS_small':
                self.model = torch.hub.load('intel-isl/MiDaS', 'MiDaS_small')
            elif model_type == 'DPT_Hybrid':
                self.model = torch.hub.load('intel-isl/MiDaS', 'DPT_Hybrid')
            elif model_type == 'DPT_Large':
                self.model = torch.hub.load('intel-isl/MiDaS', 'DPT_Large')
            else:
                self.model = torch.hub.load('intel-isl/MiDaS', 'MiDaS_small')
            
            # Load transforms
            midas_transforms = torch.hub.load('intel-isl/MiDaS', 'transforms')
            
            if model_type in ['DPT_Hybrid', 'DPT_Large']:
                self.transform = midas_transforms.dpt_transform
            else:
                self.transform = midas_transforms.small_transform
            
            self.model.to(self.device)
            self.model.eval()
            
            self.logger.info(f"Loaded MiDaS model: {model_type} on {self.device}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading MiDaS model: {e}")
            return False
    
    def estimate_depth(self, frame: np.ndarray) -> Tuple[Optional[np.ndarray], float]:
        """
        Estimate depth from a frame.
        
        Args:
            frame: Input BGR image
            
        Returns:
            Tuple of (depth_map, inference_time)
        """
        if self.model is None:
            self.logger.error("Model not loaded")
            return None, 0.0
        
        try:
            import time
            start_time = time.time()
            
            # Convert BGR to RGB
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Apply transforms
            input_batch = self.transform(img).to(self.device)
            
            # Inference
            with torch.no_grad():
                prediction = self.model(input_batch)
                
                # Interpolate to original size
                prediction = torch.nn.functional.interpolate(
                    prediction.unsqueeze(1),
                    size=img.shape[:2],
                    mode='bicubic',
                    align_corners=False
                ).squeeze()
            
            # Convert to numpy
            depth_map = prediction.cpu().numpy()
            
            # Normalize to 0-1 range for visualization and processing
            depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min() + 1e-8)
            
            # Apply output scaling if needed
            if self.output_scale != 1.0:
                new_size = (int(depth_map.shape[1] * self.output_scale),
                           int(depth_map.shape[0] * self.output_scale))
                depth_map = cv2.resize(depth_map, new_size)
            
            inference_time = time.time() - start_time
            
            return depth_map, inference_time
            
        except Exception as e:
            self.logger.error(f"Error estimating depth: {e}")
            return None, 0.0
    
    def get_depth_at_point(self, depth_map: np.ndarray, x: int, y: int, radius: int = 5) -> float:
        """
        Get average depth value at a specific point.
        
        Args:
            depth_map: Depth map array
            x: X coordinate
            y: Y coordinate
            radius: Radius for averaging
            
        Returns:
            Average depth value
        """
        if depth_map is None:
            return 0.0
        
        h, w = depth_map.shape
        x = max(radius, min(x, w - radius))
        y = max(radius, min(y, h - radius))
        
        region = depth_map[y-radius:y+radius+1, x-radius:x+radius+1]
        return np.mean(region)
    
    def visualize_depth(self, depth_map: np.ndarray) -> np.ndarray:
        """
        Create a colored visualization of the depth map.
        
        Args:
            depth_map: Depth map array
            
        Returns:
            Colored depth visualization (BGR)
        """
        if depth_map is None:
            return None
        
        # Normalize to 0-255
        depth_colored = (depth_map * 255).astype(np.uint8)
        
        # Apply colormap
        depth_colored = cv2.applyColorMap(depth_colored, cv2.COLORMAP_MAGMA)
        
        return depth_colored
