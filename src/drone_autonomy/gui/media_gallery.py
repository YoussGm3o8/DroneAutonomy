"""
Media Gallery for Saved Images and Videos

Displays thumbnails and allows playback/viewing of:
- Captured target photos
- Competition deliverables
- Video recordings
- Screenshots
"""

import os
from typing import List, Optional
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QListWidget, QListWidgetItem, QFileDialog,
                             QGroupBox, QTabWidget, QTextEdit, QSplitter)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon
import cv2


class MediaGallery(QWidget):
    """
    Gallery view for saved media files
    """
    
    # Signals
    media_selected = pyqtSignal(str)  # file_path
    video_play_requested = pyqtSignal(str)  # file_path
    
    def __init__(self, media_dirs: Optional[dict] = None, parent=None):
        super().__init__(parent)
        
        # Default media directories
        self.media_dirs = media_dirs or {
            'photos': 'output/photos',
            'videos': 'output/videos',
            'screenshots': 'output/screenshots',
            'deliverables': 'output/deliverables'
        }
        
        self.current_file = None
        
        self.init_ui()
        self.refresh_gallery()
        
    def init_ui(self):
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        
        # Title and controls
        header_layout = QHBoxLayout()
        title = QLabel("Media Gallery")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_gallery)
        header_layout.addWidget(self.refresh_btn)
        
        self.open_folder_btn = QPushButton("📁 Open Folder")
        self.open_folder_btn.clicked.connect(self._open_folder)
        header_layout.addWidget(self.open_folder_btn)
        
        main_layout.addLayout(header_layout)
        
        # Splitter for list and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Tab widget for different media types
        self.tabs = QTabWidget()
        
        # Photos tab
        self.photos_list = QListWidget()
        self.photos_list.setIconSize(QSize(100, 100))
        self.photos_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.photos_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.photos_list.setSpacing(10)
        self.photos_list.itemClicked.connect(self._on_item_clicked)
        self.tabs.addTab(self.photos_list, "📷 Photos")
        
        # Videos tab
        self.videos_list = QListWidget()
        self.videos_list.setIconSize(QSize(100, 100))
        self.videos_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.videos_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.videos_list.setSpacing(10)
        self.videos_list.itemDoubleClicked.connect(self._on_video_double_clicked)
        self.tabs.addTab(self.videos_list, "🎥 Videos")
        
        # Screenshots tab
        self.screenshots_list = QListWidget()
        self.screenshots_list.setIconSize(QSize(100, 100))
        self.screenshots_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.screenshots_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.screenshots_list.setSpacing(10)
        self.screenshots_list.itemClicked.connect(self._on_item_clicked)
        self.tabs.addTab(self.screenshots_list, "🖼️ Screenshots")
        
        # Deliverables tab
        self.deliverables_list = QListWidget()
        self.deliverables_list.itemClicked.connect(self._on_deliverable_clicked)
        self.tabs.addTab(self.deliverables_list, "📋 Deliverables")
        
        splitter.addWidget(self.tabs)
        
        # Preview panel
        preview_panel = QWidget()
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel("Select a file to preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 2px solid #333; background-color: black; color: white;")
        self.preview_label.setMinimumSize(400, 300)
        self.preview_label.setScaledContents(True)
        preview_layout.addWidget(self.preview_label)
        
        # File info
        self.file_info = QTextEdit()
        self.file_info.setReadOnly(True)
        self.file_info.setMaximumHeight(150)
        self.file_info.setPlaceholderText("File information will appear here...")
        preview_layout.addWidget(self.file_info)
        
        # Preview controls
        preview_controls = QHBoxLayout()
        
        self.play_video_btn = QPushButton("▶ Play Video")
        self.play_video_btn.clicked.connect(self._play_video)
        self.play_video_btn.setEnabled(False)
        preview_controls.addWidget(self.play_video_btn)
        
        self.export_btn = QPushButton("💾 Export")
        self.export_btn.clicked.connect(self._export_file)
        self.export_btn.setEnabled(False)
        preview_controls.addWidget(self.export_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.setStyleSheet("background-color: #dc3545; color: white;")
        self.delete_btn.clicked.connect(self._delete_file)
        self.delete_btn.setEnabled(False)
        preview_controls.addWidget(self.delete_btn)
        
        preview_controls.addStretch()
        preview_layout.addLayout(preview_controls)
        
        preview_panel.setLayout(preview_layout)
        splitter.addWidget(preview_panel)
        
        splitter.setSizes([300, 500])
        main_layout.addWidget(splitter)
        
        self.setLayout(main_layout)
        
    def refresh_gallery(self):
        """Refresh all media lists"""
        self._load_photos()
        self._load_videos()
        self._load_screenshots()
        self._load_deliverables()
        
    def _load_photos(self):
        """Load photos into gallery"""
        self.photos_list.clear()
        photos_dir = self.media_dirs['photos']
        
        if not os.path.exists(photos_dir):
            os.makedirs(photos_dir, exist_ok=True)
            return
            
        for file in sorted(Path(photos_dir).glob('*.jpg'), reverse=True):
            self._add_image_item(self.photos_list, str(file))
            
        for file in sorted(Path(photos_dir).glob('*.png'), reverse=True):
            self._add_image_item(self.photos_list, str(file))
            
    def _load_videos(self):
        """Load videos into gallery"""
        self.videos_list.clear()
        videos_dir = self.media_dirs['videos']
        
        if not os.path.exists(videos_dir):
            os.makedirs(videos_dir, exist_ok=True)
            return
            
        for file in sorted(Path(videos_dir).glob('*.mp4'), reverse=True):
            self._add_video_item(self.videos_list, str(file))
            
        for file in sorted(Path(videos_dir).glob('*.avi'), reverse=True):
            self._add_video_item(self.videos_list, str(file))
            
    def _load_screenshots(self):
        """Load screenshots into gallery"""
        self.screenshots_list.clear()
        screenshots_dir = self.media_dirs['screenshots']
        
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir, exist_ok=True)
            return
            
        for file in sorted(Path(screenshots_dir).glob('*.jpg'), reverse=True):
            self._add_image_item(self.screenshots_list, str(file))
            
    def _load_deliverables(self):
        """Load deliverables into list"""
        self.deliverables_list.clear()
        deliverables_dir = self.media_dirs['deliverables']
        
        if not os.path.exists(deliverables_dir):
            os.makedirs(deliverables_dir, exist_ok=True)
            return
            
        # Load text descriptions
        for file in sorted(Path(deliverables_dir).glob('*.txt'), reverse=True):
            item = QListWidgetItem(f"📄 {file.name}")
            item.setData(Qt.ItemDataRole.UserRole, str(file))
            self.deliverables_list.addItem(item)
            
        # Load JSON files
        for file in sorted(Path(deliverables_dir).glob('*.json'), reverse=True):
            item = QListWidgetItem(f"📋 {file.name}")
            item.setData(Qt.ItemDataRole.UserRole, str(file))
            self.deliverables_list.addItem(item)
            
        # Load CSV logs
        for file in sorted(Path(deliverables_dir).glob('*.csv'), reverse=True):
            item = QListWidgetItem(f"📊 {file.name}")
            item.setData(Qt.ItemDataRole.UserRole, str(file))
            self.deliverables_list.addItem(item)
            
    def _add_image_item(self, list_widget: QListWidget, file_path: str):
        """Add image item with thumbnail"""
        # Create thumbnail
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            thumbnail = pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
            icon = QIcon(thumbnail)
            
            item = QListWidgetItem(icon, Path(file_path).name)
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            list_widget.addItem(item)
            
    def _add_video_item(self, list_widget: QListWidget, file_path: str):
        """Add video item with first frame thumbnail"""
        # Extract first frame as thumbnail
        cap = cv2.VideoCapture(file_path)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            # Convert to RGB and create thumbnail
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame_rgb.shape[:2]
            from PyQt6.QtGui import QImage
            q_image = QImage(frame_rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            thumbnail = pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
            icon = QIcon(thumbnail)
            
            item = QListWidgetItem(icon, Path(file_path).name)
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            list_widget.addItem(item)
        else:
            # Fallback text item
            item = QListWidgetItem(f"🎥 {Path(file_path).name}")
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            list_widget.addItem(item)
            
    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle image/screenshot item click"""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        self.current_file = file_path
        
        # Display preview
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
            
        # Display file info
        self._display_file_info(file_path)
        
        # Enable buttons
        self.play_video_btn.setEnabled(False)
        self.export_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        
        self.media_selected.emit(file_path)
        
    def _on_video_double_clicked(self, item: QListWidgetItem):
        """Handle video item double-click"""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        self.video_play_requested.emit(file_path)
        
    def _on_deliverable_clicked(self, item: QListWidgetItem):
        """Handle deliverable item click"""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        self.current_file = file_path
        
        # Display file contents
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            self.file_info.setPlainText(content)
            self.preview_label.setText(f"📄 {Path(file_path).name}\n\nSee file info below")
        except Exception as e:
            self.file_info.setPlainText(f"Error reading file: {e}")
            
        # Enable buttons
        self.play_video_btn.setEnabled(False)
        self.export_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        
    def _display_file_info(self, file_path: str):
        """Display file information"""
        file_stat = os.stat(file_path)
        file_size = file_stat.st_size / 1024  # KB
        
        from datetime import datetime
        mod_time = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        info_text = f"File: {Path(file_path).name}\n"
        info_text += f"Path: {file_path}\n"
        info_text += f"Size: {file_size:.1f} KB\n"
        info_text += f"Modified: {mod_time}\n"
        
        # Add image dimensions if applicable
        if file_path.lower().endswith(('.jpg', '.png', '.jpeg')):
            pixmap = QPixmap(file_path)
            info_text += f"Dimensions: {pixmap.width()}x{pixmap.height()}\n"
            
        self.file_info.setPlainText(info_text)
        
    def _play_video(self):
        """Play selected video"""
        if self.current_file:
            self.video_play_requested.emit(self.current_file)
            
    def _export_file(self):
        """Export/copy selected file"""
        if not self.current_file:
            return
            
        file_name = Path(self.current_file).name
        save_path, _ = QFileDialog.getSaveFileName(self, "Export File", file_name)
        
        if save_path:
            import shutil
            shutil.copy2(self.current_file, save_path)
            print(f"File exported to: {save_path}")
            
    def _delete_file(self):
        """Delete selected file"""
        if not self.current_file:
            return
            
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "Delete File",
                                     f"Delete {Path(self.current_file).name}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(self.current_file)
                print(f"Deleted: {self.current_file}")
                self.refresh_gallery()
                self.preview_label.clear()
                self.preview_label.setText("Select a file to preview")
                self.file_info.clear()
                self.current_file = None
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete file: {e}")
                
    def _open_folder(self):
        """Open current media folder in file explorer"""
        current_tab = self.tabs.currentIndex()
        
        if current_tab == 0:  # Photos
            folder = self.media_dirs['photos']
        elif current_tab == 1:  # Videos
            folder = self.media_dirs['videos']
        elif current_tab == 2:  # Screenshots
            folder = self.media_dirs['screenshots']
        else:  # Deliverables
            folder = self.media_dirs['deliverables']
            
        os.makedirs(folder, exist_ok=True)
        
        # Open folder in system file explorer
        import subprocess
        import sys
        if sys.platform == 'win32':
            subprocess.Popen(['explorer', os.path.abspath(folder)])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', folder])
        else:
            subprocess.Popen(['xdg-open', folder])
