"""
Task 1: Fire Reconnaissance GUI Panel

Provides comprehensive interface for:
- Drone type selection (quadcopter / VTOL tiltrotor)
- Flight boundary configuration (soft/hard GPS coordinates)
- Building/scene setup
- Lap course waypoint management
- Equipment selection and payload calculation
- Staging pad training interface
- Target detection configuration
- AI description settings
- Real-time mission monitoring
- Scoring dashboard
"""

from typing import Optional, Dict, Any, List, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QGroupBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QTextEdit, QProgressBar, QTableWidget, QTableWidgetItem,
    QLineEdit, QTabWidget, QFileDialog, QMessageBox, QRadioButton,
    QButtonGroup, QScrollArea, QFormLayout, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor
from pathlib import Path
import yaml
import json
import csv


class Task1FireReconPanel(QWidget):
    """
    Main control panel for Task 1: Fire Reconnaissance
    """
    
    # Signals
    mission_start_requested = pyqtSignal(dict)  # config
    mission_stop_requested = pyqtSignal()
    config_changed = pyqtSignal(dict)
    boundary_violation_warning = pyqtSignal(str)  # violation type
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.mission_running = False
        self.mission_config = {}
        self.detected_targets = []
        self.current_scores = {
            'target_detection': 0.0,
            'equipment_delivery': 0.0,
            'distance_flown': 0.0,
            'payload_fraction': 0.0,
            'safe_landing': 0.0
        }
        
        self.init_ui()
        self.load_default_config()
    
    def init_ui(self):
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        
        # Header
        header = QLabel("Task 1: Fire Reconnaissance")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #d32f2f; padding: 10px;")
        main_layout.addWidget(header)
        
        # Tab widget for different configuration sections
        self.tabs = QTabWidget()
        
        # Tab 1: Drone & Mission Setup
        self.tabs.addTab(self._create_drone_setup_tab(), "Drone Setup")
        
        # Tab 2: Boundaries
        self.tabs.addTab(self._create_boundaries_tab(), "Flight Boundaries")
        
        # Tab 3: Building & Scene
        self.tabs.addTab(self._create_building_tab(), "Building/Scene")
        
        # Tab 4: Lap Course
        self.tabs.addTab(self._create_lap_course_tab(), "Lap Course")
        
        # Tab 5: Equipment
        self.tabs.addTab(self._create_equipment_tab(), "Equipment")
        
        # Tab 6: Staging Pads
        self.tabs.addTab(self._create_staging_pads_tab(), "Staging Pads")
        
        # Tab 7: Targets & AI
        self.tabs.addTab(self._create_targets_tab(), "Targets & AI")
        
        main_layout.addWidget(self.tabs)
        
        # Mission control buttons
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚁 Start Mission")
        self.start_btn.setStyleSheet(
            "background-color: #28a745; color: white; font-weight: bold; padding: 12px; font-size: 11pt;"
        )
        self.start_btn.clicked.connect(self._on_start_mission)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop Mission")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(
            "background-color: #dc3545; color: white; font-weight: bold; padding: 12px; font-size: 11pt;"
        )
        self.stop_btn.clicked.connect(self._on_stop_mission)
        control_layout.addWidget(self.stop_btn)
        
        self.export_btn = QPushButton("📄 Export Data")
        self.export_btn.clicked.connect(self._on_export_data)
        control_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(control_layout)
        
        # Mission status and scoring dashboard
        status_group = QGroupBox("Mission Status & Scoring")
        status_layout = QVBoxLayout()
        
        # Status labels
        status_info_layout = QHBoxLayout()
        
        self.state_label = QLabel("State: IDLE")
        self.state_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        status_info_layout.addWidget(self.state_label)
        
        self.lap_label = QLabel("Laps: 0/0")
        status_info_layout.addWidget(self.lap_label)
        
        self.target_label = QLabel("Targets: 0")
        status_info_layout.addWidget(self.target_label)
        
        self.equipment_label = QLabel("Equipment: 0/0")
        status_info_layout.addWidget(self.equipment_label)
        
        status_layout.addLayout(status_info_layout)
        
        # Scoring table
        self.score_table = QTableWidget(6, 2)
        self.score_table.setHorizontalHeaderLabels(["Component", "Score"])
        self.score_table.setMaximumHeight(200)
        self.score_table.horizontalHeader().setStretchLastSection(True)
        
        score_items = [
            ("Target Detection", "0.0 / 25"),
            ("Equipment Delivery", "0.0 / 20"),
            ("Distance Flown", "0.0 / 30"),
            ("Payload Fraction", "0.0 / 20"),
            ("Safe Landing", "0.0 / 5"),
            ("TOTAL SCORE", "0.0 / 100")
        ]
        
        for row, (component, score) in enumerate(score_items):
            self.score_table.setItem(row, 0, QTableWidgetItem(component))
            score_item = QTableWidgetItem(score)
            if row == 5:  # Total row
                score_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                score_item.setForeground(QColor("#007bff"))
            self.score_table.setItem(row, 1, score_item)
        
        status_layout.addWidget(self.score_table)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        self.setLayout(main_layout)
    
    def _create_drone_setup_tab(self) -> QWidget:
        """Create drone and mission setup tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Drone type selection
        drone_group = QGroupBox("Drone Type")
        drone_layout = QVBoxLayout()
        
        self.drone_type_group = QButtonGroup()
        
        self.quadcopter_radio = QRadioButton("Quadcopter")
        self.quadcopter_radio.setChecked(True)
        self.drone_type_group.addButton(self.quadcopter_radio, 0)
        drone_layout.addWidget(self.quadcopter_radio)
        
        quad_info = QLabel("• Hover-capable\n• Vertical landing\n• Hover-and-release equipment")
        quad_info.setStyleSheet("color: #666; margin-left: 20px; font-size: 9pt;")
        drone_layout.addWidget(quad_info)
        
        self.vtol_radio = QRadioButton("VTOL Tiltrotor (3-motor plane)")
        self.drone_type_group.addButton(self.vtol_radio, 1)
        drone_layout.addWidget(self.vtol_radio)
        
        vtol_info = QLabel("• Fixed-wing cruise for laps\n• VTOL mode for hover\n• Transition capability")
        vtol_info.setStyleSheet("color: #666; margin-left: 20px; font-size: 9pt;")
        drone_layout.addWidget(vtol_info)
        
        drone_group.setLayout(drone_layout)
        layout.addWidget(drone_group)
        
        # UAV configuration
        uav_group = QGroupBox("UAV Configuration")
        uav_layout = QFormLayout()
        
        self.uav_count_spin = QSpinBox()
        self.uav_count_spin.setRange(1, 2)
        self.uav_count_spin.setValue(1)
        uav_layout.addRow("Number of UAVs:", self.uav_count_spin)
        
        self.uav1_weight = QSpinBox()
        self.uav1_weight.setRange(0, 10000)
        self.uav1_weight.setValue(1200)
        self.uav1_weight.setSuffix(" g")
        uav_layout.addRow("UAV 1 Empty Weight:", self.uav1_weight)
        
        self.uav2_weight = QSpinBox()
        self.uav2_weight.setRange(0, 10000)
        self.uav2_weight.setValue(0)
        self.uav2_weight.setSuffix(" g")
        self.uav2_weight.setEnabled(False)
        uav_layout.addRow("UAV 2 Empty Weight:", self.uav2_weight)
        
        self.uav_count_spin.valueChanged.connect(
            lambda v: self.uav2_weight.setEnabled(v == 2)
        )
        
        uav_group.setLayout(uav_layout)
        layout.addWidget(uav_group)
        
        # Mission parameters
        mission_group = QGroupBox("Mission Parameters")
        mission_layout = QFormLayout()
        
        self.team_name_edit = QLineEdit("DroneTeam")
        mission_layout.addRow("Team Name:", self.team_name_edit)
        
        self.mission_timeout = QSpinBox()
        self.mission_timeout.setRange(300, 3600)
        self.mission_timeout.setValue(1800)
        self.mission_timeout.setSuffix(" sec")
        mission_layout.addRow("Mission Timeout:", self.mission_timeout)
        
        self.altitude_limit = QSpinBox()
        self.altitude_limit.setRange(50, 500)
        self.altitude_limit.setValue(400)
        self.altitude_limit.setSuffix(" ft")
        mission_layout.addRow("Altitude Limit:", self.altitude_limit)
        
        mission_group.setLayout(mission_layout)
        layout.addWidget(mission_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_boundaries_tab(self) -> QWidget:
        """Create flight boundaries configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        info_label = QLabel(
            "⚠ Enter GPS coordinates provided by competition organizers.\n"
            "Soft boundary: Warning zone. Hard boundary: Kill zone."
        )
        info_label.setStyleSheet("color: #856404; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Soft boundary
        soft_group = QGroupBox("Soft Boundary (Yellow - Warning)")
        soft_layout = QVBoxLayout()
        
        soft_buttons = QHBoxLayout()
        add_soft_btn = QPushButton("➕ Add Point")
        add_soft_btn.clicked.connect(lambda: self._add_boundary_point(self.soft_boundary_table))
        soft_buttons.addWidget(add_soft_btn)
        
        remove_soft_btn = QPushButton("➖ Remove Selected")
        remove_soft_btn.clicked.connect(lambda: self._remove_boundary_point(self.soft_boundary_table))
        soft_buttons.addWidget(remove_soft_btn)
        
        import_soft_btn = QPushButton("📁 Import CSV")
        import_soft_btn.clicked.connect(lambda: self._import_boundary_csv(self.soft_boundary_table))
        soft_buttons.addWidget(import_soft_btn)
        
        soft_buttons.addStretch()
        soft_layout.addLayout(soft_buttons)
        
        self.soft_boundary_table = QTableWidget(0, 2)
        self.soft_boundary_table.setHorizontalHeaderLabels(["Longitude", "Latitude"])
        self.soft_boundary_table.horizontalHeader().setStretchLastSection(True)
        self.soft_boundary_table.setMaximumHeight(150)
        soft_layout.addWidget(self.soft_boundary_table)
        
        soft_group.setLayout(soft_layout)
        layout.addWidget(soft_group)
        
        # Hard boundary
        hard_group = QGroupBox("Hard Boundary (Red - Kill Zone)")
        hard_layout = QVBoxLayout()
        
        hard_buttons = QHBoxLayout()
        add_hard_btn = QPushButton("➕ Add Point")
        add_hard_btn.clicked.connect(lambda: self._add_boundary_point(self.hard_boundary_table))
        hard_buttons.addWidget(add_hard_btn)
        
        remove_hard_btn = QPushButton("➖ Remove Selected")
        remove_hard_btn.clicked.connect(lambda: self._remove_boundary_point(self.hard_boundary_table))
        hard_buttons.addWidget(remove_hard_btn)
        
        import_hard_btn = QPushButton("📁 Import CSV")
        import_hard_btn.clicked.connect(lambda: self._import_boundary_csv(self.hard_boundary_table))
        hard_buttons.addWidget(import_hard_btn)
        
        hard_buttons.addStretch()
        hard_layout.addLayout(hard_buttons)
        
        self.hard_boundary_table = QTableWidget(0, 2)
        self.hard_boundary_table.setHorizontalHeaderLabels(["Longitude", "Latitude"])
        self.hard_boundary_table.horizontalHeader().setStretchLastSection(True)
        self.hard_boundary_table.setMaximumHeight(150)
        hard_layout.addWidget(self.hard_boundary_table)
        
        hard_group.setLayout(hard_layout)
        layout.addWidget(hard_group)
        
        # MissionPlanner integration
        mp_btn = QPushButton("📤 Send to MissionPlanner")
        mp_btn.setStyleSheet("background-color: #17a2b8; color: white; padding: 8px;")
        mp_btn.clicked.connect(self._send_to_missionplanner)
        layout.addWidget(mp_btn)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_building_tab(self) -> QWidget:
        """Create building/scene configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Building location
        location_group = QGroupBox("Building GPS Location")
        location_layout = QFormLayout()
        
        self.building_lat = QLineEdit("0.0")
        location_layout.addRow("Latitude (deg):", self.building_lat)
        
        self.building_lon = QLineEdit("0.0")
        location_layout.addRow("Longitude (deg):", self.building_lon)
        
        self.building_alt = QDoubleSpinBox()
        self.building_alt.setRange(0, 5000)
        self.building_alt.setValue(0)
        self.building_alt.setSuffix(" m")
        location_layout.addRow("Altitude AGL:", self.building_alt)
        
        location_group.setLayout(location_layout)
        layout.addWidget(location_group)
        
        # Building dimensions
        dimensions_group = QGroupBox("Building Dimensions")
        dimensions_layout = QFormLayout()
        
        self.building_length = QDoubleSpinBox()
        self.building_length.setRange(0, 200)
        self.building_length.setValue(20)
        self.building_length.setSuffix(" m")
        dimensions_layout.addRow("Length (N-S):", self.building_length)
        
        self.building_width = QDoubleSpinBox()
        self.building_width.setRange(0, 200)
        self.building_width.setValue(15)
        self.building_width.setSuffix(" m")
        dimensions_layout.addRow("Width (E-W):", self.building_width)
        
        self.building_height = QDoubleSpinBox()
        self.building_height.setRange(0, 100)
        self.building_height.setValue(10)
        self.building_height.setSuffix(" m")
        dimensions_layout.addRow("Height:", self.building_height)
        
        self.building_orientation = QDoubleSpinBox()
        self.building_orientation.setRange(0, 359)
        self.building_orientation.setValue(0)
        self.building_orientation.setSuffix(" °")
        dimensions_layout.addRow("North Face Bearing:", self.building_orientation)
        
        dimensions_group.setLayout(dimensions_layout)
        layout.addWidget(dimensions_group)
        
        # Scene parameters
        scene_group = QGroupBox("Fire Scene Parameters")
        scene_layout = QFormLayout()
        
        self.scene_buffer = QDoubleSpinBox()
        self.scene_buffer.setRange(5, 50)
        self.scene_buffer.setValue(15)
        self.scene_buffer.setSuffix(" m")
        scene_layout.addRow("Perimeter Buffer:", self.scene_buffer)
        
        self.scene_max_alt = QDoubleSpinBox()
        self.scene_max_alt.setRange(5, 50)
        self.scene_max_alt.setValue(10)
        self.scene_max_alt.setSuffix(" m")
        scene_layout.addRow("Max Altitude AGL:", self.scene_max_alt)
        
        scene_group.setLayout(scene_layout)
        layout.addWidget(scene_group)
        
        # Calculate button
        calc_btn = QPushButton("🔄 Calculate Scene Perimeter")
        calc_btn.clicked.connect(self._calculate_scene_perimeter)
        layout.addWidget(calc_btn)
        
        self.perimeter_info = QTextEdit()
        self.perimeter_info.setReadOnly(True)
        self.perimeter_info.setMaximumHeight(80)
        self.perimeter_info.setPlaceholderText("Scene perimeter will be calculated here...")
        layout.addWidget(self.perimeter_info)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_lap_course_tab(self) -> QWidget:
        """Create lap course waypoint management tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Lap strategy
        strategy_group = QGroupBox("Lap Strategy")
        strategy_layout = QFormLayout()
        
        self.target_laps = QSpinBox()
        self.target_laps.setRange(0, 10)
        self.target_laps.setValue(3)
        strategy_layout.addRow("Target Laps:", self.target_laps)
        
        strategy_info = QLabel(
            "0 laps = Direct flight to scene\n"
            "More laps = Higher distance score but longer mission"
        )
        strategy_info.setStyleSheet("color: #666; font-size: 9pt;")
        strategy_layout.addRow("", strategy_info)
        
        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)
        
        # Waypoints table
        waypoints_group = QGroupBox("Lap Course Waypoints")
        waypoints_layout = QVBoxLayout()
        
        waypoint_buttons = QHBoxLayout()
        add_wp_btn = QPushButton("➕ Add Waypoint")
        add_wp_btn.clicked.connect(self._add_waypoint)
        waypoint_buttons.addWidget(add_wp_btn)
        
        remove_wp_btn = QPushButton("➖ Remove Selected")
        remove_wp_btn.clicked.connect(self._remove_waypoint)
        waypoint_buttons.addWidget(remove_wp_btn)
        
        import_wp_btn = QPushButton("📁 Import CSV")
        import_wp_btn.clicked.connect(self._import_waypoints)
        waypoint_buttons.addWidget(import_wp_btn)
        
        waypoint_buttons.addStretch()
        waypoints_layout.addLayout(waypoint_buttons)
        
        self.waypoints_table = QTableWidget(0, 3)
        self.waypoints_table.setHorizontalHeaderLabels(["Latitude", "Longitude", "Altitude (m)"])
        self.waypoints_table.horizontalHeader().setStretchLastSection(True)
        waypoints_layout.addWidget(self.waypoints_table)
        
        waypoints_group.setLayout(waypoints_layout)
        layout.addWidget(waypoints_group)
        
        # Distance calculator
        distance_label = QLabel("Estimated Distance: 0.0 km")
        distance_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        layout.addWidget(distance_label)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_equipment_tab(self) -> QWidget:
        """Create equipment selection and payload calculator tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Equipment selection
        equipment_group = QGroupBox("Equipment Selection")
        equipment_layout = QVBoxLayout()
        
        self.radio_check = QCheckBox("Handheld Radio (500g, 5pts)")
        self.radio_check.setChecked(True)
        equipment_layout.addWidget(self.radio_check)
        
        self.oxygen_check = QCheckBox("Oxygen Tank (1000g, 5pts)")
        self.oxygen_check.setChecked(True)
        equipment_layout.addWidget(self.oxygen_check)
        
        self.ladder_check = QCheckBox("Ladder (3000g, 10pts)")
        self.ladder_check.setChecked(False)
        equipment_layout.addWidget(self.ladder_check)
        
        # Connect checkboxes to update calculator
        for checkbox in [self.radio_check, self.oxygen_check, self.ladder_check]:
            checkbox.stateChanged.connect(self._update_payload_calculator)
        
        equipment_group.setLayout(equipment_layout)
        layout.addWidget(equipment_group)
        
        # Payload calculator
        payload_group = QGroupBox("Payload Fraction Calculator")
        payload_layout = QVBoxLayout()
        
        self.payload_summary = QLabel(
            "Total Payload: 1500g\n"
            "Total System Weight: 2700g\n"
            "Payload Fraction: 0.556 (55.6%)\n"
            "Expected Score: 20.0 / 20 pts"
        )
        self.payload_summary.setStyleSheet(
            "background-color: #e3f2fd; padding: 10px; border-radius: 5px; font-size: 10pt;"
        )
        payload_layout.addWidget(self.payload_summary)
        
        payload_group.setLayout(payload_layout)
        layout.addWidget(payload_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_staging_pads_tab(self) -> QWidget:
        """Create staging pad training interface tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        info_label = QLabel(
            "⚠ Staging pad appearance is unknown until competition.\n"
            "Capture 50-100 images from multiple angles to train custom YOLO model."
        )
        info_label.setStyleSheet("background-color: #fff3cd; padding: 10px; border-radius: 5px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Image capture
        capture_group = QGroupBox("Image Capture")
        capture_layout = QVBoxLayout()
        
        self.staging_images_count = QLabel("Images Captured: 0")
        capture_layout.addWidget(self.staging_images_count)
        
        capture_btn = QPushButton("📷 Capture Staging Pad Image")
        capture_btn.setStyleSheet("background-color: #007bff; color: white; padding: 10px;")
        capture_btn.clicked.connect(self._capture_staging_pad_image)
        capture_layout.addWidget(capture_btn)
        
        self.staging_image_path = QLineEdit()
        self.staging_image_path.setPlaceholderText("Training images saved to...")
        self.staging_image_path.setReadOnly(True)
        capture_layout.addWidget(self.staging_image_path)
        
        capture_group.setLayout(capture_layout)
        layout.addWidget(capture_group)
        
        # Model training
        training_group = QGroupBox("Model Training")
        training_layout = QVBoxLayout()
        
        self.model_status = QLabel("Model Status: Not trained")
        training_layout.addWidget(self.model_status)
        
        train_btn = QPushButton("🎯 Train YOLO Model")
        train_btn.setStyleSheet("background-color: #28a745; color: white; padding: 10px;")
        train_btn.clicked.connect(self._train_staging_pad_model)
        training_layout.addWidget(train_btn)
        
        self.training_progress = QProgressBar()
        training_layout.addWidget(self.training_progress)
        
        self.training_log = QTextEdit()
        self.training_log.setReadOnly(True)
        self.training_log.setMaximumHeight(150)
        self.training_log.setPlaceholderText("Training log will appear here...")
        training_layout.addWidget(self.training_log)
        
        training_group.setLayout(training_layout)
        layout.addWidget(training_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_targets_tab(self) -> QWidget:
        """Create targets and AI description configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Target detection settings
        target_group = QGroupBox("Target Detection Settings")
        target_layout = QFormLayout()
        
        self.target_confidence = QDoubleSpinBox()
        self.target_confidence.setRange(0.1, 1.0)
        self.target_confidence.setValue(0.6)
        self.target_confidence.setSingleStep(0.05)
        target_layout.addRow("Detection Confidence:", self.target_confidence)
        
        colors_label = QLabel("Target Colors: Black, White, Red, Yellow, Blue, Green")
        colors_label.setStyleSheet("color: #666;")
        target_layout.addRow("", colors_label)
        
        target_group.setLayout(target_layout)
        layout.addWidget(target_group)
        
        # AI description system
        ai_group = QGroupBox("AI Description System (OpenRouter)")
        ai_layout = QVBoxLayout()
        
        self.ai_enabled_check = QCheckBox("Enable AI-Powered Descriptions")
        self.ai_enabled_check.setChecked(True)
        ai_layout.addWidget(self.ai_enabled_check)
        
        ai_form = QFormLayout()
        
        self.ai_api_key = QLineEdit()
        self.ai_api_key.setPlaceholderText("Enter OpenRouter API key...")
        self.ai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        ai_form.addRow("API Key:", self.ai_api_key)
        
        self.ai_model_label = QLabel("Model: NVIDIA Nemotron Nano 12B V2 VL (Free)")
        self.ai_model_label.setStyleSheet("color: #28a745; font-weight: bold;")
        ai_form.addRow("", self.ai_model_label)
        
        ai_layout.addLayout(ai_form)
        
        test_ai_btn = QPushButton("🔍 Test API Connection")
        test_ai_btn.clicked.connect(self._test_ai_api)
        ai_layout.addWidget(test_ai_btn)
        
        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)
        
        # Target descriptions viewer
        descriptions_group = QGroupBox("Detected Targets & Descriptions")
        descriptions_layout = QVBoxLayout()
        
        self.descriptions_text = QTextEdit()
        self.descriptions_text.setReadOnly(True)
        self.descriptions_text.setPlaceholderText(
            "Target descriptions will appear here during mission...\n\n"
            "Example:\n"
            "Target 1: On the north face of the building, 3.2m above ground "
            "and 1.6m from the western wall. The colour is blue."
        )
        descriptions_layout.addWidget(self.descriptions_text)
        
        descriptions_group.setLayout(descriptions_layout)
        layout.addWidget(descriptions_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    # ===== Helper Methods =====
    
    def load_default_config(self):
        """Load default configuration"""
        try:
            config_path = Path("config/task1_fire_reconnaissance.yaml")
            if config_path.exists():
                with open(config_path) as f:
                    self.mission_config = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def _add_boundary_point(self, table: QTableWidget):
        """Add GPS point to boundary table"""
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem("0.0"))  # Longitude
        table.setItem(row, 1, QTableWidgetItem("0.0"))  # Latitude
    
    def _remove_boundary_point(self, table: QTableWidget):
        """Remove selected boundary point"""
        current_row = table.currentRow()
        if current_row >= 0:
            table.removeRow(current_row)
    
    def _import_boundary_csv(self, table: QTableWidget):
        """Import boundary from CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Boundary CSV", "", "CSV Files (*.csv)"
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    reader = csv.reader(f)
                    next(reader, None)  # Skip header
                    table.setRowCount(0)
                    for row_data in reader:
                        if len(row_data) >= 2:
                            row = table.rowCount()
                            table.insertRow(row)
                            table.setItem(row, 0, QTableWidgetItem(row_data[0]))  # Lon
                            table.setItem(row, 1, QTableWidgetItem(row_data[1]))  # Lat
                QMessageBox.information(self, "Success", "Boundary imported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import CSV: {e}")
    
    def _send_to_missionplanner(self):
        """Send boundaries to MissionPlanner"""
        QMessageBox.information(
            self, "MissionPlanner Integration",
            "This feature will upload geofences to MissionPlanner.\n"
            "Implementation requires MissionPlanner API connection."
        )
    
    def _calculate_scene_perimeter(self):
        """Calculate and display scene perimeter"""
        try:
            lat = float(self.building_lat.text())
            lon = float(self.building_lon.text())
            length = self.building_length.value()
            width = self.building_width.value()
            buffer = self.scene_buffer.value()
            
            # Simplified calculation
            info = f"Building Center: ({lat:.6f}, {lon:.6f})\n"
            info += f"Scene Area: {(length + 2*buffer) * (width + 2*buffer):.1f} m²\n"
            info += f"Buffer Zone: {buffer}m around perimeter"
            
            self.perimeter_info.setText(info)
        except ValueError:
            self.perimeter_info.setText("Invalid GPS coordinates")
    
    def _add_waypoint(self):
        """Add waypoint to lap course"""
        row = self.waypoints_table.rowCount()
        self.waypoints_table.insertRow(row)
        self.waypoints_table.setItem(row, 0, QTableWidgetItem("0.0"))
        self.waypoints_table.setItem(row, 1, QTableWidgetItem("0.0"))
        self.waypoints_table.setItem(row, 2, QTableWidgetItem("50.0"))
    
    def _remove_waypoint(self):
        """Remove selected waypoint"""
        current_row = self.waypoints_table.currentRow()
        if current_row >= 0:
            self.waypoints_table.removeRow(current_row)
    
    def _import_waypoints(self):
        """Import waypoints from CSV"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Waypoints CSV", "", "CSV Files (*.csv)"
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    reader = csv.reader(f)
                    next(reader, None)
                    self.waypoints_table.setRowCount(0)
                    for row_data in reader:
                        if len(row_data) >= 3:
                            row = self.waypoints_table.rowCount()
                            self.waypoints_table.insertRow(row)
                            self.waypoints_table.setItem(row, 0, QTableWidgetItem(row_data[0]))
                            self.waypoints_table.setItem(row, 1, QTableWidgetItem(row_data[1]))
                            self.waypoints_table.setItem(row, 2, QTableWidgetItem(row_data[2]))
                QMessageBox.information(self, "Success", "Waypoints imported!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import: {e}")
    
    def _update_payload_calculator(self):
        """Update payload fraction calculations"""
        # Calculate payload weight
        payload_weight = 0
        if self.radio_check.isChecked():
            payload_weight += 500
        if self.oxygen_check.isChecked():
            payload_weight += 1000
        if self.ladder_check.isChecked():
            payload_weight += 3000
        
        # Calculate total weight
        uav_weight = self.uav1_weight.value()
        if self.uav_count_spin.value() == 2:
            uav_weight += self.uav2_weight.value()
        
        total_weight = uav_weight + payload_weight
        
        # Calculate payload fraction
        if total_weight > 0:
            pf = payload_weight / total_weight
            score = min(pf, 0.35) / 0.35 * 20.0
        else:
            pf = 0
            score = 0
        
        # Update display
        summary = f"Total Payload: {payload_weight}g\n"
        summary += f"Total System Weight: {total_weight}g\n"
        summary += f"Payload Fraction: {pf:.3f} ({pf*100:.1f}%)\n"
        summary += f"Expected Score: {score:.1f} / 20 pts"
        
        self.payload_summary.setText(summary)
        self.current_scores['payload_fraction'] = score
        self._update_score_display()
    
    def _capture_staging_pad_image(self):
        """Capture image for staging pad training"""
        QMessageBox.information(
            self, "Image Capture",
            "This feature will capture the current video frame and save it to "
            "the training dataset folder for staging pad detection."
        )
    
    def _train_staging_pad_model(self):
        """Train custom YOLO model for staging pad detection"""
        QMessageBox.information(
            self, "Model Training",
            "This feature will fine-tune YOLOv8n on captured staging pad images.\n"
            "Training requires at least 50 annotated images."
        )
    
    def _test_ai_api(self):
        """Test OpenRouter API connection"""
        if not self.ai_api_key.text():
            QMessageBox.warning(self, "API Key Required", "Please enter your OpenRouter API key.")
            return
        
        QMessageBox.information(
            self, "API Test",
            "This will test the connection to OpenRouter API.\n"
            "Implementation requires network request to:\n"
            "https://openrouter.ai/api/v1/chat/completions"
        )
    
    def _on_start_mission(self):
        """Handle mission start"""
        # Collect configuration from UI
        config = self._collect_mission_config()
        
        # Validate configuration
        if not self._validate_config(config):
            return
        
        # Update UI state
        self.mission_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.state_label.setText("State: PRE-FLIGHT CHECK")
        
        # Emit signal to start mission
        self.mission_start_requested.emit(config)
    
    def _on_stop_mission(self):
        """Handle mission stop"""
        reply = QMessageBox.question(
            self, "Stop Mission",
            "Are you sure you want to stop the mission?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.mission_running = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.state_label.setText("State: STOPPED")
            self.mission_stop_requested.emit()
    
    def _on_export_data(self):
        """Export mission data"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Target Descriptions",
            f"Task_1_{self.team_name_edit.text()}_targets.txt",
            "Text Files (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.descriptions_text.toPlainText())
                QMessageBox.information(self, "Success", f"Data exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {e}")
    
    def _collect_mission_config(self) -> Dict[str, Any]:
        """Collect all mission configuration from UI"""
        config = {
            'drone_type': 'quadcopter' if self.quadcopter_radio.isChecked() else 'vtol_tiltrotor',
            'uav_count': self.uav_count_spin.value(),
            'uav_weights_g': [self.uav1_weight.value(), self.uav2_weight.value()],
            'team_name': self.team_name_edit.text(),
            'timeout': self.mission_timeout.value(),
            'altitude_limit_ft': self.altitude_limit.value(),
            
            # Boundaries
            'soft_boundary': self._get_boundary_coords(self.soft_boundary_table),
            'hard_boundary': self._get_boundary_coords(self.hard_boundary_table),
            
            # Building
            'building_gps': [
                float(self.building_lat.text() or 0),
                float(self.building_lon.text() or 0),
                self.building_alt.value()
            ],
            'building_dimensions': [
                self.building_length.value(),
                self.building_width.value(),
                self.building_height.value()
            ],
            'building_orientation': self.building_orientation.value(),
            'scene_buffer_m': self.scene_buffer.value(),
            
            # Lap course
            'lap_waypoints': self._get_waypoint_coords(),
            'target_laps': self.target_laps.value(),
            
            # Equipment
            'equipment_selection': {
                'radio': self.radio_check.isChecked(),
                'oxygen': self.oxygen_check.isChecked(),
                'ladder': self.ladder_check.isChecked()
            },
            
            # AI
            'ai_description_enabled': self.ai_enabled_check.isChecked(),
            'ai_api_key': self.ai_api_key.text(),
            'target_detection_confidence': self.target_confidence.value(),
        }
        
        return config
    
    def _get_boundary_coords(self, table: QTableWidget) -> List[Tuple[float, float]]:
        """Extract boundary coordinates from table"""
        coords = []
        for row in range(table.rowCount()):
            try:
                lon = float(table.item(row, 0).text())
                lat = float(table.item(row, 1).text())
                coords.append((lat, lon))
            except (ValueError, AttributeError):
                pass
        return coords
    
    def _get_waypoint_coords(self) -> List[Tuple[float, float, float]]:
        """Extract waypoint coordinates from table"""
        coords = []
        for row in range(self.waypoints_table.rowCount()):
            try:
                lat = float(self.waypoints_table.item(row, 0).text())
                lon = float(self.waypoints_table.item(row, 1).text())
                alt = float(self.waypoints_table.item(row, 2).text())
                coords.append((lat, lon, alt))
            except (ValueError, AttributeError):
                pass
        return coords
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate mission configuration"""
        errors = []
        
        if not config['team_name']:
            errors.append("Team name is required")
        
        if config['target_laps'] > 0 and not config['lap_waypoints']:
            errors.append("Lap waypoints required when target laps > 0")
        
        if config['building_gps'] == [0.0, 0.0, 0.0]:
            errors.append("Building GPS location not configured")
        
        if errors:
            QMessageBox.warning(self, "Configuration Error", "\n".join(errors))
            return False
        
        return True
    
    def _update_score_display(self):
        """Update scoring table"""
        scores = self.current_scores
        total = sum(scores.values())
        
        score_items = [
            ("Target Detection", f"{scores['target_detection']:.1f} / 25"),
            ("Equipment Delivery", f"{scores['equipment_delivery']:.1f} / 20"),
            ("Distance Flown", f"{scores['distance_flown']:.1f} / 30"),
            ("Payload Fraction", f"{scores['payload_fraction']:.1f} / 20"),
            ("Safe Landing", f"{scores['safe_landing']:.1f} / 5"),
            ("TOTAL SCORE", f"{total:.1f} / 100")
        ]
        
        for row, (_, score_text) in enumerate(score_items):
            self.score_table.item(row, 1).setText(score_text)
    
    # ===== Public Methods for External Updates =====
    
    def update_mission_state(self, state: str):
        """Update mission state display"""
        self.state_label.setText(f"State: {state}")
    
    def update_lap_count(self, current: int, target: int):
        """Update lap counter"""
        self.lap_label.setText(f"Laps: {current}/{target}")
    
    def update_target_count(self, count: int):
        """Update target counter"""
        self.target_label.setText(f"Targets: {count}")
    
    def update_equipment_status(self, delivered: int, total: int):
        """Update equipment delivery status"""
        self.equipment_label.setText(f"Equipment: {delivered}/{total}")
    
    def update_scores(self, scores: Dict[str, float]):
        """Update all score components"""
        self.current_scores.update(scores)
        self._update_score_display()
    
    def add_target_description(self, description: str):
        """Add target description to viewer"""
        current = self.descriptions_text.toPlainText()
        if current:
            current += "\n\n"
        target_num = len(self.detected_targets) + 1
        current += f"Target {target_num}: {description}"
        self.descriptions_text.setText(current)
        self.detected_targets.append(description)
