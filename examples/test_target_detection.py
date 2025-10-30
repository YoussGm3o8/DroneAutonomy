"""Example script for testing target detection only."""

import sys
import os
import cv2
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from drone_autonomy.detection.target_detector import TargetDetector
from drone_autonomy.utils.config import Config
from drone_autonomy.utils.logger import setup_logging


def try_open_camera(gstreamer_pipeline=None, camera_id=0):
    """
    Try to open camera with GStreamer first, then fallback to webcam.
    
    Args:
        gstreamer_pipeline: GStreamer pipeline string for drone camera
        camera_id: Webcam ID to use as fallback
        
    Returns:
        Tuple of (VideoCapture object, source_name) or (None, None) if both fail
    """
    # Try GStreamer pipeline first (drone camera)
    if gstreamer_pipeline:
        print(f"Attempting to connect to drone camera via GStreamer...")
        cap = cv2.VideoCapture(gstreamer_pipeline, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print("✓ Successfully connected to drone camera!")
                return cap, "Drone Camera (GStreamer)"
            else:
                cap.release()
        print("✗ Failed to open drone camera")
    
    # Fallback to webcam
    print(f"Attempting to open webcam (ID: {camera_id})...")
    cap = cv2.VideoCapture(camera_id)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"✓ Successfully opened webcam {camera_id}")
            return cap, f"Webcam {camera_id}"
        else:
            cap.release()
    
    return None, None


def main():
    """Test target detection on drone camera or webcam."""
    print("=" * 80)
    print("DroneAutonomy - Target Detection Test")
    print("=" * 80)
    print()
    print("Testing red circular target detection.")
    print("Will try drone camera first, then fallback to webcam.")
    print("Press 'q' to quit, 's' to save current frame.")
    print()
    
    # Setup logging
    setup_logging()
    
    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'default_config.yaml')
    config_obj = Config(config_path)
    
    # Get configurations
    video_config = config_obj.config.get('video', {})
    gstreamer_pipeline = video_config.get('gstreamer_pipeline')
    camera_id = video_config.get('camera_id', 0)
    
    target_config = config_obj.config.get('target_detection', {
        'hsv_lower': [0, 100, 100],
        'hsv_upper': [10, 255, 255],
        'min_radius': 10,
        'max_radius': 200,
        'circle_threshold': 0.7
    })
    
    # Create detector
    detector = TargetDetector(target_config)
    
    # Try to open camera
    cap, source_name = try_open_camera(gstreamer_pipeline, camera_id)
    
    if cap is None:
        print("\nError: Cannot open any camera source")
        return 1
    
    print(f"\nUsing camera source: {source_name}")
    print("Starting detection...")
    
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
