"""
Drone Autonomy GUI Launcher

Launch the graphical interface for drone computer vision control.

Usage:
    python launch_gui.py [--config CONFIG_FILE] [--video-source SOURCE]

Options:
    --config: Path to configuration YAML file (default: config/default_config.yaml)
    --video-source: Video source (webcam, rtsp:URL, file:PATH)
    --help: Show this help message

Examples:
    # Launch with webcam
    python launch_gui.py --video-source webcam

    # Launch with RTSP stream
    python launch_gui.py --video-source rtsp://192.168.1.100:8554/stream

    # Launch with video file
    python launch_gui.py --video-source file:output/videos/test.mp4

    # Launch with custom config
    python launch_gui.py --config config/high_performance.yaml
"""

import sys
import os
import argparse
from pathlib import Path

# Add src to path FIRST
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import DLL setup BEFORE anything else (this sets up OpenCV paths)
try:
    from drone_autonomy.utils import dll_setup_auto
except ImportError:
    print("Warning: Could not import dll_setup_auto, DLL paths may not be configured")
    pass


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Drone Autonomy GUI - Computer Vision Control Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config/default_config.yaml",
        help="Path to configuration YAML file"
    )
    
    parser.add_argument(
        "--video-source",
        type=str,
        default="webcam",
        help="Video source: webcam, rtsp:URL, or file:PATH"
    )
    
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Start in fullscreen mode"
    )
    
    parser.add_argument(
        "--no-telemetry",
        action="store_true",
        help="Disable telemetry display"
    )
    
    parser.add_argument(
        "--demo-mode",
        action="store_true",
        help="Run in demo mode with simulated data"
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    # Import PyQt6
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
    except ImportError:
        print("Error: PyQt6 not installed!")
        print("Install with: pip install PyQt6")
        sys.exit(1)
    
    # Import GUI module
    try:
        from drone_autonomy.gui.main_window import MainWindow
    except ImportError as e:
        print(f"Error importing GUI module: {e}")
        print("Make sure you're running from the project root directory.")
        sys.exit(1)
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Drone Autonomy")
    app.setOrganizationName("DroneAutonomy")
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create main window
    window = MainWindow()
    
    # Apply arguments
    if args.fullscreen:
        window.showFullScreen()
    else:
        window.show()
    
    # Load configuration
    if Path(args.config).exists():
        print(f"Loading configuration: {args.config}")
        # TODO: Load and apply configuration
    else:
        print(f"Warning: Configuration file not found: {args.config}")
        print("Using default settings.")
    
    # Set video source
    print(f"Video source: {args.video_source}")
    # TODO: Initialize video source
    
    if args.demo_mode:
        print("Running in demo mode with simulated data")
        # TODO: Initialize demo mode
    
    # Run application
    print("Drone Autonomy GUI started successfully!")
    print("Press Ctrl+Q or use File > Exit to quit.")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
