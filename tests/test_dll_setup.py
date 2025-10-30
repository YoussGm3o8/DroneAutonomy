"""
Test script to verify OpenCV with GStreamer DLL setup.

This script tests that:
1. DLL paths are configured correctly
2. OpenCV can be imported successfully
3. GStreamer backend is available
"""
import sys
import os

def test_dll_setup():
    """Test DLL setup and OpenCV with GStreamer."""
    print("=" * 60)
    print("Testing OpenCV + GStreamer DLL Setup")
    print("=" * 60)
    
    # Test 1: Import drone_autonomy (triggers DLL setup)
    print("\n[1/4] Importing drone_autonomy package...")
    try:
        import drone_autonomy
        print("✓ Successfully imported drone_autonomy")
        print(f"  Version: {drone_autonomy.__version__}")
    except Exception as e:
        print(f"✗ Failed to import drone_autonomy: {e}")
        return False
    
    # Test 2: Import OpenCV
    print("\n[2/4] Importing OpenCV (cv2)...")
    try:
        import cv2
        print("✓ Successfully imported cv2")
        print(f"  OpenCV Version: {cv2.__version__}")
    except Exception as e:
        print(f"✗ Failed to import cv2: {e}")
        return False
    
    # Test 3: Check GStreamer backend
    print("\n[3/4] Checking GStreamer backend...")
    backends = cv2.videoio_registry.getBackends()
    backend_names = [cv2.videoio_registry.getBackendName(b) for b in backends]
    
    print(f"  Available backends: {', '.join(backend_names)}")
    
    if 'GSTREAMER' in backend_names:
        print("✓ GStreamer backend is available!")
    else:
        print("✗ GStreamer backend NOT found")
        print("  This may indicate GStreamer DLLs are not properly loaded")
    
    # Test 4: Verify DLL directories
    print("\n[4/4] Verifying DLL directories...")
    opencv_path = "C:\\opencv\\build\\bin\\Release"
    gstreamer_path = "C:\\gstreamer\\1.0\\msvc_x86_64\\bin"
    
    opencv_exists = os.path.exists(opencv_path)
    gstreamer_exists = os.path.exists(gstreamer_path)
    
    print(f"  OpenCV path exists: {'✓' if opencv_exists else '✗'} {opencv_path}")
    print(f"  GStreamer path exists: {'✓' if gstreamer_exists else '✗'} {gstreamer_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    if opencv_exists and gstreamer_exists and 'GSTREAMER' in backend_names:
        print("✓ All tests passed! OpenCV with GStreamer is ready to use.")
        return True
    else:
        print("⚠ Some tests failed. Please check the setup.")
        if not opencv_exists:
            print("  - OpenCV directory not found at expected location")
        if not gstreamer_exists:
            print("  - GStreamer directory not found at expected location")
        if 'GSTREAMER' not in backend_names:
            print("  - GStreamer backend not available in OpenCV")
        return False


if __name__ == "__main__":
    success = test_dll_setup()
    sys.exit(0 if success else 1)
