"""Test MiDaS model loading specifically."""
import sys
sys.path.insert(0, '../src')

from drone_autonomy.depth.depth_estimator import DepthEstimator
import cv2
import numpy as np

print("=" * 80)
print("Testing MiDaS Model Loading")
print("=" * 80)

# Create depth estimator with MiDaS configuration
print("\n1. Initializing DepthEstimator with 'midas' model type...")
config = {
    'model': 'midas',  # Force MiDaS (correct config key)
    'device': 'cuda'
}

try:
    depth_estimator = DepthEstimator(config)
    print("✓ DepthEstimator created")
    
    # Load the model
    print("\n2. Loading MiDaS model...")
    if depth_estimator.load_model():
        print("✓ MiDaS model loaded successfully")
    else:
        print("✗ Failed to load MiDaS model")
        sys.exit(1)
except Exception as e:
    print(f"✗ Failed to create/load DepthEstimator: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test with a dummy image
print("\n3. Testing inference with dummy image...")
dummy_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

try:
    depth_map, inference_time = depth_estimator.estimate_depth(dummy_image)
    if depth_map is not None:
        print(f"✓ Depth estimation successful")
        print(f"  Input shape: {dummy_image.shape}")
        print(f"  Output shape: {depth_map.shape}")
        print(f"  Depth range: [{depth_map.min():.2f}, {depth_map.max():.2f}]")
        print(f"  Inference time: {inference_time*1000:.1f}ms")
    else:
        print("✗ Depth estimation returned None")
        sys.exit(1)
except Exception as e:
    print(f"✗ Depth estimation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verify with webcam if available
print("\n4. Testing with webcam...")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("✗ Webcam not available, skipping real test")
else:
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        depth_map, inference_time = depth_estimator.estimate_depth(frame)
        if depth_map is not None:
            print(f"✓ Webcam frame processed successfully")
            print(f"  Frame shape: {frame.shape}")
            print(f"  Depth shape: {depth_map.shape}")
            print(f"  Inference time: {inference_time*1000:.1f}ms")
            
            # Visualize
            depth_colored = cv2.applyColorMap(
                cv2.normalize(depth_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8),
                cv2.COLORMAP_INFERNO
            )
            
            # Resize depth to match frame size for visualization
            depth_colored_resized = cv2.resize(depth_colored, (frame.shape[1], frame.shape[0]))
            
            combined = np.hstack([frame, depth_colored_resized])
            cv2.imshow('MiDaS Test: RGB | Depth', combined)
            print("\nPress any key to close visualization...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        else:
            print("✗ Depth estimation returned None")
    else:
        print("✗ Failed to capture frame from webcam")

print("\n" + "=" * 80)
print("MiDaS Loading Test Complete!")
print("=" * 80)
