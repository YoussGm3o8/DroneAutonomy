"""Example script for camera calibration."""

import sys
import cv2
import numpy as np
from pathlib import Path
sys.path.insert(0, '/home/runner/work/DroneAutonomy/DroneAutonomy/src')

from drone_autonomy.utils.camera_calibration import CameraCalibration
from drone_autonomy.utils.logger import setup_logging


def capture_calibration_images(output_dir: str, num_images: int = 20):
    """
    Capture calibration images from webcam.
    
    Args:
        output_dir: Directory to save images
        num_images: Number of images to capture
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Cannot open camera")
        return False
    
    print(f"Capturing {num_images} calibration images")
    print("Position chessboard pattern in view and press SPACE to capture")
    print("Press 'q' to quit")
    
    count = 0
    while count < num_images:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Show frame
        display = frame.copy()
        cv2.putText(display, f"Images captured: {count}/{num_images}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(display, "Press SPACE to capture, 'q' to quit",
                   (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow('Calibration', display)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            # Save image
            filename = Path(output_dir) / f"calibration_{count:03d}.png"
            cv2.imwrite(str(filename), frame)
            print(f"Saved {filename}")
            count += 1
        elif key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    return count >= num_images


def main():
    """Main calibration workflow."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Camera calibration utility')
    parser.add_argument('--capture', action='store_true', help='Capture calibration images')
    parser.add_argument('--images', type=str, help='Path to calibration images directory')
    parser.add_argument('--output', type=str, default='config/camera_calibration.json',
                       help='Output calibration file')
    parser.add_argument('--pattern-cols', type=int, default=9, help='Chessboard columns')
    parser.add_argument('--pattern-rows', type=int, default=6, help='Chessboard rows')
    parser.add_argument('--square-size', type=float, default=0.025, help='Square size in meters')
    
    args = parser.parse_args()
    
    setup_logging()
    
    # Capture mode
    if args.capture:
        print("=" * 80)
        print("Camera Calibration - Capture Mode")
        print("=" * 80)
        
        capture_dir = args.images or 'data/calibration_images'
        if capture_calibration_images(capture_dir, num_images=20):
            print(f"\nCaptured images saved to {capture_dir}")
            print(f"Run calibration with: --images {capture_dir}")
        return 0
    
    # Calibration mode
    if not args.images:
        print("Error: Either --capture or --images required")
        return 1
    
    print("=" * 80)
    print("Camera Calibration")
    print("=" * 80)
    print(f"Images directory: {args.images}")
    print(f"Pattern size: {args.pattern_cols}x{args.pattern_rows}")
    print(f"Square size: {args.square_size}m")
    print()
    
    calib = CameraCalibration()
    
    print("Running calibration...")
    success = calib.calibrate_from_chessboard(
        images_path=args.images,
        pattern_size=(args.pattern_cols, args.pattern_rows),
        square_size=args.square_size
    )
    
    if success:
        calib.save_to_file(args.output)
        print(f"\nCalibration saved to {args.output}")
        return 0
    else:
        print("\nCalibration failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
