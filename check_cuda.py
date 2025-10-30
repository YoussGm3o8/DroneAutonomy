"""Check CUDA availability"""
import torch

print("=" * 60)
print("GPU/CUDA Status Check")
print("=" * 60)
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU device count: {torch.cuda.device_count()}")
    print(f"GPU device 0: {torch.cuda.get_device_name(0)}")
    print(f"GPU memory allocated: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")
    print(f"GPU memory cached: {torch.cuda.memory_reserved(0) / 1024**2:.2f} MB")
else:
    print("CUDA is NOT available!")
    print("Possible reasons:")
    print("  1. PyTorch CPU-only version installed")
    print("  2. NVIDIA GPU drivers not installed")
    print("  3. CUDA toolkit not compatible with PyTorch")
print("=" * 60)
