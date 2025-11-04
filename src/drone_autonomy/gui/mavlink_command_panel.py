"""
MAVLink Command Execution Panel for GUI

Provides:
- Takeoff/Land controls
- RTL (Return to Launch)
- Direct velocity commands (body frame and NED frame)
- Position commands
- Yaw control
- Command history log
"""

from typing import Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QGroupBox, QPushButton, QComboBox, QMessageBox,
                             QSlider, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QTextEdit, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class MAVLinkCommandPanel(QWidget):
    """
    MAVLink command execution panel with comprehensive flight controls
    """

    # Signals
    takeoff_requested = pyqtSignal(float)  # altitude
    land_requested = pyqtSignal()
    rtl_requested = pyqtSignal()
    velocity_body_requested = pyqtSignal(float, float, float, float)  # vx, vy, vz, yaw_rate
    velocity_ned_requested = pyqtSignal(float, float, float, float)  # vx, vy, vz, yaw_rate
    velocity_with_yaw_requested = pyqtSignal(float, float, float, float, str)  # vx, vy, vz, yaw, frame
    goto_position_requested = pyqtSignal(float, float, float)  # lat, lon, alt

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mavlink = None  # Reference to MAVLink telemetry

        self.init_ui()

    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # ===== BASIC FLIGHT COMMANDS =====
        basic_group = QGroupBox("Basic Flight Commands")
        basic_layout = QVBoxLayout()

        # Takeoff
        takeoff_layout = QHBoxLayout()
        takeoff_layout.addWidget(QLabel("Takeoff Altitude:"))
        self.takeoff_alt_spinbox = QDoubleSpinBox()
        self.takeoff_alt_spinbox.setRange(1.0, 50.0)
        self.takeoff_alt_spinbox.setSingleStep(0.5)
        self.takeoff_alt_spinbox.setValue(5.0)
        self.takeoff_alt_spinbox.setSuffix(" m")
        takeoff_layout.addWidget(self.takeoff_alt_spinbox)

        self.takeoff_button = QPushButton("🚁 Takeoff")
        self.takeoff_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.takeoff_button.clicked.connect(self._on_takeoff_clicked)
        takeoff_layout.addWidget(self.takeoff_button)
        basic_layout.addLayout(takeoff_layout)

        # Land and RTL buttons
        land_rtl_layout = QHBoxLayout()

        self.land_button = QPushButton("🛬 Land")
        self.land_button.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.land_button.clicked.connect(self._on_land_clicked)
        land_rtl_layout.addWidget(self.land_button)

        self.rtl_button = QPushButton("🏠 Return to Launch")
        self.rtl_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.rtl_button.clicked.connect(self._on_rtl_clicked)
        land_rtl_layout.addWidget(self.rtl_button)

        basic_layout.addLayout(land_rtl_layout)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # ===== VELOCITY COMMANDS =====
        velocity_group = QGroupBox("Velocity Commands")
        velocity_layout = QVBoxLayout()

        # Frame selection
        frame_layout = QHBoxLayout()
        frame_layout.addWidget(QLabel("Frame:"))
        self.frame_combo = QComboBox()
        self.frame_combo.addItems(["Body Frame", "NED Frame"])
        self.frame_combo.setStyleSheet("padding: 5px;")
        frame_layout.addWidget(self.frame_combo)
        frame_layout.addStretch()
        velocity_layout.addLayout(frame_layout)

        # Velocity inputs
        vel_x_layout = QHBoxLayout()
        vel_x_layout.addWidget(QLabel("Forward (X):"))
        self.vel_x_spinbox = QDoubleSpinBox()
        self.vel_x_spinbox.setRange(-5.0, 5.0)
        self.vel_x_spinbox.setSingleStep(0.1)
        self.vel_x_spinbox.setValue(0.0)
        self.vel_x_spinbox.setSuffix(" m/s")
        vel_x_layout.addWidget(self.vel_x_spinbox)
        velocity_layout.addLayout(vel_x_layout)

        vel_y_layout = QHBoxLayout()
        vel_y_layout.addWidget(QLabel("Right (Y):"))
        self.vel_y_spinbox = QDoubleSpinBox()
        self.vel_y_spinbox.setRange(-5.0, 5.0)
        self.vel_y_spinbox.setSingleStep(0.1)
        self.vel_y_spinbox.setValue(0.0)
        self.vel_y_spinbox.setSuffix(" m/s")
        vel_y_layout.addWidget(self.vel_y_spinbox)
        velocity_layout.addLayout(vel_y_layout)

        vel_z_layout = QHBoxLayout()
        vel_z_layout.addWidget(QLabel("Down (Z):"))
        self.vel_z_spinbox = QDoubleSpinBox()
        self.vel_z_spinbox.setRange(-3.0, 3.0)
        self.vel_z_spinbox.setSingleStep(0.1)
        self.vel_z_spinbox.setValue(0.0)
        self.vel_z_spinbox.setSuffix(" m/s")
        vel_z_layout.addWidget(self.vel_z_spinbox)
        velocity_layout.addLayout(vel_z_layout)

        yaw_rate_layout = QHBoxLayout()
        yaw_rate_layout.addWidget(QLabel("Yaw Rate:"))
        self.yaw_rate_spinbox = QDoubleSpinBox()
        self.yaw_rate_spinbox.setRange(-180.0, 180.0)
        self.yaw_rate_spinbox.setSingleStep(5.0)
        self.yaw_rate_spinbox.setValue(0.0)
        self.yaw_rate_spinbox.setSuffix(" deg/s")
        yaw_rate_layout.addWidget(self.yaw_rate_spinbox)
        velocity_layout.addLayout(yaw_rate_layout)

        # Send velocity button
        vel_button_layout = QHBoxLayout()
        self.send_velocity_button = QPushButton("➡ Send Velocity Command")
        self.send_velocity_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.send_velocity_button.clicked.connect(self._on_send_velocity_clicked)
        vel_button_layout.addWidget(self.send_velocity_button)

        self.stop_button = QPushButton("⏹ Stop (Zero Velocity)")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        vel_button_layout.addWidget(self.stop_button)

        velocity_layout.addLayout(vel_button_layout)

        velocity_group.setLayout(velocity_layout)
        layout.addWidget(velocity_group)

        # ===== YAW CONTROL =====
        yaw_group = QGroupBox("Yaw Control")
        yaw_layout = QVBoxLayout()

        yaw_input_layout = QHBoxLayout()
        yaw_input_layout.addWidget(QLabel("Target Yaw:"))
        self.yaw_spinbox = QDoubleSpinBox()
        self.yaw_spinbox.setRange(0.0, 360.0)
        self.yaw_spinbox.setSingleStep(5.0)
        self.yaw_spinbox.setValue(0.0)
        self.yaw_spinbox.setSuffix(" deg")
        self.yaw_spinbox.setWrapping(True)
        yaw_input_layout.addWidget(self.yaw_spinbox)

        self.set_yaw_button = QPushButton("Set Yaw")
        self.set_yaw_button.clicked.connect(self._on_set_yaw_clicked)
        yaw_input_layout.addWidget(self.set_yaw_button)
        yaw_layout.addLayout(yaw_input_layout)

        # Quick yaw buttons
        quick_yaw_layout = QHBoxLayout()
        quick_yaw_layout.addWidget(QLabel("Quick:"))

        north_btn = QPushButton("North (0°)")
        north_btn.clicked.connect(lambda: self.yaw_spinbox.setValue(0))
        quick_yaw_layout.addWidget(north_btn)

        east_btn = QPushButton("East (90°)")
        east_btn.clicked.connect(lambda: self.yaw_spinbox.setValue(90))
        quick_yaw_layout.addWidget(east_btn)

        south_btn = QPushButton("South (180°)")
        south_btn.clicked.connect(lambda: self.yaw_spinbox.setValue(180))
        quick_yaw_layout.addWidget(south_btn)

        west_btn = QPushButton("West (270°)")
        west_btn.clicked.connect(lambda: self.yaw_spinbox.setValue(270))
        quick_yaw_layout.addWidget(west_btn)

        yaw_layout.addLayout(quick_yaw_layout)
        yaw_group.setLayout(yaw_layout)
        layout.addWidget(yaw_group)

        # ===== POSITION COMMANDS =====
        position_group = QGroupBox("Position Commands")
        position_layout = QVBoxLayout()

        pos_info = QLabel("Go to GPS coordinates (requires GPS lock):")
        pos_info.setStyleSheet("color: #666; font-size: 9pt;")
        position_layout.addWidget(pos_info)

        lat_layout = QHBoxLayout()
        lat_layout.addWidget(QLabel("Latitude:"))
        self.lat_input = QLineEdit()
        self.lat_input.setPlaceholderText("e.g., 47.641468")
        lat_layout.addWidget(self.lat_input)
        position_layout.addLayout(lat_layout)

        lon_layout = QHBoxLayout()
        lon_layout.addWidget(QLabel("Longitude:"))
        self.lon_input = QLineEdit()
        self.lon_input.setPlaceholderText("e.g., -122.140165")
        lon_layout.addWidget(self.lon_input)
        position_layout.addLayout(lon_layout)

        alt_layout = QHBoxLayout()
        alt_layout.addWidget(QLabel("Altitude:"))
        self.pos_alt_spinbox = QDoubleSpinBox()
        self.pos_alt_spinbox.setRange(1.0, 100.0)
        self.pos_alt_spinbox.setSingleStep(1.0)
        self.pos_alt_spinbox.setValue(10.0)
        self.pos_alt_spinbox.setSuffix(" m")
        alt_layout.addWidget(self.pos_alt_spinbox)
        position_layout.addLayout(alt_layout)

        goto_button_layout = QHBoxLayout()
        self.goto_button = QPushButton("🎯 Go To Position")
        self.goto_button.setStyleSheet("""
            QPushButton {
                background-color: #6f42c1;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5a32a3;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.goto_button.clicked.connect(self._on_goto_clicked)
        goto_button_layout.addWidget(self.goto_button)
        position_layout.addLayout(goto_button_layout)

        position_group.setLayout(position_layout)
        layout.addWidget(position_group)

        # ===== COMMAND LOG =====
        log_group = QGroupBox("Command Log")
        log_layout = QVBoxLayout()

        self.command_log = QTextEdit()
        self.command_log.setReadOnly(True)
        self.command_log.setMaximumHeight(120)
        self.command_log.setStyleSheet(
            "background-color: #f8f9fa; font-family: monospace; font-size: 9pt;"
        )
        log_layout.addWidget(self.command_log)

        clear_log_button = QPushButton("Clear Log")
        clear_log_button.clicked.connect(self.command_log.clear)
        log_layout.addWidget(clear_log_button)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # ===== CONNECTION STATUS =====
        self.connection_label = QLabel("⚠ MAVLink not connected")
        self.connection_label.setStyleSheet(
            "color: red; font-weight: bold; padding: 8px; "
            "background-color: #ffe6e6; border-radius: 5px;"
        )
        layout.addWidget(self.connection_label)

        layout.addStretch()
        self.setLayout(layout)

        # Initially disable controls
        self._update_control_states(False)

    def set_mavlink(self, mavlink):
        """Set MAVLink telemetry reference"""
        self.mavlink = mavlink
        self._update_connection_status()

    def _update_connection_status(self):
        """Update connection status display"""
        if self.mavlink and self.mavlink.is_connected:
            self.connection_label.setText("✓ MAVLink connected")
            self.connection_label.setStyleSheet(
                "color: green; font-weight: bold; padding: 8px; "
                "background-color: #e6ffe6; border-radius: 5px;"
            )
            self._update_control_states(True)
        else:
            self.connection_label.setText("⚠ MAVLink not connected")
            self.connection_label.setStyleSheet(
                "color: red; font-weight: bold; padding: 8px; "
                "background-color: #ffe6e6; border-radius: 5px;"
            )
            self._update_control_states(False)

    def _update_control_states(self, enabled: bool):
        """Enable or disable all controls"""
        self.takeoff_button.setEnabled(enabled)
        self.land_button.setEnabled(enabled)
        self.rtl_button.setEnabled(enabled)
        self.send_velocity_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)
        self.set_yaw_button.setEnabled(enabled)
        self.goto_button.setEnabled(enabled)

    def _log_command(self, command: str):
        """Add command to log"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.command_log.append(f"[{timestamp}] {command}")

    def _on_takeoff_clicked(self):
        """Handle takeoff button"""
        altitude = self.takeoff_alt_spinbox.value()

        reply = QMessageBox.question(
            self,
            "Confirm Takeoff",
            f"Takeoff to {altitude:.1f}m altitude?\n\n"
            "⚠ Ensure:\n"
            "• Motors are armed\n"
            "• Area is clear\n"
            "• GPS lock obtained (if required)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.mavlink and self.mavlink.is_connected:
                success = self.mavlink.takeoff(altitude)
                if success:
                    self._log_command(f"Takeoff to {altitude:.1f}m")
                    QMessageBox.information(self, "Takeoff", "Takeoff command sent!")
                else:
                    self._log_command(f"Takeoff FAILED")
                    QMessageBox.warning(self, "Takeoff Failed", "Failed to send takeoff command")

                self.takeoff_requested.emit(altitude)

    def _on_land_clicked(self):
        """Handle land button"""
        reply = QMessageBox.question(
            self,
            "Confirm Land",
            "Command drone to land at current position?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.mavlink and self.mavlink.is_connected:
                success = self.mavlink.land()
                if success:
                    self._log_command("Land command sent")
                    QMessageBox.information(self, "Land", "Land command sent!")
                else:
                    self._log_command("Land FAILED")
                    QMessageBox.warning(self, "Land Failed", "Failed to send land command")

                self.land_requested.emit()

    def _on_rtl_clicked(self):
        """Handle RTL button"""
        reply = QMessageBox.question(
            self,
            "Confirm RTL",
            "Command drone to Return to Launch?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.mavlink and self.mavlink.is_connected:
                success = self.mavlink.return_to_launch()
                if success:
                    self._log_command("RTL command sent")
                    QMessageBox.information(self, "RTL", "Return to Launch command sent!")
                else:
                    self._log_command("RTL FAILED")
                    QMessageBox.warning(self, "RTL Failed", "Failed to send RTL command")

                self.rtl_requested.emit()

    def _on_send_velocity_clicked(self):
        """Handle send velocity button"""
        vx = self.vel_x_spinbox.value()
        vy = self.vel_y_spinbox.value()
        vz = self.vel_z_spinbox.value()
        yaw_rate = self.yaw_rate_spinbox.value()
        frame = self.frame_combo.currentText()

        if self.mavlink and self.mavlink.is_connected:
            if "Body" in frame:
                self.mavlink.send_velocity_body(vx, vy, vz, yaw_rate)
                self._log_command(f"Velocity (body): vx={vx:.1f}, vy={vy:.1f}, vz={vz:.1f}, yaw_rate={yaw_rate:.1f}")
                self.velocity_body_requested.emit(vx, vy, vz, yaw_rate)
            else:  # NED Frame
                self.mavlink.send_velocity_ned(vx, vy, vz, yaw_rate)
                self._log_command(f"Velocity (NED): vx={vx:.1f}, vy={vy:.1f}, vz={vz:.1f}, yaw_rate={yaw_rate:.1f}")
                self.velocity_ned_requested.emit(vx, vy, vz, yaw_rate)

    def _on_stop_clicked(self):
        """Handle stop button - send zero velocity"""
        if self.mavlink and self.mavlink.is_connected:
            self.mavlink.send_velocity_body(0, 0, 0, 0)
            self._log_command("STOP - Zero velocity")

    def _on_set_yaw_clicked(self):
        """Handle set yaw button"""
        yaw = self.yaw_spinbox.value()
        vx = self.vel_x_spinbox.value()
        vy = self.vel_y_spinbox.value()
        vz = self.vel_z_spinbox.value()
        frame = "BODY_FWD" if "Body" in self.frame_combo.currentText() else "BODY_OFFSET_YAW"

        if self.mavlink and self.mavlink.is_connected:
            self.mavlink.send_velocity_with_yaw(vx, vy, vz, yaw, frame)
            self._log_command(f"Set yaw: {yaw:.0f}° with velocity vx={vx:.1f}, vy={vy:.1f}, vz={vz:.1f}")
            self.velocity_with_yaw_requested.emit(vx, vy, vz, yaw, frame)

    def _on_goto_clicked(self):
        """Handle go to position button"""
        try:
            lat = float(self.lat_input.text())
            lon = float(self.lon_input.text())
            alt = self.pos_alt_spinbox.value()

            reply = QMessageBox.question(
                self,
                "Confirm Go To",
                f"Go to position?\n\n"
                f"Latitude: {lat:.6f}\n"
                f"Longitude: {lon:.6f}\n"
                f"Altitude: {alt:.1f}m\n\n"
                "⚠ Ensure GPS lock is obtained",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Note: This would require implementing goto_position in MAVLinkTelemetry
                self._log_command(f"Go to: lat={lat:.6f}, lon={lon:.6f}, alt={alt:.1f}m")
                QMessageBox.information(
                    self,
                    "Go To Position",
                    "Position command sent!\n\n"
                    "Note: Drone must be in GUIDED mode with GPS lock."
                )
                self.goto_position_requested.emit(lat, lon, alt)

        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Please enter valid latitude and longitude values"
            )
