"""
Task Control Panel for Competition Task Execution

Provides interface for:
- Task selection from available tasks
- Task configuration (parameters, thresholds)
- Start/stop/pause controls
- Live scoring display
- Task progress tracking
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QComboBox, QLabel, QGroupBox, QSpinBox, QDoubleSpinBox,
                             QCheckBox, QTextEdit, QProgressBar, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class TaskControlPanel(QWidget):
    """
    Control panel for task management
    """
    
    # Signals
    task_start_requested = pyqtSignal(str, dict)  # task_name, config
    task_stop_requested = pyqtSignal()
    task_pause_requested = pyqtSignal()
    task_resume_requested = pyqtSignal()
    config_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_task = None
        self.task_running = False
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        
        # Task selection group
        selection_group = QGroupBox("Task Selection")
        selection_layout = QVBoxLayout()
        
        self.task_combo = QComboBox()
        self.task_combo.addItems([
            "Target Search",
            "Waypoint Navigation",
            "Obstacle Course",
            "Circular Flight Test",
            "Precision Landing",
            "Autonomous Wet-Capture",
            "Custom Competition Task"
        ])
        self.task_combo.currentTextChanged.connect(self._on_task_changed)
        selection_layout.addWidget(QLabel("Select Task:"))
        selection_layout.addWidget(self.task_combo)
        
        # Task description
        self.task_description = QLabel("Search for red circular targets and log GPS coordinates.")
        self.task_description.setWordWrap(True)
        self.task_description.setStyleSheet("color: #888; font-style: italic;")
        selection_layout.addWidget(self.task_description)
        
        selection_group.setLayout(selection_layout)
        main_layout.addWidget(selection_group)
        
        # Configuration group (scrollable)
        config_group = QGroupBox("Task Configuration")
        config_scroll = QScrollArea()
        config_scroll.setWidgetResizable(True)
        config_scroll.setMaximumHeight(300)
        
        config_widget = QWidget()
        self.config_layout = QVBoxLayout()
        config_widget.setLayout(self.config_layout)
        config_scroll.setWidget(config_widget)
        
        config_group_layout = QVBoxLayout()
        config_group_layout.addWidget(config_scroll)
        config_group.setLayout(config_group_layout)
        main_layout.addWidget(config_group)
        
        # Initialize default config
        self._build_config_ui("Target Search")
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ Start Task")
        self.start_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
        self.start_btn.clicked.connect(self._on_start_clicked)
        control_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        control_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #dc3545; color: white;")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        control_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(control_layout)
        
        # Progress and status
        status_group = QGroupBox("Task Status")
        status_group.setMinimumHeight(280)  # Ensure enough space
        status_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(25)  # Taller progress bar
        status_layout.addWidget(QLabel("Progress:"))
        status_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Status: Idle")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 11pt; padding: 5px;")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        self.score_label = QLabel("Score: 0.0 points")
        self.score_label.setStyleSheet("font-size: 13pt; color: #007bff; padding: 5px;")
        self.score_label.setWordWrap(True)
        status_layout.addWidget(self.score_label)
        
        self.task_info = QTextEdit()
        self.task_info.setReadOnly(True)
        self.task_info.setMinimumHeight(120)  # Larger info area
        self.task_info.setPlaceholderText("Task information will appear here...")
        status_layout.addWidget(self.task_info)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
        
    def _build_config_ui(self, task_name: str):
        """Build configuration UI based on task"""
        # Clear existing config
        while self.config_layout.count():
            item = self.config_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Add task-specific config widgets
        if task_name == "Target Search":
            self._add_target_search_config()
        elif task_name == "Waypoint Navigation":
            self._add_waypoint_config()
        elif task_name == "Obstacle Course":
            self._add_obstacle_config()
        elif task_name == "Circular Flight Test":
            self._add_circular_flight_config()
        elif task_name == "Precision Landing":
            self._add_landing_config()
        elif task_name == "Autonomous Wet-Capture":
            self._add_wet_capture_config()
        else:
            self._add_custom_config()
            
    def _add_target_search_config(self):
        """Add Target Search task configuration"""
        # Max targets
        self.config_layout.addWidget(QLabel("Max Targets:"))
        max_targets = QSpinBox()
        max_targets.setRange(1, 20)
        max_targets.setValue(5)
        max_targets.setObjectName("max_targets")
        self.config_layout.addWidget(max_targets)
        
        # Search timeout
        self.config_layout.addWidget(QLabel("Search Timeout (seconds):"))
        timeout = QSpinBox()
        timeout.setRange(30, 600)
        timeout.setValue(300)
        timeout.setObjectName("timeout")
        self.config_layout.addWidget(timeout)
        
        # Confidence threshold
        self.config_layout.addWidget(QLabel("Detection Confidence:"))
        confidence = QDoubleSpinBox()
        confidence.setRange(0.1, 1.0)
        confidence.setValue(0.6)
        confidence.setSingleStep(0.05)
        confidence.setObjectName("confidence_threshold")
        self.config_layout.addWidget(confidence)
        
        # Auto capture
        auto_capture = QCheckBox("Auto-capture target photos")
        auto_capture.setChecked(True)
        auto_capture.setObjectName("auto_capture")
        self.config_layout.addWidget(auto_capture)
        
    def _add_waypoint_config(self):
        """Add Waypoint Navigation configuration"""
        self.config_layout.addWidget(QLabel("Waypoint Tolerance (meters):"))
        tolerance = QDoubleSpinBox()
        tolerance.setRange(0.5, 10.0)
        tolerance.setValue(2.0)
        tolerance.setObjectName("waypoint_tolerance")
        self.config_layout.addWidget(tolerance)
        
        self.config_layout.addWidget(QLabel("Max Altitude (meters):"))
        max_alt = QSpinBox()
        max_alt.setRange(5, 100)
        max_alt.setValue(30)
        max_alt.setObjectName("max_altitude")
        self.config_layout.addWidget(max_alt)
        
        self.config_layout.addWidget(QLabel("Cruise Speed (m/s):"))
        speed = QDoubleSpinBox()
        speed.setRange(1.0, 15.0)
        speed.setValue(5.0)
        speed.setObjectName("cruise_speed")
        self.config_layout.addWidget(speed)
        
    def _add_obstacle_config(self):
        """Add Obstacle Course configuration"""
        self.config_layout.addWidget(QLabel("Min Safe Distance (meters):"))
        safe_dist = QDoubleSpinBox()
        safe_dist.setRange(0.5, 5.0)
        safe_dist.setValue(2.0)
        safe_dist.setObjectName("min_safe_distance")
        self.config_layout.addWidget(safe_dist)
        
        self.config_layout.addWidget(QLabel("Avoidance Speed (m/s):"))
        speed = QDoubleSpinBox()
        speed.setRange(0.5, 5.0)
        speed.setValue(2.0)
        speed.setObjectName("avoidance_speed")
        self.config_layout.addWidget(speed)
        
        emergency_stop = QCheckBox("Emergency stop on collision risk")
        emergency_stop.setChecked(True)
        emergency_stop.setObjectName("emergency_stop")
        self.config_layout.addWidget(emergency_stop)
        
    def _add_circular_flight_config(self):
        """Add Circular Flight Test configuration"""
        self.config_layout.addWidget(QLabel("Circle Radius (meters):"))
        radius = QDoubleSpinBox()
        radius.setRange(1.0, 50.0)
        radius.setValue(10.0)
        radius.setDecimals(1)
        radius.setObjectName("circle_radius")
        self.config_layout.addWidget(radius)
        
        self.config_layout.addWidget(QLabel("Flight Altitude (meters):"))
        altitude = QDoubleSpinBox()
        altitude.setRange(1.0, 50.0)
        altitude.setValue(5.0)
        altitude.setDecimals(1)
        altitude.setObjectName("flight_altitude")
        self.config_layout.addWidget(altitude)
        
        self.config_layout.addWidget(QLabel("Flight Speed (m/s):"))
        speed = QDoubleSpinBox()
        speed.setRange(0.5, 10.0)
        speed.setValue(2.0)
        speed.setDecimals(1)
        speed.setObjectName("flight_speed")
        self.config_layout.addWidget(speed)
        
        self.config_layout.addWidget(QLabel("Number of Circles:"))
        num_circles = QSpinBox()
        num_circles.setRange(1, 20)
        num_circles.setValue(3)
        num_circles.setObjectName("num_circles")
        self.config_layout.addWidget(num_circles)
        
        obstacle_avoidance = QCheckBox("Enable Obstacle Avoidance")
        obstacle_avoidance.setChecked(True)
        obstacle_avoidance.setObjectName("obstacle_avoidance")
        self.config_layout.addWidget(obstacle_avoidance)
        
        self.config_layout.addWidget(QLabel("Safe Distance (meters):"))
        safe_dist = QDoubleSpinBox()
        safe_dist.setRange(0.5, 10.0)
        safe_dist.setValue(3.0)
        safe_dist.setDecimals(1)
        safe_dist.setObjectName("safe_distance")
        self.config_layout.addWidget(safe_dist)
    
    def _add_landing_config(self):
        """Add Precision Landing configuration"""
        self.config_layout.addWidget(QLabel("Landing Pad Size (meters):"))
        pad_size = QDoubleSpinBox()
        pad_size.setRange(0.5, 5.0)
        pad_size.setValue(1.5)
        pad_size.setObjectName("pad_size")
        self.config_layout.addWidget(pad_size)
        
        self.config_layout.addWidget(QLabel("Descent Rate (m/s):"))
        descent = QDoubleSpinBox()
        descent.setRange(0.1, 2.0)
        descent.setValue(0.5)
        descent.setObjectName("descent_rate")
        self.config_layout.addWidget(descent)
        
        self.config_layout.addWidget(QLabel("Centering Tolerance (pixels):"))
        tolerance = QSpinBox()
        tolerance.setRange(5, 50)
        tolerance.setValue(20)
        tolerance.setObjectName("centering_tolerance")
        self.config_layout.addWidget(tolerance)
        
    def _add_wet_capture_config(self):
        """Add Autonomous Wet-Capture configuration"""
        self.config_layout.addWidget(QLabel("Approach Distance (meters):"))
        approach_dist = QDoubleSpinBox()
        approach_dist.setRange(0.3, 2.0)
        approach_dist.setValue(0.7)
        approach_dist.setObjectName("approach_distance")
        self.config_layout.addWidget(approach_dist)
        
        self.config_layout.addWidget(QLabel("Stabilization Time (seconds):"))
        stab_time = QDoubleSpinBox()
        stab_time.setRange(0.5, 5.0)
        stab_time.setValue(2.0)
        stab_time.setObjectName("stabilization_time")
        self.config_layout.addWidget(stab_time)
        
        self.config_layout.addWidget(QLabel("Water Duration (seconds):"))
        water_duration = QDoubleSpinBox()
        water_duration.setRange(0.5, 5.0)
        water_duration.setValue(2.0)
        water_duration.setObjectName("water_duration")
        self.config_layout.addWidget(water_duration)
        
        auto_upload = QCheckBox("Auto-upload deliverables")
        auto_upload.setChecked(True)
        auto_upload.setObjectName("auto_upload")
        self.config_layout.addWidget(auto_upload)
        
    def _add_custom_config(self):
        """Add generic custom configuration"""
        self.config_layout.addWidget(QLabel("No specific configuration available."))
        self.config_layout.addWidget(QLabel("Use default settings."))
        
    def _on_task_changed(self, task_name: str):
        """Handle task selection change"""
        self._build_config_ui(task_name)
        
        # Update task description
        descriptions = {
            "Target Search": "Search for red circular targets and log GPS coordinates with photo capture.",
            "Waypoint Navigation": "Navigate through GPS waypoints with specified tolerance and speed.",
            "Obstacle Course": "Avoid obstacles using depth sensing and safe distance thresholds.",
            "Circular Flight Test": "Fly in circles with obstacle avoidance to test autonomous navigation.",
            "Precision Landing": "Detect landing pad and perform centered precision landing.",
            "Autonomous Wet-Capture": "Autonomously approach, aim, wet, capture, and upload target deliverables.",
            "Custom Competition Task": "Configure custom task parameters for competition execution."
        }
        self.task_description.setText(descriptions.get(task_name, "No description available."))
        
    def _on_start_clicked(self):
        """Handle start button click"""
        task_name = self.task_combo.currentText()
        config = self._get_current_config()
        
        self.task_running = True
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.task_combo.setEnabled(False)
        
        self.status_label.setText("Status: Running")
        self.status_label.setStyleSheet("font-weight: bold; color: #28a745;")
        
        self.task_start_requested.emit(task_name, config)
        
    def _on_pause_clicked(self):
        """Handle pause button click"""
        if self.pause_btn.text() == "⏸ Pause":
            self.pause_btn.setText("▶ Resume")
            self.status_label.setText("Status: Paused")
            self.status_label.setStyleSheet("font-weight: bold; color: #ffc107;")
            self.task_pause_requested.emit()
        else:
            self.pause_btn.setText("⏸ Pause")
            self.status_label.setText("Status: Running")
            self.status_label.setStyleSheet("font-weight: bold; color: #28a745;")
            self.task_resume_requested.emit()
            
    def _on_stop_clicked(self):
        """Handle stop button click"""
        self.task_running = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸ Pause")
        self.stop_btn.setEnabled(False)
        self.task_combo.setEnabled(True)
        
        self.status_label.setText("Status: Stopped")
        self.status_label.setStyleSheet("font-weight: bold; color: #dc3545;")
        self.progress_bar.setValue(0)
        
        self.task_stop_requested.emit()
        
    def _get_current_config(self) -> Dict[str, Any]:
        """Extract current configuration from UI widgets"""
        config = {}
        
        # Iterate through config widgets
        for i in range(self.config_layout.count()):
            widget = self.config_layout.itemAt(i).widget()
            if widget and hasattr(widget, 'objectName') and widget.objectName():
                name = widget.objectName()
                
                if isinstance(widget, QSpinBox):
                    config[name] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    config[name] = widget.value()
                elif isinstance(widget, QCheckBox):
                    config[name] = widget.isChecked()
                    
        return config
        
    def update_progress(self, progress: float):
        """Update progress bar (0-100)"""
        self.progress_bar.setValue(int(progress))
        
    def update_score(self, score: float):
        """Update score display"""
        self.score_label.setText(f"Score: {score:.1f} points")
        
    def update_status(self, status: str, details: str = ""):
        """Update status label and info"""
        self.status_label.setText(f"Status: {status}")
        
        if details:
            self.task_info.append(details)
            # Auto-scroll to bottom
            self.task_info.verticalScrollBar().setValue(
                self.task_info.verticalScrollBar().maximum()
            )
            
    def reset(self):
        """Reset control panel to initial state"""
        self.task_running = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸ Pause")
        self.stop_btn.setEnabled(False)
        self.task_combo.setEnabled(True)
        
        self.status_label.setText("Status: Idle")
        self.status_label.setStyleSheet("font-weight: bold;")
        self.score_label.setText("Score: 0.0 points")
        self.progress_bar.setValue(0)
        self.task_info.clear()
