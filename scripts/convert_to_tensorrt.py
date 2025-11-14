"""
Convert Depth Anything V2 Small ONNX model to TensorRT FP16 engine.

This script converts the ONNX model to an optimized TensorRT engine with FP16 precision
for maximum performance on RTX 3060 Mobile (and other NVIDIA GPUs).

Requirements:
    - TensorRT 8.6+ installed
    - CUDA 11.8 or 12.x
    - ONNX model: depth_anything_v2_vits.onnx

Usage:
    python scripts/convert_to_tensorrt.py [--onnx-path PATH] [--output PATH] [--workspace SIZE]

Expected Performance:
    - RTX 3060 Mobile: 18-24ms per frame (≥40-55 FPS) at 518×518 input
    - RTX 4090: ~3ms per frame at 720p input
    
Based on official TensorRT Depth Anything V2 implementation:
https://github.com/spacewalk01/depth-anything-tensorrt
"""

import argparse
import os
import sys
from pathlib import Path

# Initialize PyTorch CUDA first to avoid CUDA initialization conflicts with TensorRT
try:
    import torch
    if torch.cuda.is_available():
        # This initializes CUDA runtime properly for TensorRT
        _dummy = torch.zeros(1).cuda()
        print(f"✓ CUDA initialized via PyTorch: {torch.cuda.get_device_name(0)}")
        del _dummy
except Exception as e:
    print(f"⚠ Warning: Could not initialize CUDA via PyTorch: {e}")

try:
    import tensorrt as trt
except ImportError:
    print("ERROR: TensorRT is required!")
    print("Install with:")
    print("  pip install tensorrt")
    print("\nSee: https://docs.nvidia.com/deeplearning/tensorrt/install-guide/")
    sys.exit(1)

# CUDA bindings are optional for conversion (only needed for inference)
try:
    import cuda.cuda as cuda_driver
    CUDA_AVAILABLE = True
except ImportError:
    try:
        import pycuda.driver as cuda
        import pycuda.autoinit
        CUDA_AVAILABLE = True
    except ImportError:
        CUDA_AVAILABLE = False
        print("Note: CUDA Python bindings not found (optional for conversion)")
        print("  Install with: pip install cuda-python")


class TensorRTConverter:
    """Convert ONNX model to TensorRT engine with FP16 precision."""
    
    def __init__(self, onnx_path: Path, output_path: Path, workspace_gb: int = 2):
        """
        Initialize converter.
        
        Args:
            onnx_path: Path to ONNX model
            output_path: Path for output TensorRT engine
            workspace_gb: Workspace size in GB (default: 2GB for RTX 3060 Mobile)
        """
        self.onnx_path = onnx_path
        self.output_path = output_path
        self.workspace_gb = workspace_gb
        
        # TensorRT logger
        self.logger = trt.Logger(trt.Logger.INFO)
    
    def build_engine(self) -> bool:
        """
        Build TensorRT engine from ONNX model.
        
        Returns:
            True if successful, False otherwise
        """
        print("=" * 70)
        print("TensorRT Engine Builder - Depth Anything V2 Small (ViT-S)")
        print("=" * 70)
        print(f"ONNX Model: {self.onnx_path}")
        print(f"Output Engine: {self.output_path}")
        print(f"Workspace: {self.workspace_gb}GB")
        print(f"Precision: FP16 (Half Precision)")
        print("=" * 70)
        
        try:
            # Verify ONNX file exists
            if not self.onnx_path.exists():
                print(f"ERROR: ONNX model not found: {self.onnx_path}")
                return False
            
            # Create builder and network
            builder = trt.Builder(self.logger)
            network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
            parser = trt.OnnxParser(network, self.logger)
        except Exception as e:
            print(f"ERROR: Failed to initialize TensorRT: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Parse ONNX model
        print("\n[1/4] Parsing ONNX model...")
        try:
            with open(self.onnx_path, 'rb') as f:
                onnx_data = f.read()
                print(f"  ONNX file size: {len(onnx_data) / (1024*1024):.2f} MB")
                if not parser.parse(onnx_data):
                    print("ERROR: Failed to parse ONNX model")
                    for i in range(parser.num_errors):
                        print(f"  {parser.get_error(i)}")
                    return False
        except Exception as e:
            print(f"ERROR: Exception during ONNX parsing: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("✓ ONNX model parsed successfully")
        
        # Configure builder
        print("\n[2/4] Configuring TensorRT builder...")
        try:
            config = builder.create_builder_config()
            
            # Set workspace size (memory for TensorRT optimization)
            workspace_bytes = self.workspace_gb * (1 << 30)  # GB to bytes
            config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, workspace_bytes)
        except Exception as e:
            print(f"ERROR: Failed to configure builder: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        try:
            # Enable FP16 mode for 2x speedup and half memory usage
            if builder.platform_has_fast_fp16:
                config.set_flag(trt.BuilderFlag.FP16)
                print("✓ FP16 precision enabled (2x speedup, 0.5x memory)")
            else:
                print("⚠ Warning: FP16 not supported on this GPU, using FP32")
            
            # Optimization profile for dynamic shapes (if needed)
            profile = builder.create_optimization_profile()
            
            # Fixed input shape: 1×3×518×518 (NCHW)
            input_shape = (1, 3, 518, 518)
            
            # Get input name from network
            input_name = network.get_input(0).name
            print(f"  Input tensor name: '{input_name}'")
            
            profile.set_shape(
                input_name,
                min=input_shape,
                opt=input_shape,
                max=input_shape
            )
            config.add_optimization_profile(profile)
            
            print(f"✓ Input shape: {input_shape} (NCHW)")
            print(f"✓ Workspace: {self.workspace_gb}GB")
        except Exception as e:
            print(f"ERROR: Failed to configure optimization profile: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Build engine
        print("\n[3/4] Building TensorRT engine (this may take several minutes)...")
        print("Note: First build takes longer as TensorRT profiles GPU kernels")
        
        try:
            serialized_engine = builder.build_serialized_network(network, config)
        except Exception as e:
            print(f"ERROR: Exception during engine build: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        if serialized_engine is None:
            print("ERROR: Failed to build TensorRT engine (returned None)")
            print("This usually means:")
            print("  1. Insufficient GPU memory")
            print("  2. Incompatible ONNX operators")
            print("  3. TensorRT version mismatch")
            return False
        
        print("✓ Engine built successfully")
        
        # Save engine to file
        print(f"\n[4/4] Saving engine to {self.output_path}...")
        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.output_path, 'wb') as f:
                f.write(serialized_engine)
            
            engine_size_mb = self.output_path.stat().st_size / (1024 * 1024)
            print(f"✓ Engine saved ({engine_size_mb:.2f} MB)")
        except Exception as e:
            print(f"ERROR: Failed to save engine: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Print summary
        print("\n" + "=" * 70)
        print("✅ TensorRT Engine Build Complete!")
        print("=" * 70)
        print(f"Engine: {self.output_path}")
        print(f"Size: {engine_size_mb:.2f} MB")
        print(f"Precision: FP16")
        print(f"Input: 1×3×518×518 (NCHW)")
        print("\nExpected Performance on RTX 3060 Mobile:")
        print("  • Inference: 18-24ms per frame")
        print("  • Throughput: ≥40-55 FPS at 518×518 input")
        print("  • VRAM Usage: <2GB at batch=1")
        print("\nNext Steps:")
        print(f"  1. Test with: python test_tensorrt_depth.py")
        print(f"  2. Update config files to use: {self.output_path}")
        print("=" * 70)
        
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert Depth Anything V2 Small ONNX to TensorRT FP16 engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--onnx-path",
        type=str,
        default="depth_anything_v2_vits.onnx",
        help="Path to ONNX model (default: depth_anything_v2_vits.onnx)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="models/depth_anything_v2_vits_fp16.engine",
        help="Output path for TensorRT engine (default: models/depth_anything_v2_vits_fp16.engine)"
    )
    
    parser.add_argument(
        "--workspace",
        type=int,
        default=2,
        help="Workspace size in GB (default: 2GB for RTX 3060 Mobile 6GB)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose TensorRT logging"
    )
    
    args = parser.parse_args()
    
    # Convert paths
    onnx_path = Path(args.onnx_path)
    output_path = Path(args.output)
    
    # Create converter
    converter = TensorRTConverter(
        onnx_path=onnx_path,
        output_path=output_path,
        workspace_gb=args.workspace
    )
    
    # Build engine
    success = converter.build_engine()
    
    if success:
        print("\n✅ Conversion successful!")
        sys.exit(0)
    else:
        print("\n❌ Conversion failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
