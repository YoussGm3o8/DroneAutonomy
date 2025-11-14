"""
Depth Anything V2 Small (ViT-S) with TensorRT FP16 - Optimized for RTX 3060 Mobile.

This module wraps the TensorRT-accelerated depth estimator for production use.
For optimal performance, uses the TensorRT implementation directly.
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional, Dict

from .depth_estimator_trt import DepthAnythingV2TensorRT
from .scale_calibrator import DepthScaleCalibrator


class DepthEstimator:
    """
    Depth Anything V2 Small (ViT-S) with TensorRT FP16 acceleration.
    
    Optimized single-model configuration for RTX 3060 Mobile 6GB:
    - Fixed 518×518 network input (DA2 default)
    - TensorRT FP16 for minimal latency (~18-24ms on RTX 3060 Mobile)
    - Upsamples to 1080p for display/processing
    - Expected: ≥40-55 fps at 518 input before upscaling overhead
    
    Only model: depth_anything_v2_vits_tensorrt_fp16
    """
    
    def __init__(self, config: dict):
        """
        Initialize depth estimator.
        
        Args:
            config: Depth estimation configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Get model type from config (vits or vitb)
        model_name = config.get('model', 'depth_anything_v2_vits_tensorrt_fp16')
        
        # Initialize TensorRT estimator
        try:
            self.model = DepthAnythingV2TensorRT(config)
            # Expose model_type for GUI detection
            self.model_type = self.model.model_type
            self.logger.info(f"Initialized Depth Anything V2 {self.model_type.upper()} with TensorRT FP16")
        except Exception as e:
            self.logger.error(f"Failed to initialize TensorRT depth estimator: {e}")
            self.model = None
            self.model_type = None

        
    def load_model(self) -> bool:
        """
        Load TensorRT depth estimation engine.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        if self.model is None:
            self.logger.error("TensorRT depth estimator not initialized")
            return False
        
        return self.model.load_model()
    
    def estimate_depth(self, frame: np.ndarray) -> Tuple[Optional[np.ndarray], float]:
        """
        Estimate depth from a frame using TensorRT.
        
        Args:
            frame: Input BGR image (any size, processed at 518×518, upsampled to config output)
            
        Returns:
            Tuple of (depth_map, inference_time)
        """
        if self.model is None:
            self.logger.error("Model not loaded")
            return None, 0.0
        
        return self.model.estimate_depth(frame)
    
    def get_depth_at_point(self, depth_map: np.ndarray, x: int, y: int, radius: int = 5) -> float:
        """Get average depth value at a specific point."""
        if self.model is None:
            return 0.0
        return self.model.get_depth_at_point(depth_map, x, y, radius)
    
    def visualize_depth(self, depth_map: np.ndarray) -> np.ndarray:
        """Create a colored visualization of the depth map."""
        if self.model is None:
            return None
        return self.model.visualize_depth(depth_map)
    
    def get_metric_depth(
        self,
        depth_relative: np.ndarray,
        telemetry: Optional[Dict[str, float]] = None
    ) -> np.ndarray:
        """Convert relative depth to metric depth using calibration."""
        if self.model is None:
            return 10.0 - (depth_relative * 9.5)
        return self.model.get_metric_depth(depth_relative, telemetry)
    
    def get_calibration_status(self) -> Dict[str, any]:
        """Get calibration status and parameters."""
        if self.model is None:
            return {'enabled': False}
        return self.model.get_calibration_status()
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get TensorRT inference performance statistics."""
        if self.model is None:
            return {'avg_ms': 0.0, 'min_ms': 0.0, 'max_ms': 0.0, 'avg_fps': 0.0}
        return self.model.get_performance_stats()
