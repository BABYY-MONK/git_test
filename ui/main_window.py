"""
Main Window for the Download Manager application.
Provides the primary user interface for managing downloads.
"""

import sys
from typing import List, Optional
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QPushButton, QLineEdit, QLabel, QProgressBar,
    QMenuBar, QMenu, QAction, QStatusBar, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QInputDialog, QSystemTrayIcon, QApplication
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QIcon, QPixmap

from core.download_manager import DownloadManager
from core.download_task import DownloadTask, DownloadStatus
from ui.download_item import DownloadItemWidget
from config.settings import settings


class DownloadTableWidget(QTableWidget):
    """Custom table widget for displaying downloads."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()
    
    def setup_table(self):
        """Setup the download table."""
        # Set column headers
        headers = ["Name", "Size", "Progress", "Speed", "Status", "ETA"]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Configure table properties
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        
        # Set column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Name column
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Size
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # Progress
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Speed
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # ETA
        
        self.setColumnWidth(2, 150)  # Progress bar width


class MainWindow(QMainWindow):
    """Main application window."""
    
    # Signals
    download_added = pyqtSignal(str)  # URL
    download_action = pyqtSignal(str, str)  # download_id, action
    
    def __init__(self):
        super().__init__()
        
        # Initialize download manager
        self.download_manager = DownloadManager()
        self.download_manager.add_progress_callback(self.on_progress_update)
        self.download_manager.add_status_callback(self.on_status_change)
        
        # UI components
        self.download_table = None
        self.url_input = None
        self.add_button = None
        self.status_bar = None
        self.system_tray = None
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # Update every second
        
        self.setup_ui()
        self.setup_menu()
        self.setup_system_tray()
        self.load_downloads()
        
        # Connect signals
        self.download_added.connect(self.add_download)
        self.download_action.connect(self.handle_download_action)
    
    def setup_ui(self):
        """Setup the main user interface."""
        self.setWindowTitle("Download Manager")
        self.setGeometry(100, 100, 1000, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        
        # URL input section
        url_layout = QHBoxLayout()
        
        url_label = QLabel("URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter download URL here...")
        self.url_input.returnPressed.connect(self.add_download_from_input)
        
        self.add_button = QPushButton("Add Download")
        self.add_button.clicked.connect(self.add_download_from_input)
        
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.add_button)
        
        layout.addLayout(url_layout)
        
        # Download table
        self.download_table = DownloadTableWidget()
        self.download_table.cellDoubleClicked.connect(self.on_table_double_click)
        layout.addWidget(self.download_table)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(lambda: self.handle_selected_action("start"))
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(lambda: self.handle_selected_action("pause"))
        
        self.resume_button = QPushButton("Resume")
        self.resume_button.clicked.connect(lambda: self.handle_selected_action("resume"))
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(lambda: self.handle_selected_action("cancel"))
        
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(lambda: self.handle_selected_action("delete"))
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.resume_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status_bar()
    
    def setup_menu(self):
        """Setup the application menu."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        add_action = QAction("Add Download", self)
        add_action.setShortcut("Ctrl+N")
        add_action.triggered.connect(self.show_add_download_dialog)
        file_menu.addAction(add_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Downloads menu
        downloads_menu = menubar.addMenu("Downloads")
        
        start_all_action = QAction("Start All", self)
        start_all_action.triggered.connect(self.start_all_downloads)
        downloads_menu.addAction(start_all_action)
        
        pause_all_action = QAction("Pause All", self)
        pause_all_action.triggered.connect(self.pause_all_downloads)
        downloads_menu.addAction(pause_all_action)
        
        downloads_menu.addSeparator()
        
        clear_completed_action = QAction("Clear Completed", self)
        clear_completed_action.triggered.connect(self.clear_completed_downloads)
        downloads_menu.addAction(clear_completed_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        tools_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def setup_system_tray(self):
        """Setup system tray icon."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        self.system_tray = QSystemTrayIcon(self)
        
        # Set icon (you would need to provide an actual icon file)
        # self.system_tray.setIcon(QIcon("icon.png"))
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        
        self.system_tray.setContextMenu(tray_menu)
        self.system_tray.activated.connect(self.on_tray_activated)
        
        if settings.get('show_system_tray', True):
            self.system_tray.show()
    
    def load_downloads(self):
        """Load existing downloads into the table."""
        downloads = self.download_manager.get_all_downloads()
        
        self.download_table.setRowCount(len(downloads))
        
        for row, task in enumerate(downloads):
            self.update_table_row(row, task)
    
    def update_table_row(self, row: int, task: DownloadTask):
        """Update a table row with download task data."""
        # Name
        name_item = QTableWidgetItem(task.filename)
        name_item.setData(Qt.UserRole, task.id)  # Store download ID
        self.download_table.setItem(row, 0, name_item)
        
        # Size
        size_text = self.format_bytes(task.file_size) if task.file_size > 0 else "Unknown"
        self.download_table.setItem(row, 1, QTableWidgetItem(size_text))
        
        # Progress
        progress_widget = QProgressBar()
        progress_widget.setRange(0, 100)
        progress_widget.setValue(int(task.progress_percentage))
        progress_widget.setFormat(f"{task.progress_percentage:.1f}%")
        self.download_table.setCellWidget(row, 2, progress_widget)
        
        # Speed
        speed_text = self.format_speed(task.download_speed)
        self.download_table.setItem(row, 3, QTableWidgetItem(speed_text))
        
        # Status
        status_item = QTableWidgetItem(task.status.value.title())
        self.download_table.setItem(row, 4, status_item)
        
        # ETA
        eta_text = self.format_time(task.eta) if task.eta > 0 else ""
        self.download_table.setItem(row, 5, QTableWidgetItem(eta_text))
    
    def add_download_from_input(self):
        """Add download from URL input field."""
        url = self.url_input.text().strip()
        if url:
            self.add_download(url)
            self.url_input.clear()
    
    @pyqtSlot(str)
    def add_download(self, url: str):
        """Add a new download."""
        task = self.download_manager.add_download(url)
        if task:
            # Add new row to table
            row_count = self.download_table.rowCount()
            self.download_table.insertRow(row_count)
            self.update_table_row(row_count, task)
            
            self.status_bar.showMessage(f"Added download: {task.filename}", 3000)
        else:
            QMessageBox.warning(self, "Error", "Failed to add download. Please check the URL.")
    
    def get_selected_download_id(self) -> Optional[str]:
        """Get the ID of the currently selected download."""
        current_row = self.download_table.currentRow()
        if current_row >= 0:
            name_item = self.download_table.item(current_row, 0)
            if name_item:
                return name_item.data(Qt.UserRole)
        return None
    
    def handle_selected_action(self, action: str):
        """Handle action on selected download."""
        download_id = self.get_selected_download_id()
        if download_id:
            self.handle_download_action(download_id, action)
    
    @pyqtSlot(str, str)
    def handle_download_action(self, download_id: str, action: str):
        """Handle download actions."""
        success = False
        
        if action == "start":
            success = self.download_manager.start_download(download_id)
        elif action == "pause":
            success = self.download_manager.pause_download(download_id)
        elif action == "resume":
            success = self.download_manager.resume_download(download_id)
        elif action == "cancel":
            success = self.download_manager.cancel_download(download_id)
        elif action == "delete":
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                "Are you sure you want to delete this download?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                success = self.download_manager.delete_download(download_id)
                if success:
                    self.refresh_table()
        
        if not success and action != "delete":
            QMessageBox.warning(self, "Error", f"Failed to {action} download.")
    
    def refresh_table(self):
        """Refresh the entire download table."""
        self.download_table.setRowCount(0)
        self.load_downloads()
    
    def update_display(self):
        """Update the display with current download information."""
        # Update table rows
        for row in range(self.download_table.rowCount()):
            name_item = self.download_table.item(row, 0)
            if name_item:
                download_id = name_item.data(Qt.UserRole)
                task = self.download_manager.get_download(download_id)
                if task:
                    self.update_table_row(row, task)
        
        # Update status bar
        self.update_status_bar()
    
    def update_status_bar(self):
        """Update the status bar with download statistics."""
        stats = self.download_manager.get_statistics()
        active_count = stats.get('active_downloads', 0)
        total_count = stats.get('total_downloads', 0)
        
        status_text = f"Downloads: {total_count} total, {active_count} active"
        self.status_bar.showMessage(status_text)

    def on_progress_update(self, task: DownloadTask):
        """Handle progress updates from download manager."""
        # Find the row for this task and update it
        for row in range(self.download_table.rowCount()):
            name_item = self.download_table.item(row, 0)
            if name_item and name_item.data(Qt.UserRole) == task.id:
                self.update_table_row(row, task)
                break

    def on_status_change(self, task: DownloadTask):
        """Handle status changes from download manager."""
        # Update the table row
        self.on_progress_update(task)

        # Show notification for important status changes
        if task.status == DownloadStatus.COMPLETED:
            self.status_bar.showMessage(f"Download completed: {task.filename}", 5000)
        elif task.status == DownloadStatus.ERROR:
            self.status_bar.showMessage(f"Download failed: {task.filename}", 5000)

    def on_table_double_click(self, row: int, column: int):
        """Handle double-click on table."""
        name_item = self.download_table.item(row, 0)
        if name_item:
            download_id = name_item.data(Qt.UserRole)
            task = self.download_manager.get_download(download_id)

            if task and task.status == DownloadStatus.COMPLETED:
                # Open file location
                import os
                import subprocess
                import platform

                file_path = task.get_full_path()
                if os.path.exists(file_path):
                    system = platform.system()
                    if system == "Windows":
                        subprocess.run(["explorer", "/select,", file_path])
                    elif system == "Darwin":  # macOS
                        subprocess.run(["open", "-R", file_path])
                    else:  # Linux
                        subprocess.run(["xdg-open", os.path.dirname(file_path)])

    def on_tray_activated(self, reason):
        """Handle system tray activation."""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()

    def show_add_download_dialog(self):
        """Show add download dialog."""
        url, ok = QInputDialog.getText(
            self, "Add Download", "Enter URL:",
            text=QApplication.clipboard().text()
        )

        if ok and url.strip():
            self.add_download(url.strip())

    def show_settings_dialog(self):
        """Show settings dialog."""
        # This would open a settings dialog
        QMessageBox.information(self, "Settings", "Settings dialog not implemented yet.")

    def show_about_dialog(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About Download Manager",
            "Download Manager v1.0\n\n"
            "A multi-threaded download manager with browser integration.\n"
            "Features include download acceleration, pause/resume, "
            "video detection, and scheduling."
        )

    def start_all_downloads(self):
        """Start all pending/paused downloads."""
        count = 0
        for task in self.download_manager.get_all_downloads():
            if task.status in [DownloadStatus.PENDING, DownloadStatus.PAUSED]:
                if self.download_manager.start_download(task.id):
                    count += 1

        self.status_bar.showMessage(f"Started {count} downloads", 3000)

    def pause_all_downloads(self):
        """Pause all active downloads."""
        count = 0
        for task in self.download_manager.get_active_downloads():
            if self.download_manager.pause_download(task.id):
                count += 1

        self.status_bar.showMessage(f"Paused {count} downloads", 3000)

    def clear_completed_downloads(self):
        """Clear completed downloads from the list."""
        reply = QMessageBox.question(
            self, "Clear Completed",
            "Remove all completed downloads from the list?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            completed_tasks = self.download_manager.get_downloads_by_status(DownloadStatus.COMPLETED)
            count = 0

            for task in completed_tasks:
                if self.download_manager.delete_download(task.id):
                    count += 1

            self.refresh_table()
            self.status_bar.showMessage(f"Cleared {count} completed downloads", 3000)

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
            return ""
        return f"{self.format_bytes(bytes_per_second)}/s"

    def format_time(self, seconds: float) -> str:
        """Format time duration."""
        if seconds <= 0:
            return ""

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def closeEvent(self, event):
        """Handle window close event."""
        if settings.get('minimize_to_tray', True) and self.system_tray and self.system_tray.isVisible():
            self.hide()
            event.ignore()
        else:
            # Stop download manager
            self.download_manager.stop()
            event.accept()
