"""
Test Obstacle Avoidance Visualization
Demonstrates Tesla-style path planning and obstacle visualization
"""

import cv2
import numpy as np
import yaml
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from drone_autonomy.navigation.obstacle_avoidance import ObstacleAvoider
from drone_autonomy.depth.depth_estimator import DepthEstimator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration"""
    config_file = Path(__file__).parent.parent / 'config' / 'default_config.yaml'
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config


def create_test_scene(width=640, height=480):
    """Create a test frame with simulated obstacles"""
    frame = np.ones((height, width, 3), dtype=np.uint8) * 128
    
    # Add floor texture
    for i in range(0, height, 20):
        cv2.line(frame, (0, i), (width, i), (140, 140, 140), 1)
    for i in range(0, width, 20):
        cv2.line(frame, (i, 0), (i, height), (140, 140, 140), 1)
    
    # Add some obstacles (boxes)
    # Left obstacle
    cv2.rectangle(frame, (100, 200), (180, 400), (80, 80, 80), -1)
    cv2.rectangle(frame, (100, 200), (180, 400), (60, 60, 60), 2)
    
    # Center obstacle
    cv2.rectangle(frame, (280, 150), (360, 350), (70, 70, 70), -1)
    cv2.rectangle(frame, (280, 150), (360, 350), (50, 50, 50), 2)
    
    # Right obstacle (closer)
    cv2.rectangle(frame, (450, 250), (520, 450), (90, 90, 90), -1)
    cv2.rectangle(frame, (450, 250), (520, 450), (70, 70, 70), 2)
    
    # Add target (red circle)
    cv2.circle(frame, (320, 150), 20, (0, 0, 255), -1)
    cv2.circle(frame, (320, 150), 20, (0, 0, 200), 2)
    
    return frame


def create_test_depth_map(width=640, height=480):
    """Create a test depth map with obstacles at different depths"""
    # Create gradient depth map (closer at bottom)
    depth_map = np.linspace(0.0, 1.0, height, dtype=np.float32)
    depth_map = np.tile(depth_map[:, np.newaxis], (1, width))
    
    # Add obstacles (closer = darker)
    # Left obstacle (3m away)
    depth_map[200:400, 100:180] = 0.3
    
    # Center obstacle (2.5m away)
    depth_map[150:350, 280:360] = 0.25
    
    # Right obstacle (1.8m away - critical)
    depth_map[250:450, 450:520] = 0.18
    
    # Target area (4m away)
    for i in range(20):
        for j in range(20):
            dist = np.sqrt((i-10)**2 + (j-10)**2)
            if dist <= 10:
                depth_map[150-10+i, 320-10+j] = 0.4
    
    return depth_map


def main():
    """Main test function"""
    logger.info("Starting Obstacle Avoidance Visualization Test")
    
    # Load configuration
    config = load_config()
    avoidance_config = config.get('autonomous', {}).get('obstacle_avoidance', {})
    
    # Initialize obstacle avoider
    obstacle_avoider = ObstacleAvoider(avoidance_config, logger)
    
    # Create test scene
    frame = create_test_scene()
    depth_map = create_test_depth_map()
    
    logger.info("Test scene created")
    logger.info(f"Frame shape: {frame.shape}")
    logger.info(f"Depth map shape: {depth_map.shape}")
    
    # Detect obstacles
    obstacles = obstacle_avoider.detect_obstacles(depth_map)
    logger.info(f"Detected {len(obstacles)} obstacles")
    
    for i, obs in enumerate(obstacles):
        logger.info(f"  Obstacle {i+1}: pos={obs.position}, dist={obs.distance:.2f}m, risk={obs.risk.get_name()}")
    
    # Generate paths
    target_position = (320, 150)  # Target position
    paths = obstacle_avoider.generate_path_candidates(frame.shape, target_position)
    logger.info(f"Generated {len(paths)} path candidates")
    
    if obstacle_avoider.selected_path:
        logger.info(f"Selected path: cost={obstacle_avoider.selected_path.cost:.2f}, "
                   f"clearance={obstacle_avoider.selected_path.clearance:.2f}m, "
                   f"safe={obstacle_avoider.selected_path.is_safe}")
    
    # Check if avoidance needed
    should_avoid = obstacle_avoider.should_avoid(target_detected=True, target_distance=4.0)
    logger.info(f"Avoidance active: {should_avoid}")
    
    if should_avoid:
        command = obstacle_avoider.get_avoidance_command()
        logger.info(f"Avoidance command: {command}")
    
    # Create visualizations
    logger.info("Creating visualizations...")
    
    # 1. Original frame
    cv2.imshow("1. Original Scene", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    
    # 2. Depth map
    depth_viz = cv2.normalize(depth_map, None, 0, 255, cv2.NORM_MINMAX)
    depth_viz = depth_viz.astype(np.uint8)
    depth_viz = cv2.applyColorMap(depth_viz, cv2.COLORMAP_TURBO)
    cv2.imshow("2. Depth Map", depth_viz)
    
    # 3. Obstacle Avoidance Visualization (Tesla-style)
    frame_rgb = frame.copy()
    viz_frame = obstacle_avoider.visualize(frame_rgb, depth_map)
    cv2.imshow("3. Obstacle Avoidance (Tesla Style)", cv2.cvtColor(viz_frame, cv2.COLOR_RGB2BGR))
    
    # 4. Depth overlay
    depth_heatmap = cv2.applyColorMap(depth_viz, cv2.COLORMAP_TURBO)
    depth_heatmap = cv2.cvtColor(depth_heatmap, cv2.COLOR_BGR2RGB)
    overlay = cv2.addWeighted(frame, 0.6, depth_heatmap, 0.4, 0)
    cv2.imshow("4. Depth Overlay", cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
    
    logger.info("\nVisualization windows created")
    logger.info("Press any key to exit...")
    
    # Wait for key press
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    logger.info("Test completed successfully")


if __name__ == '__main__':
    main()
