"""
Telemetry Display for Real-time Drone Data

Displays:
- GPS coordinates (latitude, longitude, altitude)
- Attitude (roll, pitch, yaw)
- Velocity (ground speed, vertical speed)
- Battery status
- Flight mode
- Connection status
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QGroupBox, QGridLayout, QProgressBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor


class TelemetryDisplay(QWidget):
    """
    Real-time telemetry data display
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.telemetry_data = {}
        self.connection_status = "Disconnected"
        
        # Cache previous values to avoid unnecessary updates
        self.prev_armed = None
        self.prev_mode = None
        self.prev_gps_fix = None
        
        self.init_ui()
        
        # Update timer for connection status indicator
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self._update_status_indicator)
        self.blink_timer.start(500)  # Blink every 500ms
        self.blink_state = False
        
    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        layout.setSpacing(8)  # Add spacing between groups
        
        # Connection status
        status_layout = QHBoxLayout()
        
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: red; font-size: 18px;")
        status_layout.addWidget(self.status_indicator)
        
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.flight_mode_label = QLabel("Mode: UNKNOWN")
        self.flight_mode_label.setStyleSheet("color: #0056b3; font-weight: bold; font-size: 10pt;")  # Darker blue
        status_layout.addWidget(self.flight_mode_label)
        
        layout.addLayout(status_layout)
        
        # GPS group
        gps_group = QGroupBox("GPS Position")
        gps_layout = QGridLayout()
        gps_layout.setVerticalSpacing(6)
        gps_layout.setHorizontalSpacing(10)
        
        label_font_size = "font-size: 9pt;"
        value_font_style = "font-family: 'Courier New'; font-size: 10pt;"
        
        gps_layout.addWidget(QLabel("Latitude:"), 0, 0)
        self.lat_value = QLabel("--")
        self.lat_value.setStyleSheet(value_font_style)
        self.lat_value.setMinimumWidth(140)
        gps_layout.addWidget(self.lat_value, 0, 1)
        
        gps_layout.addWidget(QLabel("Longitude:"), 1, 0)
        self.lon_value = QLabel("--")
        self.lon_value.setStyleSheet(value_font_style)
        self.lon_value.setMinimumWidth(140)
        gps_layout.addWidget(self.lon_value, 1, 1)
        
        gps_layout.addWidget(QLabel("Altitude:"), 2, 0)
        self.alt_value = QLabel("-- m")
        self.alt_value.setStyleSheet(value_font_style)
        gps_layout.addWidget(self.alt_value, 2, 1)
        
        gps_layout.addWidget(QLabel("GPS Fix:"), 3, 0)
        self.gps_fix_value = QLabel("No Fix")
        gps_layout.addWidget(self.gps_fix_value, 3, 1)
        
        gps_group.setLayout(gps_layout)
        layout.addWidget(gps_group)
        
        # Attitude group
        attitude_group = QGroupBox("Attitude")
        attitude_layout = QGridLayout()
        attitude_layout.setVerticalSpacing(6)
        attitude_layout.setHorizontalSpacing(10)
        
        attitude_layout.addWidget(QLabel("Roll:"), 0, 0)
        self.roll_value = QLabel("-- °")
        self.roll_value.setStyleSheet(value_font_style)
        attitude_layout.addWidget(self.roll_value, 0, 1)
        
        attitude_layout.addWidget(QLabel("Pitch:"), 1, 0)
        self.pitch_value = QLabel("-- °")
        self.pitch_value.setStyleSheet(value_font_style)
        attitude_layout.addWidget(self.pitch_value, 1, 1)
        
        attitude_layout.addWidget(QLabel("Yaw:"), 2, 0)
        self.yaw_value = QLabel("-- °")
        self.yaw_value.setStyleSheet(value_font_style)
        attitude_layout.addWidget(self.yaw_value, 2, 1)
        
        attitude_layout.addWidget(QLabel("Heading:"), 3, 0)
        self.heading_value = QLabel("-- °")
        self.heading_value.setStyleSheet(value_font_style)
        attitude_layout.addWidget(self.heading_value, 3, 1)
        
        attitude_group.setLayout(attitude_layout)
        layout.addWidget(attitude_group)
        
        # Velocity group
        velocity_group = QGroupBox("Velocity")
        velocity_layout = QGridLayout()
        velocity_layout.setVerticalSpacing(6)
        velocity_layout.setHorizontalSpacing(10)
        
        velocity_layout.addWidget(QLabel("Ground:"), 0, 0)
        self.ground_speed_value = QLabel("-- m/s")
        self.ground_speed_value.setStyleSheet(value_font_style)
        velocity_layout.addWidget(self.ground_speed_value, 0, 1)
        
        velocity_layout.addWidget(QLabel("Vertical:"), 1, 0)
        self.vertical_speed_value = QLabel("-- m/s")
        self.vertical_speed_value.setStyleSheet(value_font_style)
        velocity_layout.addWidget(self.vertical_speed_value, 1, 1)
        
        velocity_layout.addWidget(QLabel("Airspeed:"), 2, 0)
        self.airspeed_value = QLabel("-- m/s")
        self.airspeed_value.setStyleSheet(value_font_style)
        velocity_layout.addWidget(self.airspeed_value, 2, 1)
        
        velocity_group.setLayout(velocity_layout)
        layout.addWidget(velocity_group)
        
        # Battery group
        battery_group = QGroupBox("Battery")
        battery_layout = QVBoxLayout()
        battery_layout.setSpacing(6)
        
        battery_info_layout = QHBoxLayout()
        battery_info_layout.addWidget(QLabel("Voltage:"))
        self.battery_voltage_value = QLabel("-- V")
        self.battery_voltage_value.setStyleSheet(value_font_style)
        battery_info_layout.addWidget(self.battery_voltage_value)
        battery_info_layout.addWidget(QLabel("Current:"))
        self.battery_current_value = QLabel("-- A")
        self.battery_current_value.setStyleSheet(value_font_style)
        battery_info_layout.addWidget(self.battery_current_value)
        battery_info_layout.addStretch()
        battery_layout.addLayout(battery_info_layout)
        
        self.battery_progress = QProgressBar()
        self.battery_progress.setValue(0)
        self.battery_progress.setFormat("%p%")
        self.battery_progress.setMinimumHeight(22)  # Taller progress bar
        battery_layout.addWidget(self.battery_progress)
        
        battery_group.setLayout(battery_layout)
        layout.addWidget(battery_group)
        
        # System status
        system_group = QGroupBox("System")
        system_layout = QGridLayout()
        system_layout.setVerticalSpacing(6)
        system_layout.setHorizontalSpacing(10)
        
        system_layout.addWidget(QLabel("Armed:"), 0, 0)
        self.armed_value = QLabel("Disarmed")
        system_layout.addWidget(self.armed_value, 0, 1)
        
        system_layout.addWidget(QLabel("Failsafe:"), 1, 0)
        self.failsafe_value = QLabel("OK")
        system_layout.addWidget(self.failsafe_value, 1, 1)
        
        system_layout.addWidget(QLabel("RC Signal:"), 2, 0)
        self.rc_signal_value = QLabel("--")
        system_layout.addWidget(self.rc_signal_value, 2, 1)
        
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)
        
        layout.addStretch()
        self.setLayout(layout)
        self.setMinimumWidth(280)  # Ensure panel is wide enough
        
    def update_telemetry(self, telemetry: Dict[str, Any]):
        """Update telemetry display with new data"""
        self.telemetry_data = telemetry
        
        # GPS data
        if 'latitude' in telemetry:
            self.lat_value.setText(f"{telemetry['latitude']:.7f} °")
        if 'longitude' in telemetry:
            self.lon_value.setText(f"{telemetry['longitude']:.7f} °")
        if 'altitude' in telemetry:
            self.alt_value.setText(f"{telemetry['altitude']:.1f} m")
        if 'gps_fix_type' in telemetry:
            fix_types = {0: "No Fix", 1: "No Fix", 2: "2D Fix", 3: "3D Fix", 
                        4: "DGPS", 5: "RTK Float", 6: "RTK Fixed"}
            self.gps_fix_value.setText(fix_types.get(telemetry['gps_fix_type'], "Unknown"))
            
        # Attitude data
        if 'roll' in telemetry:
            self.roll_value.setText(f"{telemetry['roll']:.1f} °")
        if 'pitch' in telemetry:
            self.pitch_value.setText(f"{telemetry['pitch']:.1f} °")
        if 'yaw' in telemetry:
            self.yaw_value.setText(f"{telemetry['yaw']:.1f} °")
        if 'heading' in telemetry:
            self.heading_value.setText(f"{telemetry['heading']:.1f} °")
            
        # Velocity data
        if 'ground_speed' in telemetry:
            self.ground_speed_value.setText(f"{telemetry['ground_speed']:.1f} m/s")
        if 'vertical_speed' in telemetry:
            vs = telemetry['vertical_speed']
            sign = "+" if vs >= 0 else ""
            self.vertical_speed_value.setText(f"{sign}{vs:.1f} m/s")
        if 'airspeed' in telemetry:
            self.airspeed_value.setText(f"{telemetry['airspeed']:.1f} m/s")
            
        # Battery data
        if 'battery_voltage' in telemetry:
            voltage = telemetry['battery_voltage']
            self.battery_voltage_value.setText(f"{voltage:.2f} V")
            
            # Estimate percentage (assuming 4S LiPo: 16.8V full, 14.0V empty)
            if voltage > 0:
                percentage = min(100, max(0, (voltage - 14.0) / 2.8 * 100))
                self.battery_progress.setValue(int(percentage))
                
                # Color coding
                if percentage > 50:
                    self.battery_progress.setStyleSheet("QProgressBar::chunk { background-color: green; }")
                elif percentage > 20:
                    self.battery_progress.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
                else:
                    self.battery_progress.setStyleSheet("QProgressBar::chunk { background-color: red; }")
                    
        if 'battery_current' in telemetry:
            self.battery_current_value.setText(f"{telemetry['battery_current']:.2f} A")
            
        # System status
        if 'armed' in telemetry:
            armed = telemetry['armed']
            # Only update if changed to prevent flickering
            if armed != self.prev_armed:
                print(f"[TelemetryDisplay] Armed changed: {self.prev_armed} → {armed}")
                self.armed_value.setText("Armed" if armed else "Disarmed")
                self.armed_value.setStyleSheet(f"color: {'red' if armed else 'green'}; font-weight: bold;")
                self.prev_armed = armed
            
        if 'failsafe_active' in telemetry:
            failsafe = telemetry['failsafe_active']
            self.failsafe_value.setText("FAILSAFE" if failsafe else "OK")
            self.failsafe_value.setStyleSheet(f"color: {'red' if failsafe else 'green'}; font-weight: bold;")
            
        if 'rc_rssi' in telemetry:
            rssi = telemetry['rc_rssi']
            self.rc_signal_value.setText(f"{rssi}%")
            color = "green" if rssi > 50 else "orange" if rssi > 20 else "red"
            self.rc_signal_value.setStyleSheet(f"color: {color};")
            
        # Flight mode - only update if changed
        if 'flight_mode' in telemetry:
            mode = telemetry['flight_mode']
            if mode != self.prev_mode:
                print(f"[TelemetryDisplay] Mode changed: {self.prev_mode} → {mode}")
                self.flight_mode_label.setText(f"Mode: {mode}")
                self.prev_mode = mode
            
    def set_connection_status(self, status: str):
        """Set connection status (Connected/Disconnected/Connecting)"""
        self.connection_status = status
        self.status_label.setText(status)
        
        if status == "Connected":
            self.status_indicator.setStyleSheet("color: green; font-size: 20px;")
        elif status == "Connecting":
            self.status_indicator.setStyleSheet("color: orange; font-size: 20px;")
        else:
            self.status_indicator.setStyleSheet("color: red; font-size: 20px;")
            self.clear() # Clear display on disconnect to avoid showing stale data
            
    def _update_status_indicator(self):
        """Update blinking status indicator"""
        if self.connection_status == "Connecting":
            self.blink_state = not self.blink_state
            if self.blink_state:
                self.status_indicator.setStyleSheet("color: orange; font-size: 20px;")
            else:
                self.status_indicator.setStyleSheet("color: #555; font-size: 20px;")
                
    def clear(self):
        """Clear all telemetry data"""
        self.telemetry_data = {}
        
        # Reset cached values
        self.prev_armed = None
        self.prev_mode = None
        self.prev_gps_fix = None
        
        # Reset GPS
        self.lat_value.setText("--")
        self.lon_value.setText("--")
        self.alt_value.setText("-- m")
        self.gps_fix_value.setText("No Fix")
        
        # Reset attitude
        self.roll_value.setText("-- °")
        self.pitch_value.setText("-- °")
        self.yaw_value.setText("-- °")
        self.heading_value.setText("-- °")
        
        # Reset velocity
        self.ground_speed_value.setText("-- m/s")
        self.vertical_speed_value.setText("-- m/s")
        self.airspeed_value.setText("-- m/s")
        
        # Reset battery
        self.battery_voltage_value.setText("-- V")
        self.battery_current_value.setText("-- A")
        self.battery_progress.setValue(0)
        
        # Reset system
        self.armed_value.setText("Disarmed")
        self.failsafe_value.setText("OK")
        self.rc_signal_value.setText("--")
        self.flight_mode_label.setText("Mode: UNKNOWN")
