"""Monocular depth estimation using Depth Anything V2 or MiDaS 3.1."""

import torch
import cv2
import numpy as np
import logging
from typing import Tuple, Optional, Dict

from .scale_calibrator import DepthScaleCalibrator, CameraIntrinsics


class DepthEstimator:
    """
    Monocular depth estimator supporting multiple models.
    
    Provides dense relative depth estimation for near-field obstacle awareness.
    Includes scale calibration for converting relative depth to metric distance.
    
    Supported models:
    - depth_anything_v2_vits (Depth Anything V2 - lightest/fastest)
    - depth_anything_v2_vitb (Depth Anything V2 - medium)
    - depth_anything_v2_vitl (Depth Anything V2 - largest/slowest)
    - midas_small (MiDaS 3.1 - fastest, lightweight for real-time)
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
        self.input_size = config.get('input_size', (518, 518))
        self.output_scale = config.get('output_scale', 0.5)
        self.midas_transform = None  # For MiDaS preprocessing
        
        # Initialize scale calibrator
        self.use_metric_calibration = config.get('use_metric_calibration', True)
        if self.use_metric_calibration:
            self.calibrator = DepthScaleCalibrator(config)
            self.logger.info("Metric depth calibration enabled")
        else:
            self.calibrator = None
            self.logger.info("Using relative depth only (no metric calibration)")

        
    def load_model(self) -> bool:
        """
        Load depth estimation model (Depth Anything V2 or MiDaS).
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            # Check if MiDaS model (midas_* or dpt_*)
            if self.model_type.startswith('midas') or self.model_type.startswith('dpt_'):
                return self._load_midas_model()
            else:
                return self._load_depth_anything_model()
                
        except Exception as e:
            self.logger.error(f"Error loading depth model: {e}", exc_info=True)
            return False
    
    def _load_midas_model(self) -> bool:
        """Load MiDaS DPT model - uses torch.hub to download working weights."""
        try:
            import torch
            
            # Map config model type to torch.hub model name
            model_map = {
                'midas_small': 'MiDaS_small',  # Fastest, good for real-time
                'dpt_swin2_tiny_256': 'DPT_SwinV2_T_256',  # Swin V2 Tiny - good balance
                'dpt_swin2_base_384': 'DPT_SwinV2_B_384',  # Swin V2 Base
                'dpt_swin2_large_384': 'DPT_SwinV2_L_384',  # Swin V2 Large
                'dpt_hybrid': 'DPT_Hybrid',  # DPT with ViT hybrid backbone
                'dpt_large': 'DPT_Large',  # DPT Large
            }
            
            # Use model type from config, default to Swin V2 Tiny
            hub_model_name = model_map.get(self.model_type, 'DPT_SwinV2_T_256')
            
            self.logger.info(f"Loading MiDaS model: {hub_model_name}")
            self.logger.info("Downloading weights from torch.hub (this ensures compatibility)...")
            
            # Load model from torch.hub - downloads working pre-trained weights
            self.model = torch.hub.load("intel-isl/MiDaS", hub_model_name, trust_repo=True)
            
            # Load transforms
            midas_transforms = torch.hub.load("intel-isl/MiDAS", "transforms", trust_repo=True)
            
            # Select appropriate transform based on model
            if hub_model_name == 'MiDaS_small':
                self.midas_transform = midas_transforms.small_transform
            elif 'SwinV2_T_256' in hub_model_name or 'Swin' in hub_model_name and '256' in hub_model_name:
                # Swin 256 models use swin256_transform if available
                if hasattr(midas_transforms, 'swin256_transform'):
                    self.midas_transform = midas_transforms.swin256_transform
                else:
                    self.midas_transform = midas_transforms.small_transform
            elif 'Swin' in hub_model_name:
                # Other Swin models use swin384_transform if available
                if hasattr(midas_transforms, 'swin384_transform'):
                    self.midas_transform = midas_transforms.swin384_transform
                else:
                    self.midas_transform = midas_transforms.dpt_transform
            else:
                # DPT models use dpt_transform
                self.midas_transform = midas_transforms.dpt_transform
            
            # Move to device and set to eval mode
            self.model.to(self.device)
            self.model.eval()
            
            # Log model information
            self.logger.info("=" * 60)
            self.logger.info(f"MiDaS Model: {hub_model_name}")
            self.logger.info(f"Device: {self.device}")
            if self.device == 'cuda':
                self.logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
                self.logger.info(f"CUDA version: {torch.version.cuda}")
            self.logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading MiDaS model: {e}", exc_info=True)
            return False
    
    def _load_depth_anything_model(self) -> bool:
        """Load Depth Anything V2 model."""
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
            
            # Route to appropriate inference method (MiDaS for midas_* and dpt_*)
            if self.model_type.startswith('midas') or self.model_type.startswith('dpt_'):
                depth_map = self._estimate_depth_midas(frame)
            else:
                depth_map = self._estimate_depth_depth_anything(frame)
            
            inference_time = time.time() - start_time
            
            if depth_map is None:
                return None, 0.0
            
            # Apply output scaling if needed
            if self.output_scale != 1.0:
                new_size = (int(depth_map.shape[1] * self.output_scale),
                           int(depth_map.shape[0] * self.output_scale))
                depth_map = cv2.resize(depth_map, new_size)
            
            return depth_map, inference_time
            
        except Exception as e:
            self.logger.error(f"Error estimating depth: {e}", exc_info=True)
            return None, 0.0
    
    def _estimate_depth_midas(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Estimate depth using MiDaS model."""
        try:
            import torch
            
            # Convert BGR to RGB
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Apply MiDaS transform
            input_batch = self.midas_transform(img_rgb).to(self.device)
            
            # Inference
            with torch.no_grad():
                prediction = self.model(input_batch)
                
                # Resize to original resolution
                prediction = torch.nn.functional.interpolate(
                    prediction.unsqueeze(1),
                    size=img_rgb.shape[:2],
                    mode="bicubic",
                    align_corners=False,
                ).squeeze()
            
            # Convert to numpy
            depth_map = prediction.cpu().numpy()
            
            # Normalize to 0-1 range
            depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min() + 1e-8)
            
            return depth_map
            
        except Exception as e:
            self.logger.error(f"MiDaS inference error: {e}", exc_info=True)
            return None
    
    def _estimate_depth_depth_anything(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Estimate depth using Depth Anything V2 model."""
        try:
            # Resize input to 480p (640x480) for faster processing
            resized_frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_LINEAR)
            
            # Depth Anything V2 inference - takes BGR directly
            depth_map = self.model.infer_image(resized_frame)
            
            # Normalize to 0-1 range
            depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min() + 1e-8)
            
            return depth_map
            
        except Exception as e:
            self.logger.error(f"Depth Anything V2 inference error: {e}", exc_info=True)
            return None
    
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
    
    def get_metric_depth(
        self,
        depth_relative: np.ndarray,
        telemetry: Optional[Dict[str, float]] = None
    ) -> np.ndarray:
        """
        Convert relative depth to metric depth using calibration
        
        Args:
            depth_relative: Relative depth map (0=far, 1=close)
            telemetry: Telemetry data with altitude, pitch, roll for calibration
            
        Returns:
            Metric depth map in meters
        """
        if self.calibrator is None:
            self.logger.warning("Calibrator not initialized - using fallback conversion")
            # Fallback: simple inverse mapping
            return 10.0 - (depth_relative * 9.5)
        
        # Calibrate if telemetry available
        if telemetry is not None:
            self.calibrator.calibrate_from_telemetry(depth_relative, telemetry)
        
        # Convert to metric
        return self.calibrator.relative_to_metric(depth_relative)
    
    def get_calibration_status(self) -> Dict[str, any]:
        """Get calibration status and parameters"""
        if self.calibrator is None:
            return {'enabled': False}
        
        status = self.calibrator.get_calibration_status()
        status['enabled'] = True
        return status
