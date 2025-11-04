"""
Obstacle Avoidance Control Panel for GUI

Provides:
- Enable/disable avoidance
- Start/stop/pause/resume controls
- Real-time status and statistics
- Manual avoidance controls
- Parameter adjustment
"""

from typing import Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QGroupBox, QPushButton, QComboBox, QMessageBox,
                             QSlider, QSpinBox, QDoubleSpinBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont


class AvoidanceControlPanel(QWidget):
    """
    Obstacle avoidance control panel with real-time status and controls
    """

    # Signals
    avoidance_enabled_changed = pyqtSignal(bool)  # Enable/disable
    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    resume_requested = pyqtSignal()
    emergency_stop_requested = pyqtSignal()
    manual_avoid_left_requested = pyqtSignal(float)  # intensity
    manual_avoid_right_requested = pyqtSignal(float)  # intensity
    manual_stop_requested = pyqtSignal()
    parameters_changed = pyqtSignal(dict)  # config dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self.avoidance_controller = None  # Reference to MAVLinkAvoidanceController
        self.enabled = False
        self.current_state = "idle"

        self.init_ui()

        # Update timer for status display
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status_display)
        self.update_timer.start(100)  # Update at 10Hz

    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # ===== STATUS DISPLAY =====
        status_group = QGroupBox("Avoidance Status")
        status_layout = QVBoxLayout()

        # Enable/disable
        enable_layout = QHBoxLayout()
        self.enable_checkbox = QCheckBox("Enable Obstacle Avoidance")
        self.enable_checkbox.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.enable_checkbox.stateChanged.connect(self._on_enable_changed)
        enable_layout.addWidget(self.enable_checkbox)
        enable_layout.addStretch()
        status_layout.addLayout(enable_layout)

        # State display
        state_layout = QHBoxLayout()
        state_layout.addWidget(QLabel("State:"))
        self.state_label = QLabel("IDLE")
        self.state_label.setStyleSheet(
            "font-weight: bold; font-size: 12pt; color: #666; padding: 5px; "
            "background-color: #f0f0f0; border-radius: 3px;"
        )
        state_layout.addWidget(self.state_label)
        state_layout.addStretch()
        status_layout.addLayout(state_layout)

        # Statistics
        stats_layout = QVBoxLayout()

        obstacles_layout = QHBoxLayout()
        obstacles_layout.addWidget(QLabel("Obstacles Detected:"))
        self.obstacles_label = QLabel("0")
        self.obstacles_label.setStyleSheet("font-weight: bold; color: #0056b3;")
        obstacles_layout.addWidget(self.obstacles_label)
        obstacles_layout.addStretch()
        stats_layout.addLayout(obstacles_layout)

        maneuvers_layout = QHBoxLayout()
        maneuvers_layout.addWidget(QLabel("Avoidance Maneuvers:"))
        self.maneuvers_label = QLabel("0")
        self.maneuvers_label.setStyleSheet("font-weight: bold; color: #28a745;")
        maneuvers_layout.addWidget(self.maneuvers_label)
        maneuvers_layout.addStretch()
        stats_layout.addLayout(maneuvers_layout)

        emergency_layout = QHBoxLayout()
        emergency_layout.addWidget(QLabel("Emergency Stops:"))
        self.emergency_label = QLabel("0")
        self.emergency_label.setStyleSheet("font-weight: bold; color: #dc3545;")
        emergency_layout.addWidget(self.emergency_label)
        emergency_layout.addStretch()
        stats_layout.addLayout(emergency_layout)

        status_layout.addLayout(stats_layout)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # ===== CONTROL BUTTONS =====
        control_group = QGroupBox("Avoidance Controls")
        control_layout = QVBoxLayout()

        # Start/Stop/Pause/Resume buttons
        button_row1 = QHBoxLayout()

        self.start_button = QPushButton("▶ Start")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.start_button.clicked.connect(self._on_start_clicked)
        button_row1.addWidget(self.start_button)

        self.stop_button = QPushButton("⏹ Stop")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        button_row1.addWidget(self.stop_button)

        control_layout.addLayout(button_row1)

        button_row2 = QHBoxLayout()

        self.pause_button = QPushButton("⏸ Pause")
        self.pause_button.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.pause_button.clicked.connect(self.pause_requested.emit)
        button_row2.addWidget(self.pause_button)

        self.resume_button = QPushButton("▶ Resume")
        self.resume_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.resume_button.clicked.connect(self.resume_requested.emit)
        button_row2.addWidget(self.resume_button)

        control_layout.addLayout(button_row2)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # ===== MANUAL CONTROLS =====
        manual_group = QGroupBox("Manual Override")
        manual_layout = QVBoxLayout()

        manual_info = QLabel("Manual avoidance commands (use with caution):")
        manual_info.setStyleSheet("color: #666; font-size: 9pt;")
        manual_layout.addWidget(manual_info)

        # Intensity slider
        intensity_layout = QHBoxLayout()
        intensity_layout.addWidget(QLabel("Intensity:"))
        self.intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.intensity_slider.setMinimum(10)
        self.intensity_slider.setMaximum(100)
        self.intensity_slider.setValue(50)
        self.intensity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.intensity_slider.setTickInterval(10)
        intensity_layout.addWidget(self.intensity_slider)
        self.intensity_value_label = QLabel("0.5")
        self.intensity_value_label.setStyleSheet("font-weight: bold;")
        intensity_layout.addWidget(self.intensity_value_label)
        self.intensity_slider.valueChanged.connect(
            lambda v: self.intensity_value_label.setText(f"{v/100:.1f}")
        )
        manual_layout.addLayout(intensity_layout)

        # Manual direction buttons
        manual_button_layout = QHBoxLayout()

        self.manual_left_button = QPushButton("⬅ Avoid Left")
        self.manual_left_button.clicked.connect(self._on_manual_left)
        manual_button_layout.addWidget(self.manual_left_button)

        self.manual_stop_button = QPushButton("⏹ Stop")
        self.manual_stop_button.clicked.connect(self.manual_stop_requested.emit)
        manual_button_layout.addWidget(self.manual_stop_button)

        self.manual_right_button = QPushButton("➡ Avoid Right")
        self.manual_right_button.clicked.connect(self._on_manual_right)
        manual_button_layout.addWidget(self.manual_right_button)

        manual_layout.addLayout(manual_button_layout)

        manual_group.setLayout(manual_layout)
        layout.addWidget(manual_group)

        # ===== PARAMETERS =====
        params_group = QGroupBox("Parameters")
        params_layout = QVBoxLayout()

        # Max velocity
        max_vel_layout = QHBoxLayout()
        max_vel_layout.addWidget(QLabel("Max Velocity:"))
        self.max_vel_spinbox = QDoubleSpinBox()
        self.max_vel_spinbox.setRange(0.5, 5.0)
        self.max_vel_spinbox.setSingleStep(0.1)
        self.max_vel_spinbox.setValue(2.0)
        self.max_vel_spinbox.setSuffix(" m/s")
        self.max_vel_spinbox.valueChanged.connect(self._on_parameters_changed)
        max_vel_layout.addWidget(self.max_vel_spinbox)
        max_vel_layout.addStretch()
        params_layout.addLayout(max_vel_layout)

        # Avoidance velocity
        avoid_vel_layout = QHBoxLayout()
        avoid_vel_layout.addWidget(QLabel("Avoidance Velocity:"))
        self.avoid_vel_spinbox = QDoubleSpinBox()
        self.avoid_vel_spinbox.setRange(0.5, 3.0)
        self.avoid_vel_spinbox.setSingleStep(0.1)
        self.avoid_vel_spinbox.setValue(1.0)
        self.avoid_vel_spinbox.setSuffix(" m/s")
        self.avoid_vel_spinbox.valueChanged.connect(self._on_parameters_changed)
        avoid_vel_layout.addWidget(self.avoid_vel_spinbox)
        avoid_vel_layout.addStretch()
        params_layout.addLayout(avoid_vel_layout)

        # Emergency distance
        emergency_dist_layout = QHBoxLayout()
        emergency_dist_layout.addWidget(QLabel("Emergency Distance:"))
        self.emergency_dist_spinbox = QDoubleSpinBox()
        self.emergency_dist_spinbox.setRange(0.5, 5.0)
        self.emergency_dist_spinbox.setSingleStep(0.1)
        self.emergency_dist_spinbox.setValue(1.0)
        self.emergency_dist_spinbox.setSuffix(" m")
        self.emergency_dist_spinbox.valueChanged.connect(self._on_parameters_changed)
        emergency_dist_layout.addWidget(self.emergency_dist_spinbox)
        emergency_dist_layout.addStretch()
        params_layout.addLayout(emergency_dist_layout)

        # Enable emergency stop
        self.emergency_stop_checkbox = QCheckBox("Enable Emergency Stop")
        self.emergency_stop_checkbox.setChecked(True)
        self.emergency_stop_checkbox.stateChanged.connect(self._on_parameters_changed)
        params_layout.addWidget(self.emergency_stop_checkbox)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # ===== CONNECTION STATUS =====
        self.connection_label = QLabel("⚠ Avoidance controller not initialized")
        self.connection_label.setStyleSheet(
            "color: red; font-weight: bold; padding: 8px; "
            "background-color: #ffe6e6; border-radius: 5px;"
        )
        layout.addWidget(self.connection_label)

        layout.addStretch()
        self.setLayout(layout)

        # Initially disable controls
        self._update_control_states()

    def set_avoidance_controller(self, controller):
        """Set reference to MAVLinkAvoidanceController"""
        self.avoidance_controller = controller
        self._update_connection_status()

        # Load current parameters
        if controller:
            self.max_vel_spinbox.setValue(controller.max_velocity)
            self.avoid_vel_spinbox.setValue(controller.avoidance_velocity)
            self.emergency_dist_spinbox.setValue(controller.emergency_distance)
            self.emergency_stop_checkbox.setChecked(controller.enable_emergency_stop)

    def _update_status_display(self):
        """Update status display from controller"""
        if not self.avoidance_controller:
            return

        try:
            status = self.avoidance_controller.get_status()

            # Update state label
            state = status.get('state', 'idle').upper()
            if state != self.current_state:
                self.current_state = state
                self.state_label.setText(state)

                # Color based on state
                if state == "IDLE":
                    color = "#666"
                    bg = "#f0f0f0"
                elif state == "MONITORING":
                    color = "#0056b3"
                    bg = "#e6f2ff"
                elif state == "AVOIDING":
                    color = "#ffc107"
                    bg = "#fff8e6"
                elif state == "EMERGENCY_STOP":
                    color = "#dc3545"
                    bg = "#ffe6e6"
                elif state == "PAUSED":
                    color = "#6c757d"
                    bg = "#f0f0f0"
                else:
                    color = "#666"
                    bg = "#f0f0f0"

                self.state_label.setStyleSheet(
                    f"font-weight: bold; font-size: 12pt; color: {color}; "
                    f"padding: 5px; background-color: {bg}; border-radius: 3px;"
                )

            # Update statistics
            self.obstacles_label.setText(str(status.get('obstacles_detected', 0)))
            self.maneuvers_label.setText(str(status.get('avoidance_maneuvers', 0)))
            self.emergency_label.setText(str(status.get('emergency_stops', 0)))

            # Update control states
            self._update_control_states()

        except Exception as e:
            print(f"Error updating avoidance status: {e}")

    def _update_connection_status(self):
        """Update connection status display"""
        if self.avoidance_controller:
            self.connection_label.setText("✓ Avoidance controller ready")
            self.connection_label.setStyleSheet(
                "color: green; font-weight: bold; padding: 8px; "
                "background-color: #e6ffe6; border-radius: 5px;"
            )
        else:
            self.connection_label.setText("⚠ Avoidance controller not initialized")
            self.connection_label.setStyleSheet(
                "color: red; font-weight: bold; padding: 8px; "
                "background-color: #ffe6e6; border-radius: 5px;"
            )

        self._update_control_states()

    def _update_control_states(self):
        """Enable/disable controls based on current state"""
        has_controller = self.avoidance_controller is not None

        if not has_controller:
            # Disable everything if no controller
            self.enable_checkbox.setEnabled(False)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(False)
            self.manual_left_button.setEnabled(False)
            self.manual_right_button.setEnabled(False)
            self.manual_stop_button.setEnabled(False)
            return

        # Enable checkbox always available
        self.enable_checkbox.setEnabled(True)

        # Get current state
        try:
            status = self.avoidance_controller.get_status()
            enabled = status.get('enabled', False)
            state = status.get('state', 'idle')

            # Start button: enabled when not running
            self.start_button.setEnabled(enabled and state == 'idle')

            # Stop button: enabled when running
            self.stop_button.setEnabled(enabled and state != 'idle')

            # Pause button: enabled when monitoring or avoiding
            self.pause_button.setEnabled(
                enabled and state in ['monitoring', 'avoiding']
            )

            # Resume button: enabled when paused
            self.resume_button.setEnabled(enabled and state == 'paused')

            # Manual controls: enabled when controller is active
            manual_enabled = enabled and state != 'idle'
            self.manual_left_button.setEnabled(manual_enabled)
            self.manual_right_button.setEnabled(manual_enabled)
            self.manual_stop_button.setEnabled(manual_enabled)

        except Exception as e:
            print(f"Error updating control states: {e}")

    def _on_enable_changed(self, state):
        """Handle enable checkbox change"""
        self.enabled = state == Qt.CheckState.Checked.value
        self.avoidance_enabled_changed.emit(self.enabled)
        self._update_control_states()

    def _on_start_clicked(self):
        """Handle start button click"""
        if not self.avoidance_controller:
            QMessageBox.warning(self, "Not Ready", "Avoidance controller not initialized")
            return

        reply = QMessageBox.question(
            self,
            "Start Avoidance",
            "Start obstacle avoidance controller?\n\n"
            "The drone will:\n"
            "• Switch to GUIDED mode\n"
            "• Monitor for obstacles\n"
            "• Execute avoidance maneuvers automatically\n\n"
            "Ensure area is safe and you can take manual control if needed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.start_requested.emit()

    def _on_manual_left(self):
        """Handle manual left button"""
        intensity = self.intensity_slider.value() / 100.0
        self.manual_avoid_left_requested.emit(intensity)

    def _on_manual_right(self):
        """Handle manual right button"""
        intensity = self.intensity_slider.value() / 100.0
        self.manual_avoid_right_requested.emit(intensity)

    def _on_parameters_changed(self):
        """Handle parameter changes"""
        params = {
            'max_velocity': self.max_vel_spinbox.value(),
            'avoidance_velocity': self.avoid_vel_spinbox.value(),
            'emergency_distance': self.emergency_dist_spinbox.value(),
            'enable_emergency_stop': self.emergency_stop_checkbox.isChecked()
        }
        self.parameters_changed.emit(params)

        # Update controller if available
        if self.avoidance_controller:
            self.avoidance_controller.max_velocity = params['max_velocity']
            self.avoidance_controller.avoidance_velocity = params['avoidance_velocity']
            self.avoidance_controller.emergency_distance = params['emergency_distance']
            self.avoidance_controller.enable_emergency_stop = params['enable_emergency_stop']
