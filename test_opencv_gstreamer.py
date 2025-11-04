"""
Test OpenCV + GStreamer video reception from Gazebo
"""
import cv2
import time
import numpy as np

def test_opencv_gstreamer():
    print("Testing OpenCV GStreamer reception...")
    
    # GStreamer pipeline (from config)
    pipeline = (
        "udpsrc address=0.0.0.0 port=5600 "
        "caps=\"application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264\" ! "
        "rtpjitterbuffer ! "
        "rtph264depay ! "
        "h264parse ! "
        "avdec_h264 ! "
        "videoconvert ! "
        "video/x-raw,format=BGR ! "
        "appsink drop=true max-buffers=1 sync=false"
    )
    
    print(f"\nPipeline:\n{pipeline}\n")
    
    print("Opening VideoCapture...")
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    
    if not cap.isOpened():
        print("❌ Failed to open VideoCapture")
        return False
    
    print("✅ VideoCapture opened")
    
    # Try to read frames
    print("\nAttempting to read frames...")
    frame_count = 0
    start_time = time.time()
    timeout = 30  # Wait up to 30 seconds for first frame
    
    while time.time() - start_time < timeout:
        ret, frame = cap.read()
        
        if ret and frame is not None:
            frame_count += 1
            print(f"\n🎉 SUCCESS! Frame {frame_count} received!")
            print(f"   Shape: {frame.shape}")
            print(f"   Type: {frame.dtype}")
            print(f"   Size: {frame.nbytes} bytes")
            
            # Save first frame
            if frame_count == 1:
                cv2.imwrite("test_gazebo_frame.jpg", frame)
                print(f"   ✓ Saved to test_gazebo_frame.jpg")
            
            # Show live feed
            cv2.imshow("Gazebo GStreamer Test", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
            if frame_count >= 100:
                print(f"\n✅ Test PASSED - Received {frame_count} frames")
                break
        else:
            # No frame yet
            elapsed = time.time() - start_time
            print(f"\rWaiting for frame... ({elapsed:.1f}s)", end="")
            time.sleep(0.1)
    
    cap.release()
    cv2.destroyAllWindows()
    
    if frame_count == 0:
        print(f"\n\n❌ No frames received after {timeout} seconds")
        print("\nTroubleshooting:")
        print("1. Check Gazebo is running and simulation is PLAYING")
        print("2. Check GStreamer plugin loaded in Gazebo log")
        print("3. Verify UDP data: wsl bash scripts/test_udp_stream.sh")
        print("4. Check firewall allows UDP 5600")
        print("5. Try: wsl bash scripts/start_gazebo_sim.sh")
        return False
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("OpenCV + GStreamer Gazebo Video Test")
    print("="*60)
    print("\nMake sure Gazebo is running with:")
    print("  cmd /c start wsl.exe bash scripts/launch_gazebo_gstreamer.sh")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        success = test_opencv_gstreamer()
        if success:
            print("\n✅ Test COMPLETE!")
        else:
            print("\n❌ Test FAILED")
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
