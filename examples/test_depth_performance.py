"""
Test Depth Anything V2 vs MiDaS Performance

Compares inference speed and quality between Depth Anything V2 (vits) and MiDaS Small.
"""

import sys
import time
import cv2
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from drone_autonomy.depth.depth_estimator import DepthEstimator


def test_depth_model(model_name: str, test_image_path: str, num_iterations: int = 10):
    """Test depth estimation performance"""
    print(f"\n{'=' * 80}")
    print(f"Testing Model: {model_name}")
    print(f"{'=' * 80}\n")
    
    # Create config
    config = {
        'model': model_name,
        'device': 'cuda',
        'input_size': [518, 518] if 'depth_anything' in model_name else [384, 384],
        'output_scale': 1.0  # Full resolution for testing
    }
    
    # Initialize estimator
    estimator = DepthEstimator(config)
    
    print(f"Loading model: {model_name}...")
    if not estimator.load_model():
        print(f"❌ Failed to load model: {model_name}")
        return None
    
    print(f"✓ Model loaded successfully")
    print(f"  Device config: {estimator.device}")
    print(f"  Model device: {next(estimator.model.parameters()).device}\n")
    
    # Load test image
    if test_image_path:
        frame = cv2.imread(test_image_path)
        if frame is None:
            print(f"❌ Could not load test image: {test_image_path}")
            return None
    else:
        # Create synthetic test image (1920x1080)
        print("No test image provided, creating synthetic 1920x1080 test image...")
        frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
    
    print(f"Test image size: {frame.shape[1]}x{frame.shape[0]}")
    print(f"Running {num_iterations} iterations for timing...\n")
    
    # Warm-up run
    _, _ = estimator.estimate_depth(frame)
    
    # Timed runs
    times = []
    for i in range(num_iterations):
        depth_map, inference_time = estimator.estimate_depth(frame)
        times.append(inference_time * 1000)  # Convert to ms
        
        if (i + 1) % 5 == 0:
            print(f"  Iteration {i+1}/{num_iterations}: {inference_time*1000:.2f}ms")
    
    # Calculate statistics
    avg_time = np.mean(times)
    std_time = np.std(times)
    min_time = np.min(times)
    max_time = np.max(times)
    
    print(f"\nResults for {model_name}:")
    print(f"  Average time: {avg_time:.2f}ms (±{std_time:.2f}ms)")
    print(f"  Min time: {min_time:.2f}ms")
    print(f"  Max time: {max_time:.2f}ms")
    print(f"  FPS: {1000/avg_time:.2f}")
    
    # Save visualization
    if depth_map is not None:
        depth_vis = estimator.visualize_depth(depth_map)
        output_path = f"depth_test_{model_name.replace('_', '-')}.png"
        cv2.imwrite(output_path, depth_vis)
        print(f"  Depth visualization saved: {output_path}")
    
    return {
        'model': model_name,
        'avg_time_ms': avg_time,
        'std_time_ms': std_time,
        'min_time_ms': min_time,
        'max_time_ms': max_time,
        'fps': 1000 / avg_time
    }


def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Depth Anything V2 vs MiDaS')
    parser.add_argument('--image', type=str, help='Path to test image (optional)')
    parser.add_argument('--iterations', type=int, default=10, help='Number of test iterations')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Depth Estimation Performance Comparison")
    print("Depth Anything V2 (vits) vs MiDaS Small")
    print("=" * 80)
    
    # Test both models
    models = [
        'depth_anything_v2_vits',  # Fastest Depth Anything V2
        'MiDaS_small'  # Original MiDaS small
    ]
    
    results = []
    for model in models:
        try:
            result = test_depth_model(model, args.image, args.iterations)
            if result:
                results.append(result)
        except Exception as e:
            print(f"\n❌ Error testing {model}: {e}\n")
    
    # Comparison summary
    if len(results) == 2:
        print("\n" + "=" * 80)
        print("COMPARISON SUMMARY")
        print("=" * 80 + "\n")
        
        da_result = results[0]
        midas_result = results[1]
        
        print(f"Depth Anything V2 (vits):")
        print(f"  Average: {da_result['avg_time_ms']:.2f}ms | FPS: {da_result['fps']:.2f}")
        print()
        print(f"MiDaS Small:")
        print(f"  Average: {midas_result['avg_time_ms']:.2f}ms | FPS: {midas_result['fps']:.2f}")
        print()
        
        # Calculate speedup
        speedup = midas_result['avg_time_ms'] / da_result['avg_time_ms']
        fps_improvement = da_result['fps'] - midas_result['fps']
        
        if da_result['avg_time_ms'] < midas_result['avg_time_ms']:
            print(f"🎉 Depth Anything V2 is {speedup:.2f}x FASTER than MiDaS!")
            print(f"   FPS improvement: +{fps_improvement:.2f} FPS")
        else:
            print(f"⚠️  Depth Anything V2 is {1/speedup:.2f}x SLOWER than MiDaS")
            print(f"   FPS difference: {fps_improvement:.2f} FPS")
        
        print()
        print("Note: Depth Anything V2 generally provides better quality depth maps")
        print("      even when performance is similar to MiDaS.")
    
    print("\n" + "=" * 80)
    print("Test complete!")
    print("=" * 80)


if __name__ == '__main__':
    sys.exit(main())
