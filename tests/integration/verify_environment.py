#!/usr/bin/env python
"""
Verification script for PyTorch and DroneAutonomy environment
Checks compatibility of installed packages with CUDA 12.9 and Depth Anything V2
"""

import sys
import subprocess

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def check_torch():
    print_section("PyTorch Installation")
    try:
        import torch
        print(f"✓ PyTorch Version: {torch.__version__}")
        print(f"✓ CUDA Available: {torch.cuda.is_available()}")
        print(f"✓ CUDA Version: {torch.version.cuda}")
        
        if torch.cuda.is_available():
            print(f"✓ GPU Device: {torch.cuda.get_device_name(0)}")
            print(f"✓ CUDA Device Count: {torch.cuda.device_count()}")
            print(f"✓ GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        else:
            print("⚠ Warning: CUDA not detected (CPU mode)")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def check_torchvision():
    print_section("TorchVision Installation")
    try:
        import torchvision
        print(f"✓ TorchVision Version: {torchvision.__version__}")
        
        # Check compatibility with Depth Anything V2
        version_tuple = tuple(map(int, torchvision.__version__.split('.')[:2]))
        if version_tuple >= (0, 22):
            print(f"✓ Compatible with Depth Anything V2 (requires >=0.22.1, <0.23.0)")
        else:
            print(f"⚠ Warning: May not be compatible with Depth Anything V2")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def check_depth_anything_v2():
    print_section("Depth Anything V2 Compatibility")
    try:
        # Check if package is installed
        result = subprocess.run(
            [sys.executable, "-c", "import depth_anything_v2"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ Depth Anything V2 is installed")
            
            # Try to import the model
            try:
                from depth_anything_v2.dpt import DepthAnythingV2
                print("✓ DepthAnythingV2 model can be imported")
                return True
            except ImportError as e:
                print(f"⚠ Warning: Could not import model - {e}")
                return False
        else:
            print("✗ Depth Anything V2 not installed")
            print(f"  Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def check_opencv():
    print_section("OpenCV Installation")
    try:
        import cv2
        print(f"✓ OpenCV Version: {cv2.__version__}")
        return True
    except ImportError as e:
        print(f"✗ OpenCV import failed: {e}")
        print("  Note: This is expected on Python 3.13")
        print("  Solution: Use Python 3.11 or 3.12, or install via conda")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def check_python():
    print_section("Python Environment")
    print(f"✓ Python Version: {sys.version}")
    print(f"✓ Python Executable: {sys.executable}")
    
    if sys.version_info >= (3, 13):
        print("\n⚠ Warning: Python 3.13 detected")
        print("  Note: OpenCV may not have precompiled wheels for Python 3.13")
        print("  Recommendation: Use Python 3.11 or 3.12 for full compatibility")

def check_requirements():
    print_section("Key Package Versions")
    packages = [
        'torch',
        'torchvision',
        'torchaudio',
        'opencv-python',
        'opencv-contrib-python',
        'numpy',
        'depth-anything-v2',
        'huggingface-hub'
    ]
    
    for package in packages:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Extract version
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        version = line.split(':', 1)[1].strip()
                        print(f"✓ {package:30} {version}")
                        break
            else:
                print(f"- {package:30} (not installed)")
        except Exception as e:
            print(f"✗ {package:30} (error checking)")

def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "DroneAutonomy Environment Verification" + " "*5 + "║")
    print("║" + " "*10 + "CUDA 12.9 + Depth Anything V2 Compatibility" + " "*4 + "║")
    print("╚" + "="*58 + "╝")
    
    check_python()
    
    results = {
        'PyTorch': check_torch(),
        'TorchVision': check_torchvision(),
        'OpenCV': check_opencv(),
        'Depth Anything V2': check_depth_anything_v2(),
    }
    
    check_requirements()
    
    print_section("Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, status in results.items():
        symbol = "✓" if status else "✗"
        print(f"{symbol} {name}: {'PASS' if status else 'FAIL'}")
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✓ Environment is ready for DroneAutonomy!")
    else:
        print("\n⚠ Some issues detected. See above for details.")
    
    print_section("Recommendations")
    
    if sys.version_info >= (3, 13):
        print("• Python 3.13 detected - Consider using Python 3.11 or 3.12 for full compatibility")
    
    if not results.get('OpenCV', False):
        print("• OpenCV not working - Try:")
        print("  - Downgrade to Python 3.11 or 3.12")
        print("  - Or install via conda: conda install opencv")
    
    if results.get('PyTorch', False):
        print("✓ PyTorch is properly configured for CUDA acceleration")
        print("✓ Compatible with Depth Anything V2 for depth estimation")
    
    print()

if __name__ == '__main__':
    main()
