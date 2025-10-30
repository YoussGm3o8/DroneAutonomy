"""Check OpenCV CUDA support"""
import cv2

print("=" * 60)
print("OpenCV Build Information")
print("=" * 60)
print(f"OpenCV version: {cv2.__version__}")
print(f"Has CUDA module: {hasattr(cv2, 'cuda')}")

if hasattr(cv2, 'cuda'):
    try:
        device_count = cv2.cuda.getCudaEnabledDeviceCount()
        print(f"CUDA-enabled devices: {device_count}")
        if device_count > 0:
            print("✓ OpenCV has CUDA support!")
        else:
            print("✗ CUDA module present but no devices detected")
    except Exception as e:
        print(f"Error checking CUDA devices: {e}")
else:
    print("✗ OpenCV does NOT have CUDA support")
    print("This is NORMAL - custom build may not have CUDA")
    print("PyTorch will handle GPU acceleration for depth model")

print("=" * 60)
