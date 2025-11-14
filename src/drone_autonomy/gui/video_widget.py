"""
Video Widget for Live Streaming and Playback

Displays live video feed with overlays for:
- Detection bounding boxes (targets, obstacles)
- Depth visualization (colored heat map)
- Telemetry overlay (altitude, speed, heading)
- Target tracking indicators
- State machine status
- FPS counter (optional)
- Fullscreen mode
"""

import cv2
import numpy as np
import time
from typing import Optional, List, Tuple
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QSlider
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont


class VideoWidget(QWidget):
    """
    Advanced video display widget with overlay capabilities
    """
    
    # Signals
    frame_clicked = pyqtSignal(int, int)  # Emits x, y coordinates
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_frame = None
        self.overlay_enabled = True
        self.depth_map = None
        self.detections = []
        self.telemetry = {}
        self.state_info = ""
        self.show_fps = False  # FPS counter toggle
        self.is_fullscreen = False
        
        # Obstacle avoidance visualization
        self.obstacle_avoider = None  # Will be set externally
        
        # FPS tracking
        self.fps_history = []
        self.last_frame_time = time.time()
        self.current_fps = 0.0
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Video display label
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; border: 2px solid #333;")
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setScaledContents(False)  # Fixed: Prevent stretching
        self.video_label.mousePressEvent = self._on_video_clicked
        layout.addWidget(self.video_label)
        
        # Control bar
        control_layout = QHBoxLayout()
        
        # Fullscreen button
        self.fullscreen_btn = QPushButton("⛶ Fullscreen")
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        control_layout.addWidget(self.fullscreen_btn)
        
        # Overlay toggle
        self.overlay_btn = QPushButton("Overlays: ON")
        self.overlay_btn.setCheckable(True)
        self.overlay_btn.setChecked(True)
        self.overlay_btn.clicked.connect(self._toggle_overlay)
        control_layout.addWidget(self.overlay_btn)
        
        # Visualization mode selector
        control_layout.addWidget(QLabel("Viz Mode:"))
        self.viz_mode_combo = QComboBox()
        self.viz_mode_combo.addItems([
            "RGB Only",
            "Depth Overlay",
            "Depth Heatmap",
            "Detections Only",
            "Full Overlay",
            "Obstacle Avoidance"  # New mode
        ])
        self.viz_mode_combo.setCurrentText("Full Overlay")
        self.viz_mode_combo.currentTextChanged.connect(self.refresh_display)
        control_layout.addWidget(self.viz_mode_combo)
        
        # Depth opacity slider
        control_layout.addWidget(QLabel("Depth Opacity:"))
        self.depth_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.depth_opacity_slider.setMinimum(0)
        self.depth_opacity_slider.setMaximum(100)
        self.depth_opacity_slider.setValue(40)
        self.depth_opacity_slider.setMaximumWidth(150)
        self.depth_opacity_slider.valueChanged.connect(self.refresh_display)
        control_layout.addWidget(self.depth_opacity_slider)
        
        # Screenshot button
        self.screenshot_btn = QPushButton("📷 Capture")
        self.screenshot_btn.clicked.connect(self._capture_screenshot)
        control_layout.addWidget(self.screenshot_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        self.setLayout(layout)
        
    def set_obstacle_avoider(self, obstacle_avoider):
        """
        Set the obstacle avoider for visualization
        
        Args:
            obstacle_avoider: ObstacleAvoider instance
        """
        self.obstacle_avoider = obstacle_avoider
    
    def update_frame(self, frame: np.ndarray, depth_map: Optional[np.ndarray] = None,
                     detections: Optional[List] = None, telemetry: Optional[dict] = None,
                     state_info: str = ""):
        """
        Update displayed frame with optional overlays
        
        Args:
            frame: RGB frame (H, W, 3)
            depth_map: Depth map (H, W) or None
            detections: List of detection dicts with keys: bbox, class_name, confidence
            telemetry: Dict with GPS, altitude, heading, speed, etc.
            state_info: Current state machine state string
        """
        self.current_frame = frame.copy()
        self.depth_map = depth_map
        self.detections = detections or []
        self.telemetry = telemetry or {}
        self.state_info = state_info
        
        self.refresh_display()
        
    def refresh_display(self):
        """Redraw the current frame with overlays (optimized)"""
        if self.current_frame is None:
            return
            
        # Apply visualization based on mode
        viz_mode = self.viz_mode_combo.currentText()
        
        # Only copy frame if we need to draw on it
        if viz_mode == "RGB Only" and not self.show_fps:
            # Fast path: no overlays, just display original frame
            display_frame = self.current_frame
        elif viz_mode == "Depth Heatmap" and self.depth_map is not None:
            display_frame = self._create_depth_heatmap(self.depth_map)
        else:
            # Need to modify frame, make a copy
            display_frame = self.current_frame.copy()
            
            if viz_mode == "Depth Overlay" and self.depth_map is not None:
                display_frame = self._overlay_depth(display_frame, self.depth_map)
            elif viz_mode == "Full Overlay" and self.depth_map is not None:
                # Full overlay includes depth, obstacle avoidance, detections, telemetry
                display_frame = self._overlay_depth(display_frame, self.depth_map)
                # Add obstacle avoidance overlay if available
                if self.obstacle_avoider is not None:
                    display_frame = self.obstacle_avoider.visualize(display_frame, self.depth_map)
            elif viz_mode == "Obstacle Avoidance":
                # Tesla-style obstacle avoidance visualization only
                if self.obstacle_avoider is not None:
                    display_frame = self.obstacle_avoider.visualize(display_frame, self.depth_map)
                
            # Draw overlays if enabled
            if self.overlay_enabled and viz_mode != "RGB Only":
                if viz_mode in ["Detections Only", "Full Overlay"]:
                    display_frame = self._draw_detections(display_frame)
                
                if viz_mode == "Full Overlay":
                    display_frame = self._draw_telemetry(display_frame)
                    display_frame = self._draw_state_info(display_frame)
            
            # Draw FPS counter if enabled (always on top)
            if self.show_fps:
                display_frame = self._draw_fps(display_frame)
                
        # Convert to QPixmap and display
        self._display_numpy_frame(display_frame)
        
    def _display_numpy_frame(self, frame: np.ndarray):
        """Convert numpy frame to QPixmap and display with proper aspect ratio"""
        if frame is None:
            return
            
        h, w = frame.shape[:2]
        if len(frame.shape) == 3:
            bytes_per_line = 3 * w
            q_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        else:
            bytes_per_line = w
            q_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8)
            
        pixmap = QPixmap.fromImage(q_image)
        
        # Scale pixmap to fit label while maintaining aspect ratio
        # Use FastTransformation for better performance (vs SmoothTransformation)
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation  # Faster than Smooth
        )
        
        self.video_label.setPixmap(scaled_pixmap)
        
    def _create_depth_heatmap(self, depth_map: np.ndarray) -> np.ndarray:
        """Create colored depth heatmap"""
        # Normalize depth to 0-255
        normalized = cv2.normalize(depth_map, None, 0, 255, cv2.NORM_MINMAX)
        normalized = normalized.astype(np.uint8)
        
        # Apply colormap
        heatmap = cv2.applyColorMap(normalized, cv2.COLORMAP_TURBO)
        return cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
        
    def _overlay_depth(self, frame: np.ndarray, depth_map: np.ndarray) -> np.ndarray:
        """Overlay depth heatmap on RGB frame (optimized)"""
        # Resize depth map to frame size FIRST (before colormap for better performance)
        if depth_map.shape[:2] != frame.shape[:2]:
            depth_resized = cv2.resize(depth_map, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)
        else:
            depth_resized = depth_map
        
        # Normalize and apply colormap in-place for speed
        normalized = cv2.normalize(depth_resized, None, 0, 255, cv2.NORM_MINMAX)
        normalized = normalized.astype(np.uint8)
        heatmap = cv2.applyColorMap(normalized, cv2.COLORMAP_TURBO)
        heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
            
        # Blend with opacity
        opacity = self.depth_opacity_slider.value() / 100.0
        # Use in-place blending to avoid extra allocation
        blended = cv2.addWeighted(frame, 1 - opacity, heatmap, opacity, 0)
        return blended
        
    def _draw_detections(self, frame: np.ndarray) -> np.ndarray:
        """Draw detection bounding boxes and labels"""
        frame_draw = frame.copy()
        
        for det in self.detections:
            bbox = det.get('bbox')
            if bbox is None:
                continue
                
            x1, y1, x2, y2 = map(int, bbox)
            class_name = det.get('class_name', 'Unknown')
            confidence = det.get('confidence', 0.0)
            
            # Color coding
            color = self._get_class_color(class_name)
            
            # Draw bounding box
            cv2.rectangle(frame_draw, (x1, y1), (x2, y2), color, 2)
            
            # Draw label background
            label = f"{class_name} {confidence:.2f}"
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame_draw, (x1, y1 - label_h - 5), (x1 + label_w, y1), color, -1)
            
            # Draw label text
            cv2.putText(frame_draw, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX,
                       0.5, (255, 255, 255), 1, cv2.LINE_AA)
            
            # Draw center crosshair
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            cv2.drawMarker(frame_draw, (cx, cy), color, cv2.MARKER_CROSS, 10, 2)
            
        return frame_draw
        
    def _draw_telemetry(self, frame: np.ndarray) -> np.ndarray:
        """Draw telemetry overlay (top-left corner)"""
        if not self.telemetry:
            return frame
            
        frame_draw = frame.copy()
        y_offset = 30
        
        # Semi-transparent background
        overlay = frame_draw.copy()
        cv2.rectangle(overlay, (10, 10), (300, y_offset + len(self.telemetry) * 25), 
                     (0, 0, 0), -1)
        frame_draw = cv2.addWeighted(frame_draw, 0.7, overlay, 0.3, 0)
        
        # Draw telemetry text
        for key, value in self.telemetry.items():
            text = f"{key}: {value}"
            cv2.putText(frame_draw, text, (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX,
                       0.5, (0, 255, 0), 1, cv2.LINE_AA)
            y_offset += 25
            
        return frame_draw
        
    def _draw_state_info(self, frame: np.ndarray) -> np.ndarray:
        """Draw state machine info (bottom-left corner)"""
        if not self.state_info:
            return frame
            
        frame_draw = frame.copy()
        h = frame.shape[0]
        
        # Semi-transparent background
        overlay = frame_draw.copy()
        cv2.rectangle(overlay, (10, h - 50), (300, h - 10), (0, 0, 0), -1)
        frame_draw = cv2.addWeighted(frame_draw, 0.7, overlay, 0.3, 0)
        
        # Draw state text
        cv2.putText(frame_draw, f"State: {self.state_info}", (15, h - 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2, cv2.LINE_AA)
        
        return frame_draw
        
    def _get_class_color(self, class_name: str) -> Tuple[int, int, int]:
        """Get color for detection class"""
        color_map = {
            'target': (255, 0, 0),      # Red
            'obstacle': (0, 0, 255),     # Blue
            'landing_pad': (0, 255, 0),  # Green
            'person': (255, 255, 0),     # Yellow
        }
        return color_map.get(class_name.lower(), (128, 128, 128))  # Gray default
        
    def _toggle_overlay(self):
        """Toggle overlay display"""
        self.overlay_enabled = not self.overlay_enabled
        self.overlay_btn.setText(f"Overlays: {'ON' if self.overlay_enabled else 'OFF'}")
        self.refresh_display()
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode for video display"""
        if self.is_fullscreen:
            # Exit fullscreen - restore video label to main widget
            if hasattr(self, 'fullscreen_window') and self.fullscreen_window:
                self.fullscreen_window.close()
                self.fullscreen_window = None
                
                # Re-add video label to main layout
                self.layout().insertWidget(0, self.video_label)
                self.video_label.show()
                
            self.fullscreen_btn.setText("⛶ Fullscreen")
            self.is_fullscreen = False
            
            # Refresh display
            if self.current_frame is not None:
                self.refresh_display()
        else:
            # Enter fullscreen - create fullscreen window with video label
            from PyQt6.QtWidgets import QWidget
            from PyQt6.QtCore import Qt
            
            self.fullscreen_window = QWidget()
            self.fullscreen_window.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            self.fullscreen_window.setWindowState(Qt.WindowState.WindowFullScreen)
            
            # Create layout for fullscreen window
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            
            # Move video label to fullscreen window
            self.layout().removeWidget(self.video_label)
            layout.addWidget(self.video_label)
            
            self.fullscreen_window.setLayout(layout)
            self.fullscreen_window.showFullScreen()
            
            # Add ESC key handler
            def keyPressEvent(event):
                if event.key() == Qt.Key.Key_Escape:
                    self._toggle_fullscreen()
            
            self.fullscreen_window.keyPressEvent = keyPressEvent
            
            self.fullscreen_btn.setText("⛶ Exit Fullscreen")
            self.is_fullscreen = True
            
            # Refresh display
            if self.current_frame is not None:
                self.refresh_display()
    
    def set_fps_display(self, enabled: bool):
        """Enable/disable FPS counter display"""
        self.show_fps = enabled
        if self.current_frame is not None:
            self.refresh_display()
    
    def _update_fps(self):
        """Update FPS counter"""
        current_time = time.time()
        delta = current_time - self.last_frame_time
        
        if delta > 0:
            instant_fps = 1.0 / delta
            self.fps_history.append(instant_fps)
            
            # Keep only last 30 frames for smoothing
            if len(self.fps_history) > 30:
                self.fps_history.pop(0)
            
            # Calculate average FPS
            self.current_fps = sum(self.fps_history) / len(self.fps_history)
        
        self.last_frame_time = current_time
    
    def _draw_fps(self, frame: np.ndarray) -> np.ndarray:
        """Draw FPS counter (top-left corner)"""
        frame_draw = frame.copy()
        
        # Update FPS
        self._update_fps()
        
        # Draw semi-transparent background
        overlay = frame_draw.copy()
        cv2.rectangle(overlay, (5, 5), (150, 45), (0, 0, 0), -1)
        frame_draw = cv2.addWeighted(frame_draw, 0.6, overlay, 0.4, 0)
        
        # Draw FPS text
        fps_text = f"FPS: {self.current_fps:.1f}"
        cv2.putText(frame_draw, fps_text, (15, 30), cv2.FONT_HERSHEY_SIMPLEX,
                   0.7, (0, 255, 0), 2, cv2.LINE_AA)
        
        return frame_draw
        
    def _capture_screenshot(self):
        """Capture current frame as screenshot"""
        if self.current_frame is not None:
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"output/screenshots/frame_{timestamp}.jpg"
            
            import os
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            # Save current display
            cv2.imwrite(filename, cv2.cvtColor(self.current_frame, cv2.COLOR_RGB2BGR))
            print(f"Screenshot saved: {filename}")
            
    def _on_video_clicked(self, event):
        """Handle video click events"""
        x = event.pos().x()
        y = event.pos().y()
        
        # Convert to frame coordinates
        if self.current_frame is not None:
            label_w = self.video_label.width()
            label_h = self.video_label.height()
            frame_h, frame_w = self.current_frame.shape[:2]
            
            frame_x = int(x * frame_w / label_w)
            frame_y = int(y * frame_h / label_h)
            
            self.frame_clicked.emit(frame_x, frame_y)
            
    def clear(self):
        """Clear the display"""
        self.current_frame = None
        self.depth_map = None
        self.detections = []
        self.telemetry = {}
        self.state_info = ""
        self.fps_history = []
        self.video_label.clear()
        self.video_label.setText("No Video Feed")
