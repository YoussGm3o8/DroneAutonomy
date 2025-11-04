"""
Quick Start Example for Drone Autonomy GUI

This example demonstrates how to launch the GUI with a simple pipeline.
Perfect for testing and development.
"""

import sys
import os
from pathlib import Path

# Add src to path FIRST
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import DLL setup BEFORE OpenCV or GUI imports
try:
    from drone_autonomy.utils import dll_setup_auto
except ImportError:
    print("Warning: Could not import dll_setup_auto, DLL paths may not be configured")
    pass

# Now safe to import cv2 and other modules
import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication
from drone_autonomy.gui.main_window import MainWindow


class MockPipeline:
    """
    Mock pipeline for GUI testing without hardware
    Generates synthetic video, depth, and detections
    """
    
    def __init__(self):
        self.frame_count = 0
        self.target_x = 320
        self.target_y = 240
        self.target_vx = 2
        self.target_vy = 1
        
    def process_frame(self, frame=None):
        """
        Process frame - can generate synthetic or process provided frame
        
        Args:
            frame: Optional input frame. If None, generates synthetic frame.
        """
        if frame is None:
            # Generate synthetic frame
            frame = np.ones((480, 640, 3), dtype=np.uint8) * 50
            
            # Add grid pattern
            for i in range(0, 640, 40):
                cv2.line(frame, (i, 0), (i, 480), (70, 70, 70), 1)
            for i in range(0, 480, 40):
                cv2.line(frame, (0, i), (640, i), (70, 70, 70), 1)
        else:
            # Use provided frame (from webcam, RTSP, or file)
            # Ensure it's RGB
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            elif frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
            
        # Add moving target
        self.target_x += self.target_vx
        self.target_y += self.target_vy
        
        # Bounce off walls (adapt to frame size)
        h, w = frame.shape[:2]
        if self.target_x < 50 or self.target_x > w - 50:
            self.target_vx = -self.target_vx
        if self.target_y < 50 or self.target_y > h - 50:
            self.target_vy = -self.target_vy
            
        # Draw target circle
        cv2.circle(frame, (int(self.target_x), int(self.target_y)), 30, (0, 0, 255), -1)
        cv2.circle(frame, (int(self.target_x), int(self.target_y)), 30, (255, 255, 255), 2)
        
        # Generate synthetic depth map
        depth_map = np.zeros((h, w), dtype=np.float32)
        
        # Depth gradient (closer at bottom)
        for y in range(h):
            depth_map[y, :] = (h - y) / float(h)
        # Depth gradient (closer at bottom)
        for y in range(h):
            depth_map[y, :] = (h - y) / float(h)
            
        # Target depth (closer)
        cv2.circle(depth_map, (int(self.target_x), int(self.target_y)), 30, 0.3, -1)
        
        # Create detection for target
        detections = [{
            'bbox': [
                int(self.target_x - 30),
                int(self.target_y - 30),
                int(self.target_x + 30),
                int(self.target_y + 30)
            ],
            'class_name': 'target',
            'confidence': 0.95
        }]
        
        self.frame_count += 1
        
        return frame, depth_map, detections
        
    def get_telemetry(self):
        """Generate synthetic telemetry"""
        import math
        
        # Oscillating values for demo
        t = self.frame_count / 30.0  # Time in seconds
        
        return {
            'latitude': 40.7128 + math.sin(t * 0.1) * 0.001,
            'longitude': -74.0060 + math.cos(t * 0.1) * 0.001,
            'altitude': 30.0 + math.sin(t * 0.5) * 5.0,
            'gps_fix_type': 3,
            'roll': math.sin(t * 0.3) * 15.0,
            'pitch': math.cos(t * 0.4) * 10.0,
            'yaw': (t * 10) % 360,
            'heading': (t * 10) % 360,
            'ground_speed': 5.0 + math.sin(t * 0.2) * 2.0,
            'vertical_speed': math.sin(t * 0.5) * 1.0,
            'airspeed': 6.0 + math.sin(t * 0.3) * 1.5,
            'battery_voltage': 16.0 - (t / 600) * 2.0,  # Simulated discharge
            'battery_current': 15.0 + math.sin(t * 0.5) * 5.0,
            'armed': True,
            'failsafe_active': False,
            'rc_rssi': int(80 + math.sin(t * 0.1) * 20),
            'flight_mode': 'GUIDED'
        }
        
    def get_state(self):
        """Get state machine state"""
        states = [
            "SEARCHING",
            "TARGET_LOCKED",
            "APPROACHING",
            "POSITIONING",
            "STABILIZING"
        ]
        state_idx = (self.frame_count // 90) % len(states)
        return states[state_idx]


def main():
    """Main entry point"""
    print("=" * 60)
    print("Drone Autonomy GUI - Quick Start Example")
    print("=" * 60)
    print()
    print("This example launches the GUI with a mock pipeline that")
    print("generates synthetic video, depth maps, and telemetry.")
    print()
    print("Features demonstrated:")
    print("  ✓ Live video display with moving target")
    print("  ✓ Synthetic depth map visualization")
    print("  ✓ Detection bounding boxes")
    print("  ✓ Real-time telemetry updates")
    print("  ✓ State machine status")
    print()
    print("Controls:")
    print("  - Switch between visualization modes")
    print("  - Adjust depth overlay opacity")
    print("  - Capture screenshots")
    print("  - Select and configure tasks")
    print("  - Browse media gallery")
    print("  - View results and logs")
    print()
    print("Press Ctrl+Q to quit")
    print("=" * 60)
    print()
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Drone Autonomy - Demo")
    app.setStyle("Fusion")
    
    # Create main window
    window = MainWindow()
    
    # Create and set mock pipeline
    mock_pipeline = MockPipeline()
    window.pipeline = mock_pipeline
    
    # Start video processing thread
    window.video_thread.set_pipeline(mock_pipeline)
    window.video_thread.start()
    
    # Update status
    window.status_label.setText("Demo Mode: Mock Pipeline Active")
    window.telemetry_display.set_connection_status("Connected")
    window.results_viewer.add_log("Demo mode started with synthetic data", "INFO")
    window.results_viewer.add_log("Mock pipeline generating video at 30 FPS", "INFO")
    window.results_viewer.add_log("Synthetic telemetry updating in real-time", "SUCCESS")
    
    # Show window
    window.show()
    
    print("GUI launched successfully!")
    print("Mock pipeline running with synthetic data.")
    print()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nShutdown requested... exiting")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
