"""
Results Viewer for Task Outputs

Displays:
- Task scores and performance metrics
- Generated descriptions (text/JSON)
- Competition logs
- Error reports
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QPushButton, QLabel, QTabWidget, QTableWidget,
                             QTableWidgetItem, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import json


class ResultsViewer(QWidget):
    """
    Viewer for task results and outputs
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_results = {}
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Task Results")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Tab widget for different result types
        self.tabs = QTabWidget()
        
        # Scores tab
        scores_widget = QWidget()
        scores_layout = QVBoxLayout()
        
        self.scores_table = QTableWidget()
        self.scores_table.setColumnCount(2)
        self.scores_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.scores_table.horizontalHeader().setStretchLastSection(True)
        scores_layout.addWidget(self.scores_table)
        
        scores_widget.setLayout(scores_layout)
        self.tabs.addTab(scores_widget, "📊 Scores")
        
        # Descriptions tab
        descriptions_widget = QWidget()
        descriptions_layout = QVBoxLayout()
        
        self.descriptions_text = QTextEdit()
        self.descriptions_text.setReadOnly(True)
        self.descriptions_text.setPlaceholderText("Target descriptions will appear here...")
        descriptions_layout.addWidget(self.descriptions_text)
        
        # Description controls
        desc_controls = QHBoxLayout()
        
        self.export_desc_btn = QPushButton("💾 Export Description")
        self.export_desc_btn.clicked.connect(self._export_description)
        desc_controls.addWidget(self.export_desc_btn)
        
        self.validate_desc_btn = QPushButton("✓ Validate Schema")
        self.validate_desc_btn.clicked.connect(self._validate_description)
        desc_controls.addWidget(self.validate_desc_btn)
        
        desc_controls.addStretch()
        descriptions_layout.addLayout(desc_controls)
        
        descriptions_widget.setLayout(descriptions_layout)
        self.tabs.addTab(descriptions_widget, "📝 Descriptions")
        
        # Logs tab
        logs_widget = QWidget()
        logs_layout = QVBoxLayout()
        
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setPlaceholderText("Task execution logs will appear here...")
        self.logs_text.setStyleSheet("font-family: 'Courier New'; font-size: 10pt;")
        logs_layout.addWidget(self.logs_text)
        
        # Log controls
        log_controls = QHBoxLayout()
        
        self.clear_logs_btn = QPushButton("🗑️ Clear Logs")
        self.clear_logs_btn.clicked.connect(self.logs_text.clear)
        log_controls.addWidget(self.clear_logs_btn)
        
        self.export_logs_btn = QPushButton("💾 Export Logs")
        self.export_logs_btn.clicked.connect(self._export_logs)
        log_controls.addWidget(self.export_logs_btn)
        
        log_controls.addStretch()
        logs_layout.addLayout(log_controls)
        
        logs_widget.setLayout(logs_layout)
        self.tabs.addTab(logs_widget, "📋 Logs")
        
        # Errors tab
        errors_widget = QWidget()
        errors_layout = QVBoxLayout()
        
        self.errors_text = QTextEdit()
        self.errors_text.setReadOnly(True)
        self.errors_text.setPlaceholderText("Errors and warnings will appear here...")
        self.errors_text.setStyleSheet("color: #dc3545; font-family: 'Courier New';")
        errors_layout.addWidget(self.errors_text)
        
        errors_widget.setLayout(errors_layout)
        self.tabs.addTab(errors_widget, "⚠️ Errors")
        
        layout.addWidget(self.tabs)
        
        # Summary group
        summary_group = QGroupBox("Session Summary")
        summary_layout = QVBoxLayout()
        
        self.summary_label = QLabel("No results available")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("padding: 10px;")
        summary_layout.addWidget(self.summary_label)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        self.setLayout(layout)
        
    def update_scores(self, scores: Dict[str, Any]):
        """Update scores table"""
        self.scores_table.setRowCount(len(scores))
        
        for i, (metric, value) in enumerate(scores.items()):
            metric_item = QTableWidgetItem(metric)
            
            # Format value
            if isinstance(value, float):
                value_str = f"{value:.2f}"
            else:
                value_str = str(value)
            value_item = QTableWidgetItem(value_str)
            
            # Color coding for important metrics
            if 'score' in metric.lower() or 'points' in metric.lower():
                value_item.setForeground(Qt.GlobalColor.blue)
                font = value_item.font()
                font.setBold(True)
                value_item.setFont(font)
                
            self.scores_table.setItem(i, 0, metric_item)
            self.scores_table.setItem(i, 1, value_item)
            
        self.current_results['scores'] = scores
        self._update_summary()
        
    def add_description(self, description: str, format_type: str = "text"):
        """Add target description"""
        if format_type == "json":
            # Pretty print JSON
            try:
                parsed = json.loads(description)
                formatted = json.dumps(parsed, indent=2)
                self.descriptions_text.append(formatted)
            except json.JSONDecodeError:
                self.descriptions_text.append(description)
        else:
            self.descriptions_text.append(description)
            
        self.descriptions_text.append("\n" + "="*50 + "\n")
        
    def add_log(self, message: str, level: str = "INFO"):
        """Add log message"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        
        # Color coding by level
        color_map = {
            'INFO': 'black',
            'WARNING': 'orange',
            'ERROR': 'red',
            'SUCCESS': 'green'
        }
        color = color_map.get(level, 'black')
        
        formatted_msg = f"[{timestamp}] [{level}] {message}"
        self.logs_text.append(formatted_msg)
        
        # Auto-scroll to bottom
        self.logs_text.verticalScrollBar().setValue(
            self.logs_text.verticalScrollBar().maximum()
        )
        
    def add_error(self, error: str):
        """Add error message"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        
        formatted_error = f"[{timestamp}] ERROR: {error}\n"
        self.errors_text.append(formatted_error)
        
    def set_result(self, result: Dict[str, Any]):
        """Set complete task result"""
        self.current_results = result
        
        # Update scores if available
        if 'scores' in result:
            self.update_scores(result['scores'])
            
        # Update description if available
        if 'description' in result:
            self.add_description(result['description'])
            
        # Update logs if available
        if 'logs' in result:
            for log in result['logs']:
                self.add_log(log.get('message', ''), log.get('level', 'INFO'))
                
        # Update errors if available
        if 'errors' in result:
            for error in result['errors']:
                self.add_error(error)
                
        self._update_summary()
        
    def _update_summary(self):
        """Update summary label"""
        if not self.current_results:
            self.summary_label.setText("No results available")
            return
            
        # Build summary text
        summary = []
        
        if 'task_name' in self.current_results:
            summary.append(f"Task: {self.current_results['task_name']}")
            
        if 'status' in self.current_results:
            summary.append(f"Status: {self.current_results['status']}")
            
        if 'scores' in self.current_results:
            total_score = self.current_results['scores'].get('total_score', 0)
            summary.append(f"Total Score: {total_score:.1f} points")
            
        if 'duration' in self.current_results:
            summary.append(f"Duration: {self.current_results['duration']:.1f}s")
            
        self.summary_label.setText(" | ".join(summary))
        
    def _export_description(self):
        """Export description to file"""
        from PyQt6.QtWidgets import QFileDialog
        
        text = self.descriptions_text.toPlainText()
        if not text:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Description", "description.txt", "Text Files (*.txt);;JSON Files (*.json)"
        )
        
        if file_path:
            with open(file_path, 'w') as f:
                f.write(text)
            print(f"Description exported to: {file_path}")
            
    def _validate_description(self):
        """Validate description schema"""
        text = self.descriptions_text.toPlainText()
        
        try:
            # Try to parse as JSON
            description_data = json.loads(text)
            
            # Import validation function
            from drone_autonomy.tasks.landmark_description import TargetDescription
            
            # Validate schema
            is_valid, errors = TargetDescription.validate_schema(description_data)
            
            if is_valid:
                self.add_log("✓ Description schema is valid", "SUCCESS")
            else:
                self.add_log("✗ Description schema validation failed:", "ERROR")
                for error in errors:
                    self.add_error(error)
        except json.JSONDecodeError as e:
            self.add_error(f"Invalid JSON format: {e}")
        except Exception as e:
            self.add_error(f"Validation error: {e}")
            
    def _export_logs(self):
        """Export logs to file"""
        from PyQt6.QtWidgets import QFileDialog
        
        text = self.logs_text.toPlainText()
        if not text:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Logs", "task_logs.txt", "Text Files (*.txt)"
        )
        
        if file_path:
            with open(file_path, 'w') as f:
                f.write(text)
            print(f"Logs exported to: {file_path}")
            
    def clear_all(self):
        """Clear all results"""
        self.current_results = {}
        self.scores_table.setRowCount(0)
        self.descriptions_text.clear()
        self.logs_text.clear()
        self.errors_text.clear()
        self.summary_label.setText("No results available")
