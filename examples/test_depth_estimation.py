"""Example script for testing depth estimation."""

import sys
import os
import cv2
import torch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from drone_autonomy.depth.depth_estimator import DepthEstimator
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
        print(f"Pipeline: {gstreamer_pipeline[:80]}...")
        
        cap = cv2.VideoCapture(gstreamer_pipeline, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            # Verify we can actually read a frame
            ret, frame = cap.read()
            if ret and frame is not None:
                print("✓ Successfully connected to drone camera!")
                return cap, "Drone Camera (GStreamer)"
            else:
                print("✗ Drone camera opened but cannot read frames")
                cap.release()
        else:
            print("✗ Failed to open drone camera")
    
    # Fallback to webcam
    print(f"\nAttempting to open webcam (ID: {camera_id})...")
    cap = cv2.VideoCapture(camera_id)
    if cap.isOpened():
        # Verify we can read a frame
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"✓ Successfully opened webcam {camera_id}")
            return cap, f"Webcam {camera_id}"
        else:
            print(f"✗ Webcam {camera_id} opened but cannot read frames")
            cap.release()
    else:
        print(f"✗ Failed to open webcam {camera_id}")
    
    return None, None


def main():
    """Test depth estimation on drone camera or webcam."""
    print("=" * 80)
    print("DroneAutonomy - Depth Estimation Test")
    print("=" * 80)
    print()
    print("Testing MiDaS depth estimation.")
    print("Will try drone camera first, then fallback to webcam.")
    print("Press 'q' to quit.")
    print()
    
    # Setup logging
    setup_logging()
    
    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'default_config.yaml')
    config_obj = Config(config_path)
    
    # Get video configuration
    video_config = config_obj.config.get('video', {})
    gstreamer_pipeline = video_config.get('gstreamer_pipeline')
    camera_id = video_config.get('camera_id', 0)
    
    # Configuration for depth estimation
    depth_config = config_obj.config.get('depth', {
        'model': 'MiDaS_small',
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'input_size': (384, 384),
        'output_scale': 0.5
    })
    
    print(f"Using device: {depth_config['device']}")
    print()
    
    # Create estimator
    estimator = DepthEstimator(depth_config)
    
    print("Loading MiDaS model...")
    if not estimator.load_model():
        print("Error: Failed to load depth model")
        return 1
    
    print("✓ Model loaded successfully")
    print()
    
    # Try to open camera (drone first, then webcam)
    cap, source_name = try_open_camera(gstreamer_pipeline, camera_id)
    
    if cap is None:
        print("\nError: Cannot open any camera source")
        print("\nTroubleshooting:")
        print("1. For drone camera:")
        print("   - Verify drone is powered on and streaming")
        print("   - Check network connection to 192.168.1.231")
        print("   - Test RTSP stream: rtsp://192.168.1.231:8554/1")
        print("2. For webcam:")
        print("   - Ensure webcam is connected and not in use by another application")
        print("   - Check device manager for camera devices")
        return 1
    
    print(f"\n{'='*80}")
    print(f"Using camera source: {source_name}")
    print(f"{'='*80}\n")
    print("Starting depth estimation...")
    
    frame_count = 0
    total_inference_time = 0
    
    frame_count = 0
    total_inference_time = 0
    
    try:
        while True:
            # Read frame
            ret, frame = cap.read()
            if not ret:
                print("Warning: Cannot read frame from camera")
                break
            
            frame_count += 1
            
            # Estimate depth
            depth_map, inference_time = estimator.estimate_depth(frame)
            total_inference_time += inference_time
            
            if depth_map is not None:
                # Visualize depth
                depth_vis = estimator.visualize_depth(depth_map)
                
                # Calculate average FPS
                avg_fps = frame_count / total_inference_time if total_inference_time > 0 else 0
                
                # Display info on frame
                info_lines = [
                    f"Source: {source_name}",
                    f"Inference: {inference_time*1000:.1f}ms",
                    f"FPS: {1.0/inference_time:.1f}",
                    f"Avg FPS: {avg_fps:.1f}",
                    f"Frame: {frame_count}"
                ]
                
                y_offset = 30
                for i, line in enumerate(info_lines):
                    cv2.putText(frame, line, (10, y_offset + i*30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Add colorbar legend to depth visualization
                cv2.putText(depth_vis, "Near", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(depth_vis, "Far", (10, depth_vis.shape[0]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Show results
                cv2.imshow('Original', frame)
                cv2.imshow('Depth Map', depth_vis)
            
            # Check for quit
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\nQuitting...")
                break
            elif key == ord('s'):
                # Save current frame and depth map
                timestamp = int(cv2.getTickCount())
                cv2.imwrite(f'frame_{timestamp}.jpg', frame)
                cv2.imwrite(f'depth_{timestamp}.jpg', depth_vis)
                print(f"Saved frame_{timestamp}.jpg and depth_{timestamp}.jpg")
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nError during processing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Print statistics
        if frame_count > 0:
            avg_inference = total_inference_time / frame_count
            avg_fps = frame_count / total_inference_time if total_inference_time > 0 else 0
            print(f"\n{'='*80}")
            print("Session Statistics:")
            print(f"  Frames processed: {frame_count}")
            print(f"  Average inference time: {avg_inference*1000:.1f}ms")
            print(f"  Average FPS: {avg_fps:.1f}")
            print(f"  Camera source: {source_name}")
            print(f"{'='*80}")
        
        cap.release()
        cv2.destroyAllWindows()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
