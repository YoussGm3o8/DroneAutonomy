"""
Drone Control Panel for MAVLink Control

Provides:
- Arm/Disarm buttons
- Flight mode selection dropdown
- Emergency stop button
- Current status display
"""

from typing import Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QGroupBox, QPushButton, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class DroneControlPanel(QWidget):
    """
    Drone control panel for arming and mode changes
    """
    
    # Signals
    arm_requested = pyqtSignal()
    disarm_requested = pyqtSignal()
    mode_change_requested = pyqtSignal(str)  # mode name
    emergency_stop_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mavlink = None  # Reference to MAVLink telemetry
        self.current_mode = "UNKNOWN"
        self.is_armed = False
        self.prev_mode = None
        self.prev_armed = None
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # Status display
        status_group = QGroupBox("Current Status")
        status_layout = QVBoxLayout()
        
        # Armed status
        armed_layout = QHBoxLayout()
        armed_layout.addWidget(QLabel("Armed Status:"))
        self.armed_status_label = QLabel("DISARMED")
        self.armed_status_label.setStyleSheet(
            "font-weight: bold; font-size: 14pt; color: green; padding: 5px;"
        )
        armed_layout.addWidget(self.armed_status_label)
        armed_layout.addStretch()
        status_layout.addLayout(armed_layout)
        
        # Flight mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Flight Mode:"))
        self.mode_status_label = QLabel("UNKNOWN")
        self.mode_status_label.setStyleSheet(
            "font-weight: bold; font-size: 14pt; color: #0056b3; padding: 5px;"
        )
        mode_layout.addWidget(self.mode_status_label)
        mode_layout.addStretch()
        status_layout.addLayout(mode_layout)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Arm/Disarm controls
        arm_group = QGroupBox("Arm/Disarm Controls")
        arm_layout = QVBoxLayout()
        
        # Warning label
        warning_label = QLabel("⚠ Ensure propellers are clear before arming!")
        warning_label.setStyleSheet("color: orange; font-weight: bold;")
        arm_layout.addWidget(warning_label)
        
        # Arm/Disarm buttons
        button_layout = QHBoxLayout()
        
        self.arm_button = QPushButton("🔓 ARM MOTORS")
        self.arm_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                font-size: 12pt;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.arm_button.clicked.connect(self._on_arm_clicked)
        button_layout.addWidget(self.arm_button)
        
        self.disarm_button = QPushButton("🔒 DISARM MOTORS")
        self.disarm_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                font-size: 12pt;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.disarm_button.clicked.connect(self._on_disarm_clicked)
        button_layout.addWidget(self.disarm_button)
        
        arm_layout.addLayout(button_layout)
        arm_group.setLayout(arm_layout)
        layout.addWidget(arm_group)
        
        # Flight mode controls
        mode_group = QGroupBox("Flight Mode Selection")
        mode_layout = QVBoxLayout()
        
        # Mode description
        mode_desc_label = QLabel("Select the desired flight mode:")
        mode_layout.addWidget(mode_desc_label)
        
        # Mode selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Mode:"))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "STABILIZE",
            "ALT_HOLD",
            "LOITER",
            "GUIDED",
            "AUTO",
            "RTL",
            "LAND",
            "POSHOLD",
            "BRAKE",
            "SMART_RTL"
        ])
        self.mode_combo.setStyleSheet("font-size: 11pt; padding: 5px;")
        selector_layout.addWidget(self.mode_combo, 1)
        
        self.set_mode_button = QPushButton("Set Mode")
        self.set_mode_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.set_mode_button.clicked.connect(self._on_set_mode_clicked)
        selector_layout.addWidget(self.set_mode_button)
        
        mode_layout.addLayout(selector_layout)
        
        # Mode descriptions
        mode_info = QLabel(
            "<b>Common Modes:</b><br>"
            "• <b>STABILIZE</b>: Manual flight with auto-leveling<br>"
            "• <b>ALT_HOLD</b>: Manual with altitude hold<br>"
            "• <b>LOITER</b>: Hold position (GPS required)<br>"
            "• <b>GUIDED</b>: Accept velocity/position commands<br>"
            "• <b>RTL</b>: Return to launch<br>"
            "• <b>LAND</b>: Automatic landing"
        )
        mode_info.setStyleSheet("font-size: 9pt; color: #555; padding: 5px;")
        mode_info.setWordWrap(True)
        mode_layout.addWidget(mode_info)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Emergency controls
        emergency_group = QGroupBox("Emergency Controls")
        emergency_layout = QVBoxLayout()
        
        emergency_warning = QLabel("⚠ Use only in emergency situations!")
        emergency_warning.setStyleSheet("color: red; font-weight: bold;")
        emergency_layout.addWidget(emergency_warning)
        
        self.emergency_stop_button = QPushButton("🚨 EMERGENCY STOP (RTL)")
        self.emergency_stop_button.setStyleSheet("""
            QPushButton {
                background-color: #ff0000;
                color: white;
                font-weight: bold;
                font-size: 14pt;
                padding: 15px;
                border-radius: 5px;
                border: 3px solid #8b0000;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                border: 3px solid #495057;
            }
        """)
        self.emergency_stop_button.clicked.connect(self._on_emergency_stop_clicked)
        emergency_layout.addWidget(self.emergency_stop_button)
        
        emergency_group.setLayout(emergency_layout)
        layout.addWidget(emergency_group)
        
        # Connection status
        self.connection_label = QLabel("⚠ MAVLink not connected")
        self.connection_label.setStyleSheet(
            "color: red; font-weight: bold; padding: 10px; "
            "background-color: #ffe6e6; border-radius: 5px;"
        )
        layout.addWidget(self.connection_label)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Initially disable all controls
        self._update_control_states(False)
        
    def set_mavlink(self, mavlink):
        """Set MAVLink telemetry reference"""
        self.mavlink = mavlink
        self._update_connection_status()
        
    def update_status(self, armed: bool, mode: str):
        """Update displayed status, only if values have changed."""
        # Early return if nothing changed (prevents flickering)
        if armed == self.prev_armed and mode == self.prev_mode:
            return  # No change, do nothing to prevent flicker
        
        # Debug: log the actual changes
        if armed != self.prev_armed:
            print(f"[DroneControl] Armed state changed: {self.prev_armed} → {armed}")
        if mode != self.prev_mode:
            print(f"[DroneControl] Flight mode changed: {self.prev_mode} → {mode}")
        
        self.is_armed = armed
        self.current_mode = mode
        
        # Update armed status display only if it changed
        if armed != self.prev_armed:
            if armed:
                self.armed_status_label.setText("ARMED")
                self.armed_status_label.setStyleSheet(
                    "font-weight: bold; font-size: 14pt; color: red; padding: 5px;"
                )
            else:
                self.armed_status_label.setText("DISARMED")
                self.armed_status_label.setStyleSheet(
                    "font-weight: bold; font-size: 14pt; color: green; padding: 5px;"
                )
            # Update button states
            self.arm_button.setEnabled(not armed and self.mavlink and self.mavlink.is_connected)
            self.disarm_button.setEnabled(armed and self.mavlink and self.mavlink.is_connected)
            self.prev_armed = armed
        
        # Update mode display only if it changed
        if mode != self.prev_mode:
            self.mode_status_label.setText(mode)
            self.prev_mode = mode
        
    def _update_connection_status(self):
        """Update connection status display"""
        if self.mavlink and self.mavlink.is_connected:
            self.connection_label.setText("✓ MAVLink connected")
            self.connection_label.setStyleSheet(
                "color: green; font-weight: bold; padding: 10px; "
                "background-color: #e6ffe6; border-radius: 5px;"
            )
            self._update_control_states(True)
        else:
            self.connection_label.setText("⚠ MAVLink not connected")
            self.connection_label.setStyleSheet(
                "color: red; font-weight: bold; padding: 10px; "
                "background-color: #ffe6e6; border-radius: 5px;"
            )
            self._update_control_states(False)
            # Clear status on disconnect
            self.update_status(False, "UNKNOWN")
            
    def _update_control_states(self, enabled: bool):
        """Enable or disable all controls"""
        self.arm_button.setEnabled(enabled and not self.is_armed)
        self.disarm_button.setEnabled(enabled and self.is_armed)
        self.set_mode_button.setEnabled(enabled)
        self.mode_combo.setEnabled(enabled)
        self.emergency_stop_button.setEnabled(enabled)
        
    def _on_arm_clicked(self):
        """Handle arm button click"""
        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Arm",
            "Are you sure you want to ARM the motors?\n\n"
            "⚠ Ensure:\n"
            "• Propellers are clear\n"
            "• Drone is in safe location\n"
            "• GPS lock obtained (if required)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.mavlink and self.mavlink.is_connected:
                success = self.mavlink.arm()
                if success:
                    QMessageBox.information(self, "Arm Command", "Arm command sent successfully!")
                else:
                    QMessageBox.warning(self, "Arm Failed", "Failed to send arm command.")
            else:
                QMessageBox.warning(self, "Not Connected", "MAVLink is not connected!")
                
    def _on_disarm_clicked(self):
        """Handle disarm button click"""
        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Disarm",
            "Are you sure you want to DISARM the motors?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.mavlink and self.mavlink.is_connected:
                success = self.mavlink.disarm()
                if success:
                    QMessageBox.information(self, "Disarm Command", "Disarm command sent successfully!")
                else:
                    QMessageBox.warning(self, "Disarm Failed", "Failed to send disarm command.")
            else:
                QMessageBox.warning(self, "Not Connected", "MAVLink is not connected!")
                
    def _on_set_mode_clicked(self):
        """Handle set mode button click"""
        selected_mode = self.mode_combo.currentText()
        
        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Mode Change",
            f"Change flight mode to {selected_mode}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.mavlink and self.mavlink.is_connected:
                success = self.mavlink.set_mode(selected_mode)
                if success:
                    QMessageBox.information(
                        self, 
                        "Mode Change", 
                        f"Mode change command sent: {selected_mode}"
                    )
                else:
                    QMessageBox.warning(self, "Mode Change Failed", "Failed to send mode change command.")
            else:
                QMessageBox.warning(self, "Not Connected", "MAVLink is not connected!")
                
    def _on_emergency_stop_clicked(self):
        """Handle emergency stop button click"""
        # Critical confirmation dialog
        reply = QMessageBox.critical(
            self,
            "EMERGENCY STOP",
            "⚠ EMERGENCY STOP ⚠\n\n"
            "This will command the drone to RTL (Return to Launch).\n\n"
            "Confirm emergency stop?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.mavlink and self.mavlink.is_connected:
                success = self.mavlink.set_mode("RTL")
                if success:
                    QMessageBox.warning(
                        self, 
                        "Emergency Stop", 
                        "🚨 Emergency RTL command sent!\n\nDrone returning to launch."
                    )
                else:
                    QMessageBox.critical(self, "Emergency Stop Failed", "Failed to send RTL command!")
            else:
                QMessageBox.critical(self, "Not Connected", "MAVLink is not connected!")
