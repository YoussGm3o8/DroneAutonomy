"""
Camera utilities for test scripts.

Provides camera opening functionality with GStreamer and webcam fallback.
"""

import cv2


def try_open_camera(gstreamer_pipeline=None, camera_id=0, verbose=True):
    """
    Try to open camera with GStreamer first, then fallback to webcam.
    
    This function attempts to connect to a camera source in the following order:
    1. GStreamer pipeline (typically for drone RTSP stream)
    2. Webcam using OpenCV VideoCapture with camera_id
    
    Args:
        gstreamer_pipeline: GStreamer pipeline string for drone camera (optional)
        camera_id: Webcam ID to use as fallback (default: 0)
        verbose: Print connection attempts and results (default: True)
        
    Returns:
        Tuple of (VideoCapture object, source_name) or (None, None) if both fail
        
    Example:
        >>> cap, source = try_open_camera(
        ...     gstreamer_pipeline="rtspsrc location=rtsp://192.168.1.231:8554/1 ...",
        ...     camera_id=0
        ... )
        >>> if cap is not None:
        ...     print(f"Opened: {source}")
        ...     ret, frame = cap.read()
    """
    # Try GStreamer pipeline first (drone camera)
    if gstreamer_pipeline:
        if verbose:
            print(f"Attempting to connect to drone camera via GStreamer...")
            # Print truncated pipeline for readability
            pipeline_preview = gstreamer_pipeline[:80] + "..." if len(gstreamer_pipeline) > 80 else gstreamer_pipeline
            print(f"Pipeline: {pipeline_preview}")
        
        try:
            cap = cv2.VideoCapture(gstreamer_pipeline, cv2.CAP_GSTREAMER)
            if cap.isOpened():
                # Verify we can actually read a frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    if verbose:
                        print("✓ Successfully connected to drone camera!")
                        print(f"  Resolution: {frame.shape[1]}x{frame.shape[0]}")
                    return cap, "Drone Camera (GStreamer)"
                else:
                    if verbose:
                        print("✗ Drone camera opened but cannot read frames")
                    cap.release()
            else:
                if verbose:
                    print("✗ Failed to open GStreamer pipeline")
        except Exception as e:
            if verbose:
                print(f"✗ Error opening GStreamer pipeline: {e}")
    
    # Fallback to webcam
    if verbose:
        print(f"\nAttempting to open webcam (ID: {camera_id})...")
    
    try:
        cap = cv2.VideoCapture(camera_id)
        if cap.isOpened():
            # Verify we can read a frame
            ret, frame = cap.read()
            if ret and frame is not None:
                if verbose:
                    print(f"✓ Successfully opened webcam {camera_id}")
                    print(f"  Resolution: {frame.shape[1]}x{frame.shape[0]}")
                return cap, f"Webcam {camera_id}"
            else:
                if verbose:
                    print(f"✗ Webcam {camera_id} opened but cannot read frames")
                cap.release()
        else:
            if verbose:
                print(f"✗ Failed to open webcam {camera_id}")
    except Exception as e:
        if verbose:
            print(f"✗ Error opening webcam: {e}")
    
    # Both failed
    if verbose:
        print("\n" + "="*80)
        print("ERROR: Cannot open any camera source")
        print("="*80)
        print("\nTroubleshooting:")
        print("\n1. For drone camera (GStreamer/RTSP):")
        print("   - Verify drone is powered on and streaming")
        print("   - Check network connection to drone IP address")
        print("   - Test RTSP stream with: gst-launch-1.0 or VLC media player")
        print("   - Ensure GStreamer is installed with RTSP plugins")
        print("\n2. For webcam:")
        print("   - Ensure webcam is connected")
        print("   - Check if webcam is in use by another application")
        print("   - Verify webcam appears in device manager (Windows) or lsusb (Linux)")
        print("   - Try different camera IDs (0, 1, 2, etc.)")
        print("="*80)
    
    return None, None


def get_frame_with_retry(cap, max_retries=3):
    """
    Read frame from camera with retry logic.
    
    Args:
        cap: OpenCV VideoCapture object
        max_retries: Maximum number of retry attempts (default: 3)
        
    Returns:
        Tuple of (success, frame) or (False, None) if all retries fail
    """
    for attempt in range(max_retries):
        ret, frame = cap.read()
        if ret and frame is not None:
            return True, frame
        
        # Brief pause before retry
        import time
        time.sleep(0.05)
    
    return False, None


def set_camera_properties(cap, width=None, height=None, fps=None):
    """
    Set camera properties if supported.
    
    Args:
        cap: OpenCV VideoCapture object
        width: Desired frame width (optional)
        height: Desired frame height (optional)
        fps: Desired frames per second (optional)
        
    Returns:
        Dictionary with actual camera properties set
    """
    actual_props = {}
    
    if width is not None:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        actual_props['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    
    if height is not None:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        actual_props['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    if fps is not None:
        cap.set(cv2.CAP_PROP_FPS, fps)
        actual_props['fps'] = int(cap.get(cv2.CAP_PROP_FPS))
    
    return actual_props
