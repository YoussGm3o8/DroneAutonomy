"""
Example: Depth Model Comparison

Compares Depth Anything V2 and MiDaS 3.1 models on the same input.
Shows performance and quality differences between models.
"""

import cv2
import numpy as np
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.drone_autonomy.depth import DepthEstimator


def compare_depth_models(image_path: str = None):
    """Compare different depth estimation models."""
    
    print("=" * 60)
    print("Depth Model Comparison")
    print("=" * 60)
    
    # Initialize webcam or load image
    if image_path:
        frame = cv2.imread(image_path)
        if frame is None:
            print(f"Error: Could not load image {image_path}")
            return
        print(f"Using image: {image_path}")
    else:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open webcam")
            return
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read from webcam")
            return
        cap.release()
        print("Using webcam frame")
    
    print(f"Input resolution: {frame.shape[1]}x{frame.shape[0]}")
    print()
    
    # Define models to test
    models = [
        {
            'name': 'Depth Anything V2 (ViT-S)',
            'config': {
                'model': 'depth_anything_v2_vits',
                'device': 'cuda',
                'input_size': [640, 480],
                'output_scale': 1.0
            }
        },
        {
            'name': 'MiDaS 3.1 Small (Fastest)',
            'config': {
                'model': 'midas_small',
                'device': 'cuda',
                'input_size': [640, 480],
                'output_scale': 1.0
            }
        }
    ]
    
    results = []
    
    # Test each model
    for model_info in models:
        print(f"Testing: {model_info['name']}")
        print("-" * 60)
        
        try:
            # Create estimator
            estimator = DepthEstimator(model_info['config'])
            
            # Load model
            load_start = time.time()
            if not estimator.load_model():
                print(f"✗ Failed to load model\n")
                continue
            load_time = time.time() - load_start
            print(f"  Load time: {load_time:.2f}s")
            
            # Warm up (first inference is slower)
            print("  Warming up...")
            estimator.estimate_depth(frame)
            
            # Run multiple inferences to get average
            num_runs = 10
            print(f"  Running {num_runs} inferences...")
            inference_times = []
            
            for i in range(num_runs):
                depth_map, inference_time = estimator.estimate_depth(frame)
                inference_times.append(inference_time)
            
            avg_time = np.mean(inference_times)
            std_time = np.std(inference_times)
            fps = 1.0 / avg_time if avg_time > 0 else 0
            
            print(f"  Avg inference: {avg_time*1000:.1f}ms (±{std_time*1000:.1f}ms)")
            print(f"  Est. FPS: {fps:.1f}")
            print(f"  Output shape: {depth_map.shape}")
            
            # Visualize depth
            depth_colored = estimator.visualize_depth(depth_map)
            
            # Store results
            results.append({
                'name': model_info['name'],
                'depth_map': depth_map,
                'depth_colored': depth_colored,
                'avg_time': avg_time,
                'fps': fps
            })
            
            print(f"✓ {model_info['name']} completed\n")
            
        except Exception as e:
            print(f"✗ Error testing {model_info['name']}: {e}\n")
            import traceback
            traceback.print_exc()
    
    # Display results side by side
    if results:
        print("=" * 60)
        print("Results Summary")
        print("=" * 60)
        
        for result in results:
            print(f"{result['name']}:")
            print(f"  Inference: {result['avg_time']*1000:.1f}ms")
            print(f"  FPS: {result['fps']:.1f}")
        
        print("\nDisplaying results (press any key to close)...")
        
        # Create comparison visualization
        display_frame = cv2.resize(frame, (640, 480))
        
        rows = []
        for result in results:
            # Resize depth to match display frame
            depth_vis = cv2.resize(result['depth_colored'], (640, 480))
            
            # Add text label
            label_frame = depth_vis.copy()
            cv2.putText(label_frame, result['name'], (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(label_frame, f"{result['fps']:.1f} FPS", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            rows.append(label_frame)
        
        # Combine all
        if len(rows) == 2:
            comparison = np.vstack([
                np.hstack([display_frame, rows[0]]),
                np.hstack([display_frame, rows[1]])
            ])
        else:
            comparison = np.hstack([display_frame] + rows)
        
        cv2.imshow("Depth Model Comparison", comparison)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        # Optionally save result
        output_path = "output/depth_comparison.jpg"
        os.makedirs("output", exist_ok=True)
        cv2.imwrite(output_path, comparison)
        print(f"\n✓ Saved comparison to {output_path}")
    
    else:
        print("No results to display")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare depth estimation models")
    parser.add_argument('--image', type=str, default=None,
                       help='Path to input image (uses webcam if not provided)')
    
    args = parser.parse_args()
    
    compare_depth_models(args.image)
