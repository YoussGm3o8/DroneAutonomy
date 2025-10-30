"""Example script for testing depth estimation."""

import sys
import cv2
import torch
sys.path.insert(0, '/home/runner/work/DroneAutonomy/DroneAutonomy/src')

from drone_autonomy.depth.depth_estimator import DepthEstimator
from drone_autonomy.utils.logger import setup_logging


def main():
    """Test depth estimation on webcam."""
    print("=" * 80)
    print("DroneAutonomy - Depth Estimation Test")
    print("=" * 80)
    print()
    print("Testing MiDaS depth estimation.")
    print("Press 'q' to quit.")
    print()
    
    # Setup logging
    setup_logging()
    
    # Configuration for depth estimation
    config = {
        'model': 'MiDaS_small',
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'input_size': (384, 384),
        'output_scale': 0.5
    }
    
    print(f"Using device: {config['device']}")
    
    # Create estimator
    estimator = DepthEstimator(config)
    
    print("Loading MiDaS model...")
    if not estimator.load_model():
        print("Error: Failed to load depth model")
        return 1
    
    print("Model loaded successfully")
    
    # Open camera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Cannot open camera")
        return 1
    
    print("Camera opened successfully. Starting depth estimation...")
    
    try:
        while True:
            # Read frame
            ret, frame = cap.read()
            if not ret:
                break
            
            # Estimate depth
            depth_map, inference_time = estimator.estimate_depth(frame)
            
            if depth_map is not None:
                # Visualize depth
                depth_vis = estimator.visualize_depth(depth_map)
                
                # Display info
                info = f"Inference: {inference_time*1000:.1f}ms | FPS: {1.0/inference_time:.1f}"
                cv2.putText(frame, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Show results
                cv2.imshow('Original', frame)
                cv2.imshow('Depth Map', depth_vis)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
