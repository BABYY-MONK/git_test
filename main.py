#!/usr/bin/env python3
"""
Download Manager Application
A multi-threaded download manager with browser integration and video detection.

Features:
- Multi-threaded downloading with pause/resume support
- Browser integration for URL capture
- Video detection and downloading
- Download scheduling
- System notifications
- File organization
- Persistent download tracking

Usage:
    python main.py [URL]
    
If a URL is provided as a command line argument, it will be added to the download queue.
This is useful for browser integration via protocol handlers.
"""

import sys
import os
import signal
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

from ui.main_window import MainWindow
from browser.url_capture import URLCapture
from config.settings import settings
from core.download_manager import DownloadManager


class DownloadManagerApp:
    """Main application class."""
    
    def __init__(self):
        self.app = None
        self.main_window = None
        self.url_capture = None
        self.download_manager = None
    
    def setup_application(self):
        """Setup the Qt application."""
        # Enable high DPI scaling
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        # Create application
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Download Manager")
        self.app.setApplicationVersion("1.0")
        self.app.setOrganizationName("Download Manager")
        
        # Set application icon
        icon_path = project_root / "assets" / "icon.png"
        if icon_path.exists():
            self.app.setWindowIcon(QIcon(str(icon_path)))
        
        # Handle system signals
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Setup timer to handle Unix signals
        self.timer = QTimer()
        self.timer.start(500)
        self.timer.timeout.connect(lambda: None)
    
    def setup_browser_integration(self):
        """Setup browser integration."""
        if settings.get('enable_browser_integration', True):
            try:
                self.url_capture = URLCapture(self.handle_captured_url)
                
                # Register protocol handler
                if self.url_capture.register_protocol_handler():
                    print("Protocol handler registered successfully")
                else:
                    print("Failed to register protocol handler")
                
                # Start URL monitoring
                if self.url_capture.start_monitoring():
                    print("URL monitoring started")
                else:
                    print("Failed to start URL monitoring")
                    
            except Exception as e:
                print(f"Browser integration setup failed: {e}")
    
    def handle_captured_url(self, url: str):
        """Handle URLs captured from browser."""
        if self.main_window:
            self.main_window.download_added.emit(url)
    
    def create_main_window(self):
        """Create and show the main window."""
        self.main_window = MainWindow()
        
        # Restore window geometry
        geometry = settings.get('window_geometry', {})
        if geometry:
            self.main_window.resize(geometry.get('width', 800), geometry.get('height', 600))
            self.main_window.move(geometry.get('x', 100), geometry.get('y', 100))
        
        self.main_window.show()
    
    def save_window_geometry(self):
        """Save window geometry to settings."""
        if self.main_window:
            geometry = self.main_window.geometry()
            settings.set('window_geometry', {
                'width': geometry.width(),
                'height': geometry.height(),
                'x': geometry.x(),
                'y': geometry.y()
            })
            settings.save_settings()
    
    def signal_handler(self, signum, frame):
        """Handle system signals."""
        print(f"Received signal {signum}, shutting down...")
        self.shutdown()
    
    def shutdown(self):
        """Shutdown the application."""
        print("Shutting down Download Manager...")
        
        # Save window geometry
        self.save_window_geometry()
        
        # Stop URL capture
        if self.url_capture:
            self.url_capture.stop_monitoring()
        
        # Stop download manager (this is handled by the main window)
        
        # Quit application
        if self.app:
            self.app.quit()
    
    def run(self, initial_url: str = None):
        """Run the application."""
        try:
            # Setup application
            self.setup_application()
            
            # Setup browser integration
            self.setup_browser_integration()
            
            # Create main window
            self.create_main_window()
            
            # Add initial URL if provided
            if initial_url:
                self.main_window.download_added.emit(initial_url)
            
            # Run application
            exit_code = self.app.exec_()
            
            # Cleanup
            self.shutdown()
            
            return exit_code
            
        except Exception as e:
            print(f"Application error: {e}")
            if self.app:
                QMessageBox.critical(None, "Application Error", f"An error occurred: {str(e)}")
            return 1


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Download Manager - Multi-threaded download manager with browser integration"
    )
    
    parser.add_argument(
        'url',
        nargs='?',
        help='URL to download (optional)'
    )
    
    parser.add_argument(
        '--no-gui',
        action='store_true',
        help='Run in command line mode (not implemented)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Download Manager 1.0'
    )
    
    parser.add_argument(
        '--register-protocol',
        action='store_true',
        help='Register protocol handler and exit'
    )
    
    parser.add_argument(
        '--unregister-protocol',
        action='store_true',
        help='Unregister protocol handler and exit'
    )
    
    return parser.parse_args()


def check_dependencies():
    """Check if required dependencies are available."""
    missing_deps = []
    
    try:
        import PyQt5
    except ImportError:
        missing_deps.append("PyQt5")
    
    try:
        import requests
    except ImportError:
        missing_deps.append("requests")
    
    if missing_deps:
        print("Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nPlease install missing dependencies:")
        print("pip install -r requirements.txt")
        return False
    
    return True


def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Handle protocol registration
    if args.register_protocol:
        url_capture = URLCapture()
        if url_capture.register_protocol_handler():
            print("Protocol handler registered successfully")
            return 0
        else:
            print("Failed to register protocol handler")
            return 1
    
    if args.unregister_protocol:
        url_capture = URLCapture()
        if url_capture.unregister_protocol_handler():
            print("Protocol handler unregistered successfully")
            return 0
        else:
            print("Failed to unregister protocol handler")
            return 1
    
    # Handle command line mode (not implemented)
    if args.no_gui:
        print("Command line mode not implemented yet")
        return 1
    
    # Create and run application
    app = DownloadManagerApp()
    return app.run(args.url)


if __name__ == "__main__":
    sys.exit(main())
