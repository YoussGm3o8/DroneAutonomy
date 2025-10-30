"""Example script for testing target detection only."""

import sys
import cv2
sys.path.insert(0, '/home/runner/work/DroneAutonomy/DroneAutonomy/src')

from drone_autonomy.detection.target_detector import TargetDetector
from drone_autonomy.utils.logger import setup_logging


def main():
    """Test target detection on webcam or test image."""
    print("=" * 80)
    print("DroneAutonomy - Target Detection Test")
    print("=" * 80)
    print()
    print("Testing red circular target detection.")
    print("Press 'q' to quit.")
    print()
    
    # Setup logging
    setup_logging()
    
    # Configuration for target detection
    config = {
        'hsv_lower': [0, 100, 100],
        'hsv_upper': [10, 255, 255],
        'min_radius': 10,
        'max_radius': 200,
        'circle_threshold': 0.7
    }
    
    # Create detector
    detector = TargetDetector(config)
    
    # Open camera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Cannot open camera")
        return 1
    
    print("Camera opened successfully. Starting detection...")
    
    try:
        while True:
            # Read frame
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detect targets
            targets, process_time = detector.detect(frame)
            
            # Draw results
            output = detector.draw_targets(frame, targets)
            
            # Get mask for visualization
            mask = detector.get_mask(frame)
            mask_color = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            
            # Display info
            info = f"Targets: {len(targets)} | Time: {process_time*1000:.1f}ms"
            cv2.putText(output, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Show results
            cv2.imshow('Target Detection', output)
            cv2.imshow('Red Mask', mask_color)
            
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
