"""
Test script for metric depth calibration

Demonstrates how altitude-based calibration converts relative depth
to metric distance for obstacle avoidance.
"""

import cv2
import numpy as np
import logging
import yaml
from pathlib import Path

from drone_autonomy.depth import DepthEstimator, DepthScaleCalibrator, CameraIntrinsics


def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_config():
    """Load configuration"""
    config_path = Path(__file__).parent.parent / 'config' / 'default_config.yaml'
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config['depth']


def test_calibration_basic():
    """Test basic calibration functionality"""
    print("\n" + "="*60)
    print("TEST 1: Basic Calibration Functionality")
    print("="*60)
    
    # Setup
    config = {
        'use_metric_calibration': True,
        'image_width': 640,
        'image_height': 480,
        'horizontal_fov': 90.0,
        'min_altitude_for_calibration': 1.0,
        'ground_plane_sample_region': 0.3,
        'default_max_range': 10.0,
        'default_min_range': 0.5
    }
    
    calibrator = DepthScaleCalibrator(config)
    
    # Create synthetic depth map (ground visible at bottom)
    depth_map = np.zeros((480, 640), dtype=np.float32)
    
    # Sky region (top 50% - far, low depth values)
    depth_map[:240, :] = 0.1
    
    # Mid region (gradient)
    for y in range(240, 380):
        depth_map[y, :] = 0.1 + (y - 240) / 140 * 0.6
    
    # Ground region (bottom 20% - close, high depth values)
    depth_map[380:, :] = 0.8 + np.random.randn(100, 640) * 0.05
    depth_map = np.clip(depth_map, 0, 1)
    
    # Test calibration at different altitudes
    altitudes = [2.0, 5.0, 10.0, 15.0]
    
    for altitude in altitudes:
        success = calibrator.calibrate_from_altitude(
            depth_map=depth_map,
            altitude_agl=altitude,
            pitch_deg=-15.0,  # Looking down
            roll_deg=0.0
        )
        
        status = calibrator.get_calibration_status()
        
        print(f"\nAltitude: {altitude:.1f}m")
        print(f"  Calibration successful: {success}")
        print(f"  Scale factor: {status['scale_factor']:.2f}m")
        print(f"  Max range: {status['max_range']:.2f}m")
        print(f"  Calibrated: {status['calibrated']}")
    
    # Convert some depth values
    print("\n" + "-"*60)
    print("Depth Conversion Examples (at 5m altitude):")
    print("-"*60)
    
    calibrator = DepthScaleCalibrator(config)
    calibrator.calibrate_from_altitude(depth_map, 5.0, -15.0, 0.0)
    
    test_depths = [0.0, 0.25, 0.5, 0.75, 1.0]
    
    for depth_rel in test_depths:
        depth_metric = calibrator.relative_to_metric(np.array([depth_rel]))[0]
        print(f"  Relative depth {depth_rel:.2f} → {depth_metric:.2f}m")


def test_with_depth_estimator():
    """Test integration with DepthEstimator"""
    print("\n" + "="*60)
    print("TEST 2: Integration with DepthEstimator")
    print("="*60)
    
    # Load config
    depth_config = load_config()
    
    # Create dummy frame
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Initialize estimator (without loading actual model for this test)
    estimator = DepthEstimator(depth_config)
    
    # Check calibrator initialization
    print(f"\nMetric calibration enabled: {estimator.use_metric_calibration}")
    print(f"Calibrator initialized: {estimator.calibrator is not None}")
    
    if estimator.calibrator:
        # Simulate relative depth map
        depth_relative = np.random.rand(240, 320).astype(np.float32)
        
        # Simulate telemetry
        telemetry = {
            'altitude_rel': 5.0,
            'pitch': -10.0,
            'roll': 0.0
        }
        
        # Get metric depth
        depth_metric = estimator.get_metric_depth(depth_relative, telemetry)
        
        print(f"\nDepth map shape: {depth_metric.shape}")
        print(f"Depth range: {depth_metric.min():.2f}m to {depth_metric.max():.2f}m")
        print(f"Mean depth: {depth_metric.mean():.2f}m")
        
        # Check calibration status
        status = estimator.get_calibration_status()
        print(f"\nCalibration status:")
        print(f"  Enabled: {status['enabled']}")
        print(f"  Calibrated: {status.get('calibrated', False)}")
        print(f"  Scale factor: {status.get('scale_factor', 0):.2f}m")


def test_camera_intrinsics():
    """Test camera intrinsics calculation"""
    print("\n" + "="*60)
    print("TEST 3: Camera Intrinsics from FOV")
    print("="*60)
    
    # Test different FOVs
    fovs = [60.0, 90.0, 120.0]
    width, height = 640, 480
    
    for fov in fovs:
        camera = CameraIntrinsics.from_fov(width, height, fov)
        
        print(f"\nHorizontal FOV: {fov}°")
        print(f"  Focal length (fx, fy): ({camera.fx:.1f}, {camera.fy:.1f})")
        print(f"  Principal point (cx, cy): ({camera.cx:.1f}, {camera.cy:.1f})")
        print(f"  Image size: {camera.width}x{camera.height}")


def visualize_depth_comparison():
    """Visualize relative vs metric depth"""
    print("\n" + "="*60)
    print("TEST 4: Visual Comparison (Relative vs Metric)")
    print("="*60)
    
    # Setup
    config = {
        'use_metric_calibration': True,
        'image_width': 640,
        'image_height': 480,
        'horizontal_fov': 90.0,
        'min_altitude_for_calibration': 1.0,
        'ground_plane_sample_region': 0.3,
        'default_max_range': 10.0,
        'default_min_range': 0.5
    }
    
    calibrator = DepthScaleCalibrator(config)
    
    # Create synthetic scene
    h, w = 480, 640
    depth_relative = np.zeros((h, w), dtype=np.float32)
    
    # Create depth gradient (top = far/0, bottom = close/1)
    for y in range(h):
        depth_relative[y, :] = y / h
    
    # Add some obstacles (closer regions)
    cv2.circle(depth_relative, (200, 200), 50, 0.9, -1)
    cv2.circle(depth_relative, (400, 300), 70, 0.7, -1)
    
    # Calibrate at 5m altitude
    calibrator.calibrate_from_altitude(depth_relative, 5.0, -10.0, 0.0)
    
    # Convert to metric
    depth_metric = calibrator.relative_to_metric(depth_relative)
    
    # Visualize
    print("\nCreating visualizations...")
    
    # Relative depth visualization
    depth_rel_vis = (depth_relative * 255).astype(np.uint8)
    depth_rel_colored = cv2.applyColorMap(depth_rel_vis, cv2.COLORMAP_MAGMA)
    
    # Metric depth visualization (normalize to 0-10m range)
    depth_metric_norm = np.clip(depth_metric / 10.0, 0, 1)
    depth_metric_vis = (depth_metric_norm * 255).astype(np.uint8)
    depth_metric_colored = cv2.applyColorMap(depth_metric_vis, cv2.COLORMAP_MAGMA)
    
    # Add labels
    cv2.putText(depth_rel_colored, "Relative Depth (0-1)", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(depth_metric_colored, f"Metric Depth (0-10m)", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Sample points and show values
    sample_points = [(200, 200), (400, 300), (320, 400)]
    
    for pt in sample_points:
        x, y = pt
        rel_val = depth_relative[y, x]
        metric_val = depth_metric[y, x]
        
        cv2.circle(depth_rel_colored, pt, 5, (0, 255, 0), -1)
        cv2.circle(depth_metric_colored, pt, 5, (0, 255, 0), -1)
        
        cv2.putText(depth_metric_colored, f"{metric_val:.1f}m", 
                    (x + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Combine
    combined = np.hstack([depth_rel_colored, depth_metric_colored])
    
    # Save
    output_path = Path(__file__).parent.parent / 'output' / 'depth_calibration_test.png'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), combined)
    
    print(f"Visualization saved to: {output_path}")
    print("\nSample depths:")
    for pt in sample_points:
        x, y = pt
        print(f"  Point ({x}, {y}): {depth_relative[y, x]:.2f} → {depth_metric[y, x]:.2f}m")


def main():
    """Run all tests"""
    setup_logging()
    
    print("\n" + "="*60)
    print("METRIC DEPTH CALIBRATION TEST SUITE")
    print("="*60)
    
    try:
        test_calibration_basic()
        test_with_depth_estimator()
        test_camera_intrinsics()
        visualize_depth_comparison()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
