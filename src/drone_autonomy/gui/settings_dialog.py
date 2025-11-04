"""
Settings Dialog for Drone Autonomy GUI

Provides interface for:
- Depth model selection (Depth Anything V2 vs MiDaS)
- Device selection (CUDA vs CPU)
- Performance tuning options
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QComboBox, QLabel, QGroupBox, QDialogButtonBox,
                             QSpinBox, QDoubleSpinBox, QCheckBox, QTabWidget,
                             QWidget, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal


class SettingsDialog(QDialog):
    """
    Settings dialog for configuring the vision pipeline
    """
    
    # Signal emitted when settings are applied
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, current_settings: Dict[str, Any] = None, parent=None):
        super().__init__(parent)
        
        self.current_settings = current_settings or {}
        self.new_settings = {}
        
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.init_ui()
        self.load_current_settings()
        
    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        
        # Create tabs for different settings categories
        tabs = QTabWidget()
        
        # Depth Estimation tab
        depth_tab = self._create_depth_settings()
        tabs.addTab(depth_tab, "Depth Estimation")
        
        # Detection tab
        detection_tab = self._create_detection_settings()
        tabs.addTab(detection_tab, "Object Detection")
        
        # Performance tab
        performance_tab = self._create_performance_settings()
        tabs.addTab(performance_tab, "Performance")
        
        layout.addWidget(tabs)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply_settings)
        
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
    def _create_depth_settings(self) -> QWidget:
        """Create depth estimation settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Depth Model Selection
        model_group = QGroupBox("Depth Model")
        model_layout = QVBoxLayout()
        
        model_layout.addWidget(QLabel("Select Depth Estimation Model:"))
        
        self.depth_model_combo = QComboBox()
        self.depth_model_combo.addItem("Depth Anything V2 (ViT-S) - Balanced", "depth_anything_v2_vits")
        self.depth_model_combo.addItem("Depth Anything V2 (ViT-B) - Better Quality", "depth_anything_v2_vitb")
        self.depth_model_combo.addItem("Depth Anything V2 (ViT-L) - Best Quality", "depth_anything_v2_vitl")
        self.depth_model_combo.addItem("MiDaS DPT_Hybrid - Fast & High Quality", "dpt_hybrid")
        self.depth_model_combo.addItem("MiDaS DPT_Large - Highest Quality", "dpt_large")
        self.depth_model_combo.addItem("MiDaS Small - Lightweight", "midas_small")
        self.depth_model_combo.currentIndexChanged.connect(self._on_depth_model_changed)
        model_layout.addWidget(self.depth_model_combo)
        
        # Model description
        self.depth_model_desc = QLabel("")
        self.depth_model_desc.setWordWrap(True)
        self.depth_model_desc.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        model_layout.addWidget(self.depth_model_desc)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # Device Selection
        device_group = QGroupBox("Compute Device")
        device_layout = QVBoxLayout()
        
        device_layout.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        
        # Check CUDA availability
        try:
            import torch
            if torch.cuda.is_available():
                self.device_combo.addItem(f"CUDA (GPU: {torch.cuda.get_device_name(0)})", "cuda")
                self.device_combo.addItem("CPU", "cpu")
            else:
                self.device_combo.addItem("CPU (CUDA not available)", "cpu")
        except ImportError:
            self.device_combo.addItem("CPU (PyTorch not installed)", "cpu")
            
        device_layout.addWidget(self.device_combo)
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)
        
        # Depth Processing Options
        processing_group = QGroupBox("Processing Options")
        processing_layout = QVBoxLayout()
        
        # Input resolution
        processing_layout.addWidget(QLabel("Input Width:"))
        self.depth_width_spin = QSpinBox()
        self.depth_width_spin.setRange(320, 1920)
        self.depth_width_spin.setSingleStep(160)
        self.depth_width_spin.setValue(640)
        processing_layout.addWidget(self.depth_width_spin)
        
        processing_layout.addWidget(QLabel("Input Height:"))
        self.depth_height_spin = QSpinBox()
        self.depth_height_spin.setRange(240, 1080)
        self.depth_height_spin.setSingleStep(120)
        self.depth_height_spin.setValue(480)
        processing_layout.addWidget(self.depth_height_spin)
        
        # Output scale
        processing_layout.addWidget(QLabel("Output Scale Factor:"))
        self.output_scale_spin = QDoubleSpinBox()
        self.output_scale_spin.setRange(0.25, 1.0)
        self.output_scale_spin.setSingleStep(0.25)
        self.output_scale_spin.setValue(0.5)
        self.output_scale_spin.setToolTip("Scale down depth output for better performance (0.5 = half resolution)")
        processing_layout.addWidget(self.output_scale_spin)
        
        processing_group.setLayout(processing_layout)
        layout.addWidget(processing_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def _create_detection_settings(self) -> QWidget:
        """Create object detection settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # YOLO Settings
        yolo_group = QGroupBox("YOLO Detection")
        yolo_layout = QVBoxLayout()
        
        yolo_layout.addWidget(QLabel("Confidence Threshold:"))
        self.yolo_confidence_spin = QDoubleSpinBox()
        self.yolo_confidence_spin.setRange(0.1, 1.0)
        self.yolo_confidence_spin.setSingleStep(0.05)
        self.yolo_confidence_spin.setValue(0.5)
        yolo_layout.addWidget(self.yolo_confidence_spin)
        
        yolo_layout.addWidget(QLabel("NMS Threshold:"))
        self.yolo_nms_spin = QDoubleSpinBox()
        self.yolo_nms_spin.setRange(0.1, 1.0)
        self.yolo_nms_spin.setSingleStep(0.05)
        self.yolo_nms_spin.setValue(0.4)
        yolo_layout.addWidget(self.yolo_nms_spin)
        
        yolo_layout.addWidget(QLabel("Image Size:"))
        self.yolo_imgsz_spin = QSpinBox()
        self.yolo_imgsz_spin.setRange(320, 1280)
        self.yolo_imgsz_spin.setSingleStep(160)
        self.yolo_imgsz_spin.setValue(640)
        yolo_layout.addWidget(self.yolo_imgsz_spin)
        
        yolo_group.setLayout(yolo_layout)
        layout.addWidget(yolo_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def _create_performance_settings(self) -> QWidget:
        """Create performance settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Performance options
        perf_group = QGroupBox("Performance Tuning")
        perf_layout = QVBoxLayout()
        
        self.enable_depth_checkbox = QCheckBox("Enable Depth Estimation")
        self.enable_depth_checkbox.setChecked(True)
        perf_layout.addWidget(self.enable_depth_checkbox)
        
        self.enable_detection_checkbox = QCheckBox("Enable Object Detection")
        self.enable_detection_checkbox.setChecked(True)
        perf_layout.addWidget(self.enable_detection_checkbox)
        
        perf_layout.addWidget(QLabel("\nNote: Disabling features can improve FPS"))
        
        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)
        
        # Display options
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout()
        
        self.show_fps_checkbox = QCheckBox("Show FPS Counter")
        self.show_fps_checkbox.setChecked(False)
        self.show_fps_checkbox.setToolTip("Display frames per second in top-left corner of video feed")
        display_layout.addWidget(self.show_fps_checkbox)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def _on_depth_model_changed(self, index: int):
        """Update description when depth model changes"""
        descriptions = {
            "depth_anything_v2_vits": "Balanced speed and quality. Good for most use cases. ~30-60 FPS on GPU.",
            "depth_anything_v2_vitb": "Better depth quality but slower. ~20-40 FPS on GPU.",
            "depth_anything_v2_vitl": "Best quality but slowest. ~10-20 FPS on GPU. Not recommended for real-time.",
            "dpt_hybrid": "RECOMMENDED: Fast (140ms/7 FPS) with high quality. DPT model with ViT-Hybrid backbone. Best balance of speed and quality.",
            "dpt_large": "Highest quality (174ms/6 FPS). DPT Large model. Use when quality is critical.",
            "midas_small": "Lightweight (246ms/4 FPS). Smallest MiDaS model. Good for memory-constrained devices.",
        }
        
        model_key = self.depth_model_combo.currentData()
        self.depth_model_desc.setText(descriptions.get(model_key, ""))
        
    def load_current_settings(self):
        """Load current settings into UI"""
        # Depth settings
        if 'depth' in self.current_settings:
            depth_config = self.current_settings['depth']
            
            # Set model
            model = depth_config.get('model', 'depth_anything_v2_vits')
            index = self.depth_model_combo.findData(model)
            if index >= 0:
                self.depth_model_combo.setCurrentIndex(index)
                
            # Set device
            device = depth_config.get('device', 'cuda')
            index = self.device_combo.findData(device)
            if index >= 0:
                self.device_combo.setCurrentIndex(index)
                
            # Set input size
            input_size = depth_config.get('input_size', [640, 480])
            self.depth_width_spin.setValue(input_size[0])
            self.depth_height_spin.setValue(input_size[1])
            
            # Set output scale
            self.output_scale_spin.setValue(depth_config.get('output_scale', 0.5))
            
        # Detection settings
        if 'detection' in self.current_settings:
            det_config = self.current_settings['detection']
            self.yolo_confidence_spin.setValue(det_config.get('confidence_threshold', 0.5))
            self.yolo_nms_spin.setValue(det_config.get('nms_threshold', 0.4))
            self.yolo_imgsz_spin.setValue(det_config.get('imgsz', 640))
            
    def _apply_settings(self):
        """Apply settings without closing dialog"""
        self.new_settings = self._collect_settings()
        self.settings_changed.emit(self.new_settings)
        QMessageBox.information(self, "Settings Applied", 
                               "Settings have been applied. The model will reload on next frame.")
        
    def accept(self):
        """Accept dialog and apply settings"""
        self.new_settings = self._collect_settings()
        self.settings_changed.emit(self.new_settings)
        super().accept()
        
    def _collect_settings(self) -> Dict[str, Any]:
        """Collect all settings from UI"""
        settings = {
            'depth': {
                'model': self.depth_model_combo.currentData(),
                'device': self.device_combo.currentData(),
                'input_size': [self.depth_width_spin.value(), self.depth_height_spin.value()],
                'output_scale': self.output_scale_spin.value(),
            },
            'detection': {
                'confidence_threshold': self.yolo_confidence_spin.value(),
                'nms_threshold': self.yolo_nms_spin.value(),
                'imgsz': self.yolo_imgsz_spin.value(),
            },
            'performance': {
                'enable_depth': self.enable_depth_checkbox.isChecked(),
                'enable_detection': self.enable_detection_checkbox.isChecked(),
            },
            'display': {
                'show_fps': self.show_fps_checkbox.isChecked(),
            }
        }
        return settings
        
    def get_settings(self) -> Dict[str, Any]:
        """Get the new settings"""
        return self.new_settings
