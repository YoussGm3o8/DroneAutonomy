"""Comprehensive integration test for the DroneAutonomy pipeline."""

import sys
import cv2
import numpy as np
import time
sys.path.insert(0, '/home/runner/work/DroneAutonomy/DroneAutonomy/src')

from drone_autonomy.utils.config import Config
from drone_autonomy.utils.logger import setup_logging
from drone_autonomy.video.stream import VideoStream
from drone_autonomy.vio.vio_estimator import VIOEstimator
from drone_autonomy.depth.depth_estimator import DepthEstimator
from drone_autonomy.detection.yolo_detector import YOLODetector
from drone_autonomy.detection.target_detector import TargetDetector
from drone_autonomy.fusion.decision_layer import DecisionLayer
from drone_autonomy.utils.camera_calibration import CameraCalibration


def test_video_stream():
    """Test video stream module."""
    print("\n" + "="*80)
    print("Testing Video Stream")
    print("="*80)
    
    config = {
        'backend': 'opencv',
        'camera_id': 0,
        'width': 640,
        'height': 480,
        'fps': 30
    }
    
    stream = VideoStream(config)
    
    if not stream.start():
        print("❌ Failed to start video stream")
        return False
    
    print("✓ Video stream started")
    
    # Read a few frames
    success_count = 0
    for i in range(10):
        ret, frame, timestamp = stream.read()
        if ret and frame is not None:
            success_count += 1
    
    stream.stop()
    
    if success_count >= 8:
        print(f"✓ Successfully read {success_count}/10 frames")
        return True
    else:
        print(f"❌ Only read {success_count}/10 frames")
        return False


def test_camera_calibration():
    """Test camera calibration module."""
    print("\n" + "="*80)
    print("Testing Camera Calibration")
    print("="*80)
    
    calib = CameraCalibration()
    
    # Load from config
    config = {
        'fx': 500.0, 'fy': 500.0,
        'cx': 320.0, 'cy': 240.0,
        'k1': 0.0, 'k2': 0.0,
        'p1': 0.0, 'p2': 0.0
    }
    calib.load_from_config(config)
    
    if calib.get_camera_matrix() is not None:
        print("✓ Camera calibration loaded from config")
        return True
    else:
        print("❌ Failed to load camera calibration")
        return False


def test_target_detector():
    """Test target detector with synthetic image."""
    print("\n" + "="*80)
    print("Testing Target Detector")
    print("="*80)
    
    # Create synthetic image with red circle
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.circle(img, (320, 240), 50, (0, 0, 255), -1)
    
    config = {
        'hsv_lower': [0, 100, 100],
        'hsv_upper': [10, 255, 255],
        'min_radius': 10,
        'max_radius': 200,
        'circle_threshold': 0.5
    }
    
    detector = TargetDetector(config)
    targets, process_time = detector.detect(img)
    
    if len(targets) > 0:
        print(f"✓ Detected {len(targets)} target(s) in {process_time*1000:.1f}ms")
        print(f"  Target center: {targets[0]['center']}, radius: {targets[0]['radius']}")
        return True
    else:
        print("❌ Failed to detect synthetic red circle")
        return False


def test_fusion_layer():
    """Test fusion and decision layer."""
    print("\n" + "="*80)
    print("Testing Fusion Layer")
    print("="*80)
    
    config = {
        'depth_weight': 0.6,
        'detection_weight': 0.4,
        'min_confidence': 0.5,
        'proximity_threshold': 2.0
    }
    
    fusion = DecisionLayer(config)
    
    # Create mock detections
    detections = [
        {
            'class_name': 'person',
            'confidence': 0.8,
            'bbox': (100, 100, 200, 300),
            'center': (150, 200)
        }
    ]
    
    # Create mock depth map
    depth_map = np.random.rand(480, 640) * 0.5
    
    # Test fusion
    fused = fusion.fuse_detections_with_depth(detections, depth_map, depth_scale=10.0)
    
    if len(fused) > 0 and 'fused_confidence' in fused[0]:
        print(f"✓ Fused {len(fused)} detection(s)")
        print(f"  Fused confidence: {fused[0]['fused_confidence']:.2f}")
        print(f"  Distance estimate: {fused[0]['distance']:.2f}m")
        
        # Test avoidance command
        cmd = fusion.compute_avoidance_command(fused, 640, 480)
        print(f"  Avoidance priority: {cmd['priority']:.2f}")
        return True
    else:
        print("❌ Fusion failed")
        return False


def test_config_manager():
    """Test configuration manager."""
    print("\n" + "="*80)
    print("Testing Configuration Manager")
    print("="*80)
    
    config = Config()
    
    # Test get
    video_width = config.get('video.width', 0)
    if video_width > 0:
        print(f"✓ Read config value: video.width = {video_width}")
    else:
        print("❌ Failed to read config value")
        return False
    
    # Test set
    config.set('test.value', 123)
    if config.get('test.value') == 123:
        print("✓ Set and read config value successfully")
        return True
    else:
        print("❌ Failed to set config value")
        return False


def test_vio_estimator():
    """Test VIO estimator with synthetic frames."""
    print("\n" + "="*80)
    print("Testing VIO Estimator")
    print("="*80)
    
    # Create camera calibration
    camera_matrix = np.array([
        [500, 0, 320],
        [0, 500, 240],
        [0, 0, 1]
    ])
    dist_coeffs = np.zeros(4)
    
    config = {
        'enabled': True,
        'type': 'vins-mono'
    }
    
    vio = VIOEstimator(config, camera_matrix, dist_coeffs)
    
    # Create synthetic frames with features
    frame1 = np.random.randint(0, 255, (480, 640), dtype=np.uint8)
    frame2 = np.random.randint(0, 255, (480, 640), dtype=np.uint8)
    
    # Process frames
    success1, pos1, ori1 = vio.process_frame(frame1)
    success2, pos2, ori2 = vio.process_frame(frame2)
    
    if success1 and success2:
        print("✓ VIO processed frames successfully")
        print(f"  Position: {pos2}")
        print(f"  Orientation: {ori2}")
        return True
    else:
        print("❌ VIO processing failed")
        return False


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*80)
    print("DroneAutonomy Integration Tests")
    print("="*80)
    
    setup_logging(log_level='WARNING')
    
    tests = [
        ("Config Manager", test_config_manager),
        ("Camera Calibration", test_camera_calibration),
        ("Video Stream", test_video_stream),
        ("Target Detector", test_target_detector),
        ("Fusion Layer", test_fusion_layer),
        ("VIO Estimator", test_vio_estimator),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='DroneAutonomy Integration Tests')
    parser.add_argument('--test', type=str, help='Run specific test')
    
    args = parser.parse_args()
    
    if args.test:
        test_map = {
            'video': test_video_stream,
            'calibration': test_camera_calibration,
            'target': test_target_detector,
            'fusion': test_fusion_layer,
            'config': test_config_manager,
            'vio': test_vio_estimator,
        }
        
        if args.test in test_map:
            setup_logging(log_level='INFO')
            success = test_map[args.test]()
            return 0 if success else 1
        else:
            print(f"Unknown test: {args.test}")
            print(f"Available tests: {', '.join(test_map.keys())}")
            return 1
    else:
        # Run all tests
        success = run_all_tests()
        return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
