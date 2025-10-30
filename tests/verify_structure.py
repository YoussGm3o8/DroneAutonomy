"""Verify project structure without requiring dependencies."""

import os
import sys
from pathlib import Path


def verify_structure():
    """Verify project directory structure."""
    print("=" * 80)
    print("DroneAutonomy Structure Verification")
    print("=" * 80)
    
    project_root = Path(__file__).parent.parent
    
    # Required directories
    required_dirs = [
        'src/drone_autonomy',
        'src/drone_autonomy/video',
        'src/drone_autonomy/vio',
        'src/drone_autonomy/depth',
        'src/drone_autonomy/detection',
        'src/drone_autonomy/fusion',
        'src/drone_autonomy/mavlink',
        'src/drone_autonomy/simulation',
        'src/drone_autonomy/utils',
        'config',
        'docs',
        'examples',
        'tests',
    ]
    
    # Required files
    required_files = [
        'README.md',
        'LICENSE',
        'requirements.txt',
        'setup.py',
        '.gitignore',
        'config/default_config.yaml',
        'docs/OPERATOR_GUIDE.md',
        'docs/TECHNICAL.md',
        'src/drone_autonomy/__init__.py',
        'src/drone_autonomy/pipeline.py',
        'src/drone_autonomy/video/__init__.py',
        'src/drone_autonomy/video/stream.py',
        'src/drone_autonomy/vio/__init__.py',
        'src/drone_autonomy/vio/vio_estimator.py',
        'src/drone_autonomy/depth/__init__.py',
        'src/drone_autonomy/depth/depth_estimator.py',
        'src/drone_autonomy/detection/__init__.py',
        'src/drone_autonomy/detection/yolo_detector.py',
        'src/drone_autonomy/detection/target_detector.py',
        'src/drone_autonomy/fusion/__init__.py',
        'src/drone_autonomy/fusion/decision_layer.py',
        'src/drone_autonomy/mavlink/__init__.py',
        'src/drone_autonomy/mavlink/telemetry.py',
        'src/drone_autonomy/simulation/__init__.py',
        'src/drone_autonomy/simulation/airsim_interface.py',
        'src/drone_autonomy/utils/__init__.py',
        'src/drone_autonomy/utils/config.py',
        'src/drone_autonomy/utils/logger.py',
        'src/drone_autonomy/utils/camera_calibration.py',
        'examples/run_basic.py',
        'examples/calibrate_camera.py',
        'examples/test_depth_estimation.py',
        'examples/test_yolo_detection.py',
        'examples/test_target_detection.py',
        'examples/test_airsim.py',
        'tests/test_integration.py',
    ]
    
    print("\nChecking directories...")
    dir_ok = True
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists() and full_path.is_dir():
            print(f"  ✓ {dir_path}")
        else:
            print(f"  ✗ {dir_path} - MISSING")
            dir_ok = False
    
    print("\nChecking files...")
    file_ok = True
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists() and full_path.is_file():
            size = full_path.stat().st_size
            print(f"  ✓ {file_path} ({size} bytes)")
        else:
            print(f"  ✗ {file_path} - MISSING")
            file_ok = False
    
    print("\n" + "=" * 80)
    if dir_ok and file_ok:
        print("✓ All structure checks passed!")
        print("=" * 80)
        return True
    else:
        print("✗ Some checks failed")
        print("=" * 80)
        return False


def count_lines():
    """Count lines of code."""
    print("\nCode Statistics:")
    print("-" * 80)
    
    project_root = Path(__file__).parent.parent
    src_dir = project_root / 'src'
    
    total_lines = 0
    total_files = 0
    
    for py_file in src_dir.rglob('*.py'):
        with open(py_file, 'r') as f:
            lines = len(f.readlines())
            total_lines += lines
            total_files += 1
    
    print(f"Total Python files: {total_files}")
    print(f"Total lines of code: {total_lines}")
    print("-" * 80)


if __name__ == '__main__':
    success = verify_structure()
    count_lines()
    sys.exit(0 if success else 1)
