"""
Download Item Widget for the Download Manager application.
Custom widget for displaying individual download items with progress and controls.
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QProgressBar, 
    QPushButton, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPalette

from core.download_task import DownloadTask, DownloadStatus


class DownloadItemWidget(QWidget):
    """Custom widget for displaying a download item."""
    
    # Signals
    start_requested = pyqtSignal(str)  # download_id
    pause_requested = pyqtSignal(str)  # download_id
    resume_requested = pyqtSignal(str)  # download_id
    cancel_requested = pyqtSignal(str)  # download_id
    delete_requested = pyqtSignal(str)  # download_id
    
    def __init__(self, task: DownloadTask, parent=None):
        super().__init__(parent)
        
        self.task = task
        self.setup_ui()
        self.update_display()
    
    def setup_ui(self):
        """Setup the widget UI."""
        self.setFixedHeight(80)
        self.setFrameStyle(QFrame.StyledPanel)
        
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        
        # Left side - Download info
        info_layout = QVBoxLayout()
        
        # Filename
        self.filename_label = QLabel(self.task.filename)
        font = QFont()
        font.setBold(True)
        self.filename_label.setFont(font)
        info_layout.addWidget(self.filename_label)
        
        # URL and size info
        info_text = self.task.url
        if self.task.file_size > 0:
            info_text += f" ({self.format_bytes(self.task.file_size)})"
        
        self.info_label = QLabel(info_text)
        self.info_label.setStyleSheet("color: gray;")
        info_layout.addWidget(self.info_label)
        
        main_layout.addLayout(info_layout, 3)  # 3/5 of the width
        
        # Center - Progress
        progress_layout = QVBoxLayout()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(self.task.progress_percentage))
        progress_layout.addWidget(self.progress_bar)
        
        # Progress info (speed, ETA, etc.)
        self.progress_info_label = QLabel()
        self.progress_info_label.setAlignment(Qt.AlignCenter)
        self.progress_info_label.setStyleSheet("color: gray; font-size: 10px;")
        progress_layout.addWidget(self.progress_info_label)
        
        main_layout.addLayout(progress_layout, 1)  # 1/5 of the width
        
        # Right side - Controls
        controls_layout = QVBoxLayout()
        
        # Status label
        self.status_label = QLabel(self.task.status.value.title())
        self.status_label.setAlignment(Qt.AlignCenter)
        controls_layout.addWidget(self.status_label)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.action_button = QPushButton()
        self.action_button.clicked.connect(self.on_action_button_clicked)
        button_layout.addWidget(self.action_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.on_cancel_clicked)
        button_layout.addWidget(self.cancel_button)
        
        controls_layout.addLayout(button_layout)
        
        main_layout.addLayout(controls_layout, 1)  # 1/5 of the width
    
    def update_display(self):
        """Update the widget display with current task data."""
        # Update progress bar
        self.progress_bar.setValue(int(self.task.progress_percentage))
        
        # Update progress info
        progress_info = []
        
        if self.task.download_speed > 0:
            speed_text = self.format_speed(self.task.download_speed)
            progress_info.append(f"Speed: {speed_text}")
        
        if self.task.eta > 0:
            eta_text = self.format_time(self.task.eta)
            progress_info.append(f"ETA: {eta_text}")
        
        if self.task.downloaded_bytes > 0 and self.task.file_size > 0:
            downloaded_text = self.format_bytes(self.task.downloaded_bytes)
            total_text = self.format_bytes(self.task.file_size)
            progress_info.append(f"{downloaded_text} / {total_text}")
        
        self.progress_info_label.setText(" | ".join(progress_info))
        
        # Update status label and color
        self.status_label.setText(self.task.status.value.title())
        self.update_status_color()
        
        # Update action button
        self.update_action_button()
        
        # Update cancel button
        self.cancel_button.setEnabled(
            self.task.status in [DownloadStatus.DOWNLOADING, DownloadStatus.PAUSED, DownloadStatus.QUEUED]
        )
    
    def update_status_color(self):
        """Update status label color based on status."""
        color_map = {
            DownloadStatus.PENDING: "orange",
            DownloadStatus.QUEUED: "blue",
            DownloadStatus.DOWNLOADING: "green",
            DownloadStatus.PAUSED: "orange",
            DownloadStatus.COMPLETED: "darkgreen",
            DownloadStatus.ERROR: "red",
            DownloadStatus.CANCELLED: "gray"
        }
        
        color = color_map.get(self.task.status, "black")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
    
    def update_action_button(self):
        """Update the action button based on current status."""
        if self.task.status == DownloadStatus.PENDING:
            self.action_button.setText("Start")
            self.action_button.setEnabled(True)
        elif self.task.status == DownloadStatus.QUEUED:
            self.action_button.setText("Queued")
            self.action_button.setEnabled(False)
        elif self.task.status == DownloadStatus.DOWNLOADING:
            self.action_button.setText("Pause")
            self.action_button.setEnabled(True)
        elif self.task.status == DownloadStatus.PAUSED:
            self.action_button.setText("Resume")
            self.action_button.setEnabled(True)
        elif self.task.status == DownloadStatus.COMPLETED:
            self.action_button.setText("Open")
            self.action_button.setEnabled(True)
        elif self.task.status == DownloadStatus.ERROR:
            self.action_button.setText("Retry")
            self.action_button.setEnabled(self.task.can_retry())
        else:  # CANCELLED
            self.action_button.setText("Restart")
            self.action_button.setEnabled(True)
    
    def on_action_button_clicked(self):
        """Handle action button click."""
        if self.task.status == DownloadStatus.PENDING:
            self.start_requested.emit(self.task.id)
        elif self.task.status == DownloadStatus.DOWNLOADING:
            self.pause_requested.emit(self.task.id)
        elif self.task.status == DownloadStatus.PAUSED:
            self.resume_requested.emit(self.task.id)
        elif self.task.status == DownloadStatus.COMPLETED:
            self.open_file()
        elif self.task.status == DownloadStatus.ERROR:
            self.retry_download()
        elif self.task.status == DownloadStatus.CANCELLED:
            self.start_requested.emit(self.task.id)
    
    def on_cancel_clicked(self):
        """Handle cancel button click."""
        self.cancel_requested.emit(self.task.id)
    
    def open_file(self):
        """Open the downloaded file."""
        import os
        import subprocess
        import platform
        
        file_path = self.task.get_full_path()
        if os.path.exists(file_path):
            system = platform.system()
            try:
                if system == "Windows":
                    os.startfile(file_path)
                elif system == "Darwin":  # macOS
                    subprocess.run(["open", file_path])
                else:  # Linux
                    subprocess.run(["xdg-open", file_path])
            except Exception as e:
                print(f"Failed to open file: {e}")
    
    def retry_download(self):
        """Retry a failed download."""
        if self.task.can_retry():
            self.start_requested.emit(self.task.id)
    
    def update_task(self, task: DownloadTask):
        """Update the widget with new task data."""
        self.task = task
        self.update_display()
    
    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def format_speed(self, bytes_per_second: float) -> str:
        """Format download speed."""
        if bytes_per_second <= 0:
            return "0 B/s"
        return f"{self.format_bytes(bytes_per_second)}/s"
    
    def format_time(self, seconds: float) -> str:
        """Format time duration."""
        if seconds <= 0:
            return "Unknown"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
