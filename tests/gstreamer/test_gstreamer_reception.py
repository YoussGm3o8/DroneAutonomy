"""
Test GStreamer video reception from Gazebo
"""
import cv2
import time

def test_gstreamer_reception():
    """Test receiving GStreamer video from Gazebo."""
    print("🎥 Testing GStreamer video reception from Gazebo")
    print("📡 Listening on UDP port 5600...")
    
    # GStreamer pipeline
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
    
    print(f"\n📋 Pipeline:\n{pipeline}\n")
    
    try:
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        
        if not cap.isOpened():
            print("❌ Failed to open GStreamer pipeline")
            print("\nTroubleshooting:")
            print("1. Check if Gazebo is running")
            print("2. Check if GstCameraPlugin loaded (look in Gazebo terminal)")
            print("3. Verify firewall allows UDP 5600")
            print("4. Check Windows IP in SDF file")
            return False
        
        print("✅ GStreamer pipeline opened successfully!")
        print("⏳ Waiting for first frame...")
        
        # Try to read frames
        for i in range(100):  # Try for 10 seconds
            ret, frame = cap.read()
            
            if ret and frame is not None:
                print(f"\n🎉 SUCCESS! Received video frame!")
                print(f"   Frame shape: {frame.shape}")
                print(f"   Resolution: {frame.shape[1]}x{frame.shape[0]}")
                print(f"   Channels: {frame.shape[2]}")
                
                # Save a test frame
                cv2.imwrite("test_gstreamer_frame.jpg", frame)
                print(f"   ✓ Saved test frame to test_gstreamer_frame.jpg")
                
                cap.release()
                return True
            
            time.sleep(0.1)
        
        print("\n⚠️ No frames received after 10 seconds")
        print("\nCheck Gazebo terminal for plugin messages:")
        print("   - 'GstCameraPlugin: Initialized'")
        print("   - 'GstCameraPlugin: Streaming to udp://172.x.x.x:5600'")
        
        cap.release()
        return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure OpenCV is built with GStreamer support:")
        print("   import cv2")
        print("   print(cv2.getBuildInformation())")
        print("   # Look for 'GStreamer: YES'")
        return False

if __name__ == "__main__":
    # Check OpenCV GStreamer support
    print("Checking OpenCV GStreamer support...")
    build_info = cv2.getBuildInformation()
    if "GStreamer" in build_info:
        for line in build_info.split('\n'):
            if "GStreamer" in line:
                print(f"  {line.strip()}")
    else:
        print("  ⚠️ GStreamer info not found in build")
    
    print("\n" + "="*60 + "\n")
    
    success = test_gstreamer_reception()
    
    if success:
        print("\n✅ GStreamer reception test PASSED!")
    else:
        print("\n❌ GStreamer reception test FAILED")
