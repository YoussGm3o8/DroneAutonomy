"""Monocular depth estimation using Depth Anything V2."""

import torch
import cv2
import numpy as np
import logging
from typing import Tuple, Optional


class DepthEstimator:
    """
    Monocular depth estimator using Depth Anything V2.
    
    Provides dense relative depth estimation for near-field obstacle awareness.
    Uses the lightest and fastest Depth Anything V2 model (vits) by default.
    
    Supported models:
    - depth_anything_v2_vits (lightest/fastest - RECOMMENDED)
    - depth_anything_v2_vitb (medium)
    - depth_anything_v2_vitl (largest/slowest)
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
        self.model_type = config.get('model', 'depth_anything_v2_vits')  # Default to lightest
        self.device = config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu')
        self.input_size = config.get('input_size', (518, 518))  # Default for Depth Anything V2
        self.output_scale = config.get('output_scale', 0.5)
        
    def load_model(self) -> bool:
        """
        Load Depth Anything V2 model.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            from depth_anything_v2.dpt import DepthAnythingV2
            
            # Model configurations
            model_configs = {
                'depth_anything_v2_vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
                'depth_anything_v2_vitb': {'encoder': 'vitb', 'features': 128, 'out_channels': [96, 192, 384, 768]},
                'depth_anything_v2_vitl': {'encoder': 'vitl', 'features': 256, 'out_channels': [256, 512, 1024, 1024]},
            }
            
            if self.model_type not in model_configs:
                self.logger.warning(f"Unknown Depth Anything V2 model: {self.model_type}, using vits (fastest)")
                self.model_type = 'depth_anything_v2_vits'
            
            config = model_configs[self.model_type]
            encoder = config['encoder']
            
            self.model = DepthAnythingV2(**config)
            
            # Load pretrained weights from Hugging Face
            try:
                # Map to Hugging Face model names
                hf_model_map = {
                    'depth_anything_v2_vits': 'depth-anything/Depth-Anything-V2-Small',
                    'depth_anything_v2_vitb': 'depth-anything/Depth-Anything-V2-Base',
                    'depth_anything_v2_vitl': 'depth-anything/Depth-Anything-V2-Large',
                }
                
                hf_model_name = hf_model_map.get(self.model_type)
                
                if hf_model_name:
                    # Try loading from Hugging Face Hub
                    from huggingface_hub import hf_hub_download
                    
                    # Download model weights
                    checkpoint_path = hf_hub_download(
                        repo_id=hf_model_name,
                        filename=f"depth_anything_v2_{encoder}.pth"
                    )
                    
                    # Load directly to target device for efficiency
                    state_dict = torch.load(checkpoint_path, map_location=self.device, weights_only=True)
                    self.model.load_state_dict(state_dict)
                    self.logger.info(f"Loaded Depth Anything V2 from Hugging Face: {hf_model_name}")
                else:
                    self.logger.warning(f"No Hugging Face model mapping for {self.model_type}")
            
            except Exception as e:
                self.logger.warning(f"Could not load pretrained weights from Hugging Face: {e}")
                self.logger.info("Model will be used without pretrained weights (random init)")
            
            # Ensure model is on correct device and in eval mode
            self.model.to(self.device)
            self.model.eval()
            
            self.logger.info("=" * 60)
            self.logger.info(f"Depth Anything V2: {self.model_type}")
            self.logger.info(f"Device: {self.device}")
            if self.device == 'cuda':
                self.logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
                self.logger.info(f"CUDA version: {torch.version.cuda}")
            self.logger.info("=" * 60)
            return True
            
        except ImportError:
            self.logger.error("depth_anything_v2 package not installed. Install with: pip install depth-anything-v2")
            return False
        except Exception as e:
            self.logger.error(f"Error loading Depth Anything V2: {e}", exc_info=True)
            return False
    
    def estimate_depth(self, frame: np.ndarray) -> Tuple[Optional[np.ndarray], float]:
        """
        Estimate depth from a frame using Depth Anything V2.
        
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
            
            # Resize input to 480p (640x480) for faster processing
            original_shape = frame.shape[:2]
            resized_frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_LINEAR)
            
            # Depth Anything V2 inference - takes BGR directly
            depth_map = self.model.infer_image(resized_frame)
            
            # Resize depth map back to original resolution if needed
            # (Usually we keep it at lower resolution for performance)
            # depth_map = cv2.resize(depth_map, (original_shape[1], original_shape[0]), interpolation=cv2.INTER_LINEAR)
            
            # Normalize to 0-1 range
            depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min() + 1e-8)
            
            # Apply output scaling if needed (additional scaling beyond 480p)
            if self.output_scale != 1.0:
                new_size = (int(depth_map.shape[1] * self.output_scale),
                           int(depth_map.shape[0] * self.output_scale))
                depth_map = cv2.resize(depth_map, new_size)
            
            inference_time = time.time() - start_time
            
            return depth_map, inference_time
            
        except Exception as e:
            self.logger.error(f"Error estimating depth: {e}", exc_info=True)
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
