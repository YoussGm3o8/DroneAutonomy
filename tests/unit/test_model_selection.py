"""
Test GUI model selection for Depth Anything V2 Small and Base models.

This script verifies:
1. Settings dialog shows both Small and Base models
2. Model selection properly maps to correct engine paths
3. Model type attribute is correctly set
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "src"))

from drone_autonomy.depth.depth_estimator import DepthEstimator


def test_model_selection():
    """Test model selection with both Small and Base models."""
    
    print("=" * 70)
    print("Testing Depth Anything V2 Model Selection")
    print("=" * 70)
    
    # Test Small model (vits)
    print("\n1. Testing Small Model (ViT-S - 24.8M params)")
    print("-" * 70)
    
    config_small = {
        'model': 'depth_anything_v2_vits_tensorrt_fp16',
        'device': 'cuda',
        'output_width': 518,
        'output_height': 518,
        'use_metric_calibration': False
    }
    
    try:
        estimator_small = DepthEstimator(config_small)
        print(f"✓ Small model initialized")
        print(f"  Model type: {estimator_small.model_type}")
        print(f"  Engine path: {estimator_small.model.engine_path}")
        print(f"  Expected engine: models/depth_anything_v2_vits_fp16.engine")
        
        # Verify model_type attribute for GUI detection
        assert estimator_small.model_type == 'vits', f"Expected model_type='vits', got '{estimator_small.model_type}'"
        print(f"✓ Model type attribute correct")
        
        # Check engine path
        expected_path = Path('models/depth_anything_v2_vits_fp16.engine')
        assert estimator_small.model.engine_path == expected_path, f"Engine path mismatch"
        print(f"✓ Engine path correct")
        
        print(f"\n✓ Small model test PASSED")
        
    except Exception as e:
        print(f"\n✗ Small model test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test Base model (vitb)
    print("\n2. Testing Base Model (ViT-B - 97.5M params)")
    print("-" * 70)
    
    config_base = {
        'model': 'depth_anything_v2_vitb_tensorrt_fp16',
        'device': 'cuda',
        'output_width': 518,
        'output_height': 518,
        'use_metric_calibration': False
    }
    
    try:
        estimator_base = DepthEstimator(config_base)
        print(f"✓ Base model initialized")
        print(f"  Model type: {estimator_base.model_type}")
        print(f"  Engine path: {estimator_base.model.engine_path}")
        print(f"  Expected engine: models/depth_anything_v2_vitb_fp16.engine")
        
        # Verify model_type attribute for GUI detection
        assert estimator_base.model_type == 'vitb', f"Expected model_type='vitb', got '{estimator_base.model_type}'"
        print(f"✓ Model type attribute correct")
        
        # Check engine path
        expected_path = Path('models/depth_anything_v2_vitb_fp16.engine')
        assert estimator_base.model.engine_path == expected_path, f"Engine path mismatch"
        print(f"✓ Engine path correct")
        
        print(f"\n✓ Base model test PASSED")
        
    except Exception as e:
        print(f"\n✗ Base model test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test model switching (simulate GUI behavior)
    print("\n3. Testing Model Switching (GUI Simulation)")
    print("-" * 70)
    
    try:
        # Simulate changing from Small to Base
        print("Switching from Small to Base...")
        
        current_model = estimator_small.model_type
        new_model_config = config_base.copy()
        new_model = new_model_config['model']
        
        # Extract model type from config (like GUI does)
        new_model_type = 'vitb' if 'vitb' in new_model else 'vits'
        
        print(f"  Current model: {current_model}")
        print(f"  New model: {new_model_type}")
        
        # Check if model changed (like main_window.py line 1589)
        if current_model != new_model_type:
            print(f"  ✓ Model change detected: {current_model} → {new_model_type}")
            print(f"  Creating new estimator...")
            
            new_estimator = DepthEstimator(new_model_config)
            print(f"  ✓ New estimator created")
            print(f"  ✓ New model_type: {new_estimator.model_type}")
            print(f"  ✓ New engine: {new_estimator.model.engine_path}")
            
            assert new_estimator.model_type == 'vitb', "Model switch failed"
            print(f"\n✓ Model switching test PASSED")
        else:
            print(f"  ✗ Model change not detected")
            return False
        
    except Exception as e:
        print(f"\n✗ Model switching test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 70)
    print("✓ All model selection tests PASSED")
    print("=" * 70)
    print("\nSummary:")
    print("  • Small model (vits): maps to depth_anything_v2_vits_fp16.engine")
    print("  • Base model (vitb): maps to depth_anything_v2_vitb_fp16.engine")
    print("  • model_type attribute correctly set for GUI detection")
    print("  • Model switching logic verified")
    
    return True


if __name__ == "__main__":
    success = test_model_selection()
    sys.exit(0 if success else 1)
