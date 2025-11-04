#!/usr/bin/env python3
"""
Test MAVLink Object Avoidance System

This script demonstrates the integrated MAVLink obstacle avoidance system.
It connects to a drone (real or SITL), processes video/depth for obstacles,
and executes avoidance maneuvers via MAVLink commands.

Usage:
    # With SITL (software-in-the-loop):
    python examples/test_mavlink_avoidance.py

    # With custom config:
    python examples/test_mavlink_avoidance.py --config config/mavlink_avoidance.yaml

    # Simulation mode (no MAVLink):
    python examples/test_mavlink_avoidance.py --simulate

Requirements:
    - ArduPilot SITL or real drone with MAVLink
    - Video source (camera, RTSP stream, or AirSim)
    - GPU with CUDA for depth estimation
"""

import sys
import os
import time
import argparse
import logging
import cv2
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.drone_autonomy.utils.config import Config
from src.drone_autonomy.mavlink.telemetry import MAVLinkTelemetry
from src.drone_autonomy.navigation.obstacle_avoidance import ObstacleAvoider
from src.drone_autonomy.navigation.mavlink_avoidance_controller import (
    MAVLinkAvoidanceController,
    AvoidanceState
)
from src.drone_autonomy.depth.depth_estimator import DepthEstimator
from src.drone_autonomy.video.stream import VideoStream


def setup_logging(level: str = 'INFO'):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/mavlink_avoidance_test.log')
        ]
    )


def test_mavlink_commands(mavlink: MAVLinkTelemetry):
    """Test basic MAVLink command functionality"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Testing MAVLink Commands")
    logger.info("=" * 60)

    # Test connection
    logger.info("MAVLink connection status: " + ("✓ Connected" if mavlink.is_connected else "✗ Not connected"))
    if not mavlink.is_connected:
        return False

    # Test telemetry reading
    telemetry = mavlink.read_telemetry()
    logger.info(f"Flight mode: {telemetry.get('flight_mode', 'UNKNOWN')}")
    logger.info(f"Armed: {telemetry.get('armed', False)}")

    if 'position' in telemetry:
        pos = telemetry['position']
        logger.info(f"Position: lat={pos.get('latitude', 0):.6f}, lon={pos.get('longitude', 0):.6f}, alt={pos.get('relative_altitude', 0):.1f}m")

    # Test setting mode to GUIDED
    logger.info("\nTesting mode change to GUIDED...")
    if mavlink.set_mode("GUIDED"):
        logger.info("✓ Mode change command sent successfully")
        time.sleep(2)
        telemetry = mavlink.read_telemetry()
        logger.info(f"Current mode: {telemetry.get('flight_mode', 'UNKNOWN')}")
    else:
        logger.error("✗ Failed to send mode change command")

    # Test velocity commands
    logger.info("\nTesting velocity commands...")
    logger.info("Sending velocity command: vx=0.1 m/s (forward)")
    mavlink.send_velocity_body(0.1, 0, 0, 0)
    time.sleep(1)
    mavlink.send_velocity_body(0, 0, 0, 0)  # Stop
    logger.info("✓ Velocity command sent")

    logger.info("\nMAVLink command tests completed")
    logger.info("=" * 60)
    return True


def run_avoidance_test(config_path: str, simulate: bool = False):
    """
    Run the MAVLink obstacle avoidance test.

    Args:
        config_path: Path to configuration file
        simulate: If True, run without MAVLink connection
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("MAVLink Object Avoidance Test")
    logger.info("=" * 60)

    # Load configuration
    config = Config(config_path)
    logger.info(f"Loaded configuration from: {config_path}")

    # Initialize components
    mavlink = None
    video_stream = None
    depth_estimator = None
    avoider = None
    controller = None

    try:
        # 1. Setup MAVLink connection
        if not simulate:
            logger.info("\n[1/5] Connecting to MAVLink...")
            mavlink = MAVLinkTelemetry(config.get('mavlink', {}))
            if not mavlink.connect():
                logger.error("Failed to connect to MAVLink")
                return False
            logger.info("✓ MAVLink connected")

            # Test commands
            test_mavlink_commands(mavlink)
        else:
            logger.info("\n[1/5] Simulation mode - skipping MAVLink connection")

        # 2. Setup video stream
        logger.info("\n[2/5] Initializing video stream...")
        video_config = config.get('video', {})
        video_stream = VideoStream(video_config)
        video_stream.start()
        logger.info("✓ Video stream started")

        # Wait for first frame
        for _ in range(30):
            frame = video_stream.read()
            if frame is not None:
                break
            time.sleep(0.1)

        if frame is None:
            logger.error("Failed to read video frame")
            return False

        logger.info(f"Video resolution: {frame.shape[1]}x{frame.shape[0]}")

        # 3. Setup depth estimator
        logger.info("\n[3/5] Initializing depth estimator...")
        depth_config = config.get('depth', {})
        depth_estimator = DepthEstimator(depth_config)
        logger.info(f"✓ Depth estimator initialized (model: {depth_config.get('model', 'unknown')})")

        # 4. Setup obstacle avoider
        logger.info("\n[4/5] Initializing obstacle avoidance system...")
        avoidance_config = config.get('obstacle_avoidance', {})
        avoider = ObstacleAvoider(avoidance_config)
        logger.info("✓ Obstacle avoider initialized")

        # 5. Setup MAVLink avoidance controller
        if not simulate:
            logger.info("\n[5/5] Initializing MAVLink avoidance controller...")
            controller_config = config.get('avoidance_controller', {})
            controller = MAVLinkAvoidanceController(
                mavlink=mavlink,
                avoider=avoider,
                config=controller_config
            )
            logger.info("✓ Avoidance controller initialized")
        else:
            logger.info("\n[5/5] Simulation mode - skipping controller initialization")

        # Main test loop
        logger.info("\n" + "=" * 60)
        logger.info("Starting main avoidance loop")
        logger.info("Press 'q' to quit, 's' to start/stop controller, 'p' to pause")
        logger.info("=" * 60)

        controller_active = False
        frame_count = 0
        start_time = time.time()

        # Create display window
        cv2.namedWindow('MAVLink Obstacle Avoidance', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('MAVLink Obstacle Avoidance', 1280, 720)

        while True:
            loop_start = time.time()

            # Read frame
            frame = video_stream.read()
            if frame is None:
                logger.warning("No frame available")
                time.sleep(0.1)
                continue

            # Estimate depth
            depth_result = depth_estimator.estimate(frame)
            if depth_result is None:
                logger.warning("Depth estimation failed")
                continue

            depth_map = depth_result['depth_map']

            # Detect obstacles
            obstacles = avoider.detect_obstacles(depth_map)

            # Update controller if active
            status = {}
            if controller and controller_active:
                telemetry = mavlink.read_telemetry()
                current_velocity = None
                if 'velocity' in telemetry:
                    vel = telemetry['velocity']
                    current_velocity = (vel.get('vx', 0), vel.get('vy', 0), vel.get('vz', 0))

                status = controller.update(
                    depth_map=depth_map,
                    current_velocity=current_velocity
                )

            # Create visualization
            if controller:
                viz_frame = controller.get_visualization_frame(frame, depth_map)
            else:
                viz_frame = avoider.visualize(frame, depth_map)

            # Add status overlay
            _draw_status_overlay(viz_frame, obstacles, status, controller_active, simulate)

            # Display
            cv2.imshow('MAVLink Obstacle Avoidance', viz_frame)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                logger.info("Quit requested")
                break
            elif key == ord('s') and controller:
                if controller_active:
                    controller.stop()
                    controller_active = False
                    logger.info("Controller STOPPED")
                else:
                    if controller.start():
                        controller_active = True
                        logger.info("Controller STARTED")
                    else:
                        logger.error("Failed to start controller")
            elif key == ord('p') and controller and controller_active:
                controller.pause()
                logger.info("Controller PAUSED")
            elif key == ord('r') and controller:
                controller.resume()
                logger.info("Controller RESUMED")
            elif key == ord('e') and controller:
                controller.emergency_stop()
                logger.info("EMERGENCY STOP")

            frame_count += 1

            # FPS calculation
            loop_time = time.time() - loop_start
            fps = 1.0 / loop_time if loop_time > 0 else 0

            # Status logging (every 2 seconds)
            if frame_count % 60 == 0:
                elapsed = time.time() - start_time
                avg_fps = frame_count / elapsed if elapsed > 0 else 0
                logger.info(
                    f"Status: frames={frame_count}, fps={avg_fps:.1f}, "
                    f"obstacles={len(obstacles)}, "
                    f"controller={'active' if controller_active else 'inactive'}"
                )

                if controller:
                    ctrl_status = controller.get_status()
                    logger.info(
                        f"Controller: state={ctrl_status['state']}, "
                        f"maneuvers={ctrl_status['avoidance_maneuvers']}, "
                        f"e-stops={ctrl_status['emergency_stops']}"
                    )

        logger.info("\n" + "=" * 60)
        logger.info("Test completed")
        logger.info(f"Total frames processed: {frame_count}")
        logger.info(f"Average FPS: {frame_count / (time.time() - start_time):.1f}")
        if controller:
            final_status = controller.get_status()
            logger.info(f"Avoidance maneuvers: {final_status['avoidance_maneuvers']}")
            logger.info(f"Emergency stops: {final_status['emergency_stops']}")
        logger.info("=" * 60)

        return True

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return True

    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        return False

    finally:
        # Cleanup
        logger.info("\nCleaning up...")
        if controller and controller.enabled:
            controller.stop()
        if video_stream:
            video_stream.stop()
        if mavlink and mavlink.is_connected:
            mavlink.disconnect()
        cv2.destroyAllWindows()
        logger.info("Cleanup complete")


def _draw_status_overlay(
    frame: np.ndarray,
    obstacles: list,
    status: dict,
    controller_active: bool,
    simulate: bool
):
    """Draw status information overlay on frame"""
    h, w = frame.shape[:2]
    overlay = frame.copy()

    # Status panel
    panel_height = 120
    cv2.rectangle(overlay, (w - 300, 10), (w - 10, panel_height), (0, 0, 0), -1)
    cv2.rectangle(overlay, (w - 300, 10), (w - 10, panel_height), (100, 100, 100), 2)

    y = 35
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness = 1

    # Mode
    mode_text = "SIMULATION" if simulate else "LIVE"
    mode_color = (255, 255, 0) if simulate else (0, 255, 0)
    cv2.putText(overlay, f"Mode: {mode_text}", (w - 285, y), font, font_scale, mode_color, thickness)

    # Controller status
    y += 25
    ctrl_text = "ACTIVE" if controller_active else "INACTIVE"
    ctrl_color = (0, 255, 0) if controller_active else (128, 128, 128)
    cv2.putText(overlay, f"Controller: {ctrl_text}", (w - 285, y), font, font_scale, ctrl_color, thickness)

    # State
    if status and 'state' in status:
        y += 25
        state_color = (0, 165, 255) if status['state'] == 'avoiding' else (255, 255, 255)
        cv2.putText(overlay, f"State: {status['state']}", (w - 285, y), font, font_scale, state_color, thickness)

    # Obstacles
    y += 25
    obs_color = (0, 0, 255) if len(obstacles) > 0 else (0, 255, 0)
    cv2.putText(overlay, f"Obstacles: {len(obstacles)}", (w - 285, y), font, font_scale, obs_color, thickness)

    # Instructions
    y = h - 80
    instructions = [
        "Controls:",
        "Q: Quit",
        "S: Start/Stop",
        "P: Pause | R: Resume",
        "E: Emergency Stop"
    ]
    for i, text in enumerate(instructions):
        cv2.putText(overlay, text, (10, y + i * 15), font, 0.4, (255, 255, 255), 1)

    # Blend
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Test MAVLink Object Avoidance System')
    parser.add_argument(
        '--config',
        type=str,
        default='config/mavlink_avoidance.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--simulate',
        action='store_true',
        help='Run in simulation mode (no MAVLink connection)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )

    args = parser.parse_args()

    # Setup logging
    os.makedirs('logs', exist_ok=True)
    setup_logging(args.log_level)

    logger = logging.getLogger(__name__)
    logger.info("MAVLink Obstacle Avoidance Test Script")
    logger.info(f"Configuration: {args.config}")
    logger.info(f"Simulation mode: {args.simulate}")

    # Run test
    success = run_avoidance_test(args.config, args.simulate)

    if success:
        logger.info("\n✓ Test completed successfully")
        return 0
    else:
        logger.error("\n✗ Test failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
