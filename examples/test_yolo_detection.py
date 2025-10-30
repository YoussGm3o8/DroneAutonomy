"""Example script for testing YOLO detection."""

import sys
import cv2
import torch
sys.path.insert(0, '/home/runner/work/DroneAutonomy/DroneAutonomy/src')

from drone_autonomy.detection.yolo_detector import YOLODetector
from drone_autonomy.utils.logger import setup_logging


def main():
    """Test YOLO detection on webcam."""
    print("=" * 80)
    print("DroneAutonomy - YOLO Detection Test")
    print("=" * 80)
    print()
    print("Testing YOLO object detection.")
    print("Press 'q' to quit.")
    print()
    
    # Setup logging
    setup_logging()
    
    # Configuration for YOLO detection
    config = {
        'yolo_model': 'yolov8n.pt',
        'confidence_threshold': 0.5,
        'nms_threshold': 0.4,
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'use_tensorrt': False,
        'classes': None  # Detect all classes
    }
    
    print(f"Using device: {config['device']}")
    
    # Create detector
    detector = YOLODetector(config)
    
    print("Loading YOLO model...")
    if not detector.load_model():
        print("Error: Failed to load YOLO model")
        return 1
    
    print("Model loaded successfully")
    
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
            
            # Detect objects
            detections, inference_time = detector.detect(frame)
            
            # Draw results
            output = detector.draw_detections(frame, detections)
            
            # Display info
            det_info = ', '.join([f"{d['class_name']}({d['confidence']:.2f})" for d in detections[:3]])
            info = f"Objects: {len(detections)} | Time: {inference_time*1000:.1f}ms | FPS: {1.0/inference_time:.1f}"
            cv2.putText(output, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            if det_info:
                cv2.putText(output, det_info, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Show results
            cv2.imshow('YOLO Detection', output)
            
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
