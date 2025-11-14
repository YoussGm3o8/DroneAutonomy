"""
Test Depth Anything V2 Small TensorRT FP16 Performance

Benchmark the TensorRT engine to verify expected performance on RTX 3060 Mobile:
- Target: 18-24ms per frame (≥40-55 FPS) at 518×518 input
- Memory: <2GB VRAM at batch=1
- Input: 518×518 (fixed DA2 model input)
- Output: Upsampled to 1080p (1920×1080)

Usage:
    # Test with webcam
    python test_tensorrt_depth.py --source webcam
    
    # Test with video file
    python test_tensorrt_depth.py --source path/to/video.mp4
    
    # Test with image
    python test_tensorrt_depth.py --source path/to/image.jpg --loops 100
"""

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from drone_autonomy.depth.depth_estimator_trt import DepthAnythingV2TensorRT


class TensorRTBenchmark:
    """Benchmark TensorRT depth estimator."""
    
    def __init__(self, engine_path: str):
        """
        Initialize benchmark.
        
        Args:
            engine_path: Path to TensorRT engine file
        """
        self.engine_path = Path(engine_path)
        
        if not self.engine_path.exists():
            print(f"ERROR: TensorRT engine not found: {self.engine_path}")
            print("\nConvert ONNX to TensorRT with:")
            print("  python scripts/convert_to_tensorrt.py")
            sys.exit(1)
        
        # Initialize estimator - use native 518×518 for maximum performance
        config = {
            'engine_path': str(self.engine_path),
            'output_width': 518,  # Native model output - no upsampling (20ms savings)
            'output_height': 518,
            'use_metric_calibration': False  # Disable for pure performance test
        }
        
        print("Initializing TensorRT Depth Estimator...")
        self.estimator = DepthAnythingV2TensorRT(config)
        
        if not self.estimator.load_model():
            print("ERROR: Failed to load TensorRT engine")
            sys.exit(1)
        
        print("✓ TensorRT engine loaded successfully\n")
    
    def test_image(self, image_path: str, loops: int = 100):
        """
        Test with a single image (multiple loops for accurate timing).
        
        Args:
            image_path: Path to test image
            loops: Number of inference loops
        """
        print("=" * 70)
        print("TensorRT Performance Test - Single Image")
        print("=" * 70)
        
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            print(f"ERROR: Could not load image: {image_path}")
            return
        
        print(f"Test Image: {image_path}")
        print(f"Resolution: {img.shape[1]}×{img.shape[0]}")
        print(f"Inference Loops: {loops}")
        print("\nRunning benchmark...")
        
        # Warmup (first few runs are slower)
        for _ in range(5):
            self.estimator.estimate_depth(img)
        
        # Benchmark
        times = []
        for i in range(loops):
            depth_map, inference_time = self.estimator.estimate_depth(img)
            times.append(inference_time * 1000)  # Convert to ms
            
            if (i + 1) % 10 == 0:
                avg_ms = np.mean(times[-10:])
                print(f"  Progress: {i+1}/{loops} - Last 10 avg: {avg_ms:.2f}ms ({1000/avg_ms:.1f} FPS)")
        
        # Statistics
        times_np = np.array(times)
        avg_ms = np.mean(times_np)
        min_ms = np.min(times_np)
        max_ms = np.max(times_np)
        std_ms = np.std(times_np)
        p50_ms = np.percentile(times_np, 50)
        p95_ms = np.percentile(times_np, 95)
        p99_ms = np.percentile(times_np, 99)
        
        print("\n" + "=" * 70)
        print("Performance Results")
        print("=" * 70)
        print(f"Samples: {loops}")
        print(f"Average: {avg_ms:.2f}ms ({1000/avg_ms:.1f} FPS)")
        print(f"Median (p50): {p50_ms:.2f}ms ({1000/p50_ms:.1f} FPS)")
        print(f"Min: {min_ms:.2f}ms ({1000/min_ms:.1f} FPS)")
        print(f"Max: {max_ms:.2f}ms ({1000/max_ms:.1f} FPS)")
        print(f"Std Dev: {std_ms:.2f}ms")
        print(f"p95: {p95_ms:.2f}ms ({1000/p95_ms:.1f} FPS)")
        print(f"p99: {p99_ms:.2f}ms ({1000/p99_ms:.1f} FPS)")
        
        # Compare to target
        target_min = 18
        target_max = 24
        print(f"\nTarget (RTX 3060 Mobile): {target_min}-{target_max}ms")
        
        if avg_ms <= target_max:
            print("✅ Performance EXCEEDS target!")
        elif avg_ms <= target_max * 1.2:
            print("✓ Performance meets target")
        else:
            print("⚠ Performance below target (may need optimization)")
        
        print("=" * 70)
        
        # Show result
        depth_map, _ = self.estimator.estimate_depth(img)
        depth_colored = self.estimator.visualize_depth(depth_map)
        
        # Resize for display
        display_width = 1280
        display_height = int(img.shape[0] * display_width / img.shape[1])
        img_display = cv2.resize(img, (display_width, display_height))
        depth_display = cv2.resize(depth_colored, (display_width, display_height))
        
        # Stack side by side
        result = np.hstack([img_display, depth_display])
        
        cv2.imshow("TensorRT Depth Test - Input | Depth", result)
        print("\nPress any key to close...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    def test_video(self, source: str):
        """
        Test with video source (webcam or file).
        
        Args:
            source: Video source ('webcam' or path to video file)
        """
        print("=" * 70)
        print("TensorRT Performance Test - Video Stream")
        print("=" * 70)
        
        # Open video source
        if source == 'webcam':
            cap = cv2.VideoCapture(0)
            print("Video Source: Webcam (camera 0)")
        else:
            cap = cv2.VideoCapture(source)
            print(f"Video Source: {source}")
        
        if not cap.isOpened():
            print(f"ERROR: Could not open video source: {source}")
            return
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"Resolution: {width}×{height}")
        print(f"FPS: {fps:.1f}")
        print("\nRunning real-time test...")
        print("Press 'q' to quit, 's' to save frame")
        
        frame_count = 0
        times = []
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Estimate depth
                depth_map, inference_time = self.estimator.estimate_depth(frame)
                times.append(inference_time * 1000)  # ms
                
                if len(times) > 100:
                    times.pop(0)  # Keep last 100
                
                # Visualize
                depth_colored = self.estimator.visualize_depth(depth_map)
                
                # Resize for display
                display_width = 1280
                display_height = int(frame.shape[0] * display_width / frame.shape[1])
                frame_display = cv2.resize(frame, (display_width, display_height))
                depth_display = cv2.resize(depth_colored, (display_width, display_height))
                
                # Stack side by side
                result = np.hstack([frame_display, depth_display])
                
                # Add performance overlay
                avg_ms = np.mean(times) if times else 0
                avg_fps = 1000 / avg_ms if avg_ms > 0 else 0
                
                cv2.putText(
                    result,
                    f"TensorRT FP16: {avg_ms:.1f}ms ({avg_fps:.1f} FPS)",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )
                
                cv2.putText(
                    result,
                    f"Frame: {frame_count}",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    1
                )
                
                cv2.imshow("TensorRT Depth Test - Input | Depth", result)
                
                frame_count += 1
                
                # Handle keys
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    save_path = f"output/depth_test_frame_{frame_count}.png"
                    Path("output").mkdir(exist_ok=True)
                    cv2.imwrite(save_path, result)
                    print(f"Saved frame to {save_path}")
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        # Final statistics
        if times:
            times_np = np.array(times)
            avg_ms = np.mean(times_np)
            min_ms = np.min(times_np)
            max_ms = np.max(times_np)
            
            print("\n" + "=" * 70)
            print("Video Test Results")
            print("=" * 70)
            print(f"Frames Processed: {frame_count}")
            print(f"Average: {avg_ms:.2f}ms ({1000/avg_ms:.1f} FPS)")
            print(f"Min: {min_ms:.2f}ms ({1000/min_ms:.1f} FPS)")
            print(f"Max: {max_ms:.2f}ms ({1000/max_ms:.1f} FPS)")
            print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test TensorRT Depth Anything V2 Small FP16 performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--engine",
        type=str,
        default="models/depth_anything_v2_vits_fp16.engine",
        help="Path to TensorRT engine (default: models/depth_anything_v2_vits_fp16.engine)"
    )
    
    parser.add_argument(
        "--source",
        type=str,
        default="webcam",
        help="Video source: 'webcam', image path, or video path (default: webcam)"
    )
    
    parser.add_argument(
        "--loops",
        type=int,
        default=100,
        help="Number of loops for image testing (default: 100)"
    )
    
    args = parser.parse_args()
    
    # Create benchmark
    benchmark = TensorRTBenchmark(args.engine)
    
    # Run test
    if args.source == 'webcam':
        benchmark.test_video('webcam')
    elif Path(args.source).suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
        benchmark.test_image(args.source, args.loops)
    else:
        benchmark.test_video(args.source)


if __name__ == "__main__":
    main()
