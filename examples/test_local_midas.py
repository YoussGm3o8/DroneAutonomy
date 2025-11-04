"""
Test local MiDaS DPT_SwinV2_T_256 model loading
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_midas_loading():
    """Test loading the local MiDaS model."""
    print("=" * 60)
    print("Testing Local MiDaS DPT_SwinV2_T_256 Model")
    print("=" * 60)
    
    try:
        import torch
        from src.drone_autonomy.depth import DepthEstimator
        
        # Check if local model file exists
        model_path = os.path.join(os.path.dirname(__file__), '..', 'dpt_swin2_tiny_256.pt')
        model_path = os.path.abspath(model_path)
        
        print(f"\nChecking for local model file...")
        print(f"Path: {model_path}")
        
        if os.path.exists(model_path):
            print(f"✓ Local model file found")
            file_size_mb = os.path.getsize(model_path) / (1024 * 1024)
            print(f"  Size: {file_size_mb:.2f} MB")
        else:
            print(f"✗ Local model file NOT found")
            return False
        
        # Create depth estimator config
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        config = {
            'model': 'midas_small',
            'device': device,
            'input_size': [256, 256],
            'output_scale': 1.0
        }
        
        print(f"\nInitializing DepthEstimator...")
        print(f"  Device: {device}")
        print(f"  Model: {config['model']}")
        
        # Create estimator
        estimator = DepthEstimator(config)
        
        # Load model
        print(f"\nLoading model...")
        if estimator.load_model():
            print(f"\n✓ SUCCESS: Local MiDaS model loaded successfully!")
            print(f"\nModel details:")
            print(f"  Architecture: DPT_SwinV2_T_256")
            print(f"  Input size: 256x256")
            print(f"  Device: {device}")
            print(f"  Memory footprint: ~80-120MB")
            print(f"  Expected FPS: 80-150 (GPU), 15-25 (CPU)")
            return True
        else:
            print(f"\n✗ FAILED: Could not load local MiDaS model")
            return False
            
    except ImportError as e:
        print(f"\n✗ Import error: {e}")
        print("Make sure all dependencies are installed:")
        print("  pip install torch torchvision")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_midas_loading()
    
    print("\n" + "=" * 60)
    if success:
        print("TEST PASSED: Local MiDaS model ready for use")
    else:
        print("TEST FAILED: Check errors above")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
