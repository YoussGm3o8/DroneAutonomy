"""Check OpenCV GStreamer support"""
import cv2

print("OpenCV Version:", cv2.__version__)
print("\nBuild Information:")
print("="*60)

build_info = cv2.getBuildInformation()

# Find GStreamer section
for line in build_info.split('\n'):
    if 'GStreamer' in line or 'GSTREAMER' in line.upper():
        print(line)
    if 'FFMPEG' in line:
        print(line)

print("\n" + "="*60)

# Check backends
print("\nAvailable VideoCapture backends:")
backends = [
    (cv2.CAP_GSTREAMER, "GStreamer"),
    (cv2.CAP_FFMPEG, "FFMPEG"),
    (cv2.CAP_MSMF, "Media Foundation"),
    (cv2.CAP_DSHOW, "DirectShow"),
]

for backend_id, name in backends:
    try:
        cap = cv2.VideoCapture()
        cap.open("test", backend_id)
        print(f"  ✓ {name} (ID: {backend_id})")
        cap.release()
    except:
        print(f"  ✗ {name} (ID: {backend_id})")

print("\nTesting GStreamer specifically...")
test_pipeline = "videotestsrc ! appsink"
cap = cv2.VideoCapture(test_pipeline, cv2.CAP_GSTREAMER)
if cap.isOpened():
    print("✅ GStreamer backend WORKS!")
    ret, frame = cap.read()
    if ret:
        print(f"✅ Can read test frames! Shape: {frame.shape}")
    cap.release()
else:
    print("❌ GStreamer backend FAILED - OpenCV not built with GStreamer support!")
    print("\nYou need to either:")
    print("1. Rebuild OpenCV with GStreamer support")
    print("2. Use pre-built OpenCV with GStreamer (from conda-forge or custom build)")
