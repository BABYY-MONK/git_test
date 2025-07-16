"""
Notification System for the Download Manager application.
Handles system notifications and alerts for download events.
"""

import os
import platform
from typing import Optional
from pathlib import Path

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

from core.download_task import DownloadTask
from config.settings import settings


class Notifier:
    """Handles system notifications for download events."""
    
    def __init__(self):
        self.app_name = "Download Manager"
        self.app_icon = self._get_app_icon()
        self.notifications_enabled = settings.get('enable_notifications', True)
    
    def _get_app_icon(self) -> Optional[str]:
        """Get the application icon path."""
        try:
            # Look for icon in common locations
            possible_paths = [
                Path(__file__).parent.parent / "assets" / "icon.ico",
                Path(__file__).parent.parent / "assets" / "icon.png",
                Path(__file__).parent.parent / "icon.ico",
                Path(__file__).parent.parent / "icon.png"
            ]
            
            for path in possible_paths:
                if path.exists():
                    return str(path)
            
        except Exception:
            pass
        
        return None
    
    def notify_download_completed(self, task: DownloadTask) -> None:
        """Notify when a download is completed."""
        if not self.notifications_enabled:
            return
        
        title = "Download Completed"
        message = f"'{task.filename}' has been downloaded successfully."
        
        self._send_notification(title, message, timeout=10)
    
    def notify_download_failed(self, task: DownloadTask) -> None:
        """Notify when a download fails."""
        if not self.notifications_enabled:
            return
        
        title = "Download Failed"
        message = f"'{task.filename}' failed to download."
        if task.error_message:
            message += f"\nError: {task.error_message}"
        
        self._send_notification(title, message, timeout=10)
    
    def notify_download_started(self, task: DownloadTask) -> None:
        """Notify when a download starts."""
        if not self.notifications_enabled:
            return
        
        title = "Download Started"
        message = f"Started downloading '{task.filename}'"
        
        self._send_notification(title, message, timeout=5)
    
    def notify_download_paused(self, task: DownloadTask) -> None:
        """Notify when a download is paused."""
        if not self.notifications_enabled:
            return
        
        title = "Download Paused"
        message = f"'{task.filename}' has been paused."
        
        self._send_notification(title, message, timeout=5)
    
    def notify_download_resumed(self, task: DownloadTask) -> None:
        """Notify when a download is resumed."""
        if not self.notifications_enabled:
            return
        
        title = "Download Resumed"
        message = f"'{task.filename}' has been resumed."
        
        self._send_notification(title, message, timeout=5)
    
    def notify_all_downloads_completed(self, count: int) -> None:
        """Notify when all downloads are completed."""
        if not self.notifications_enabled:
            return
        
        title = "All Downloads Completed"
        message = f"All {count} downloads have been completed successfully."
        
        self._send_notification(title, message, timeout=10)
    
    def notify_disk_space_low(self, available_space: int, required_space: int) -> None:
        """Notify when disk space is low."""
        if not self.notifications_enabled:
            return
        
        title = "Low Disk Space"
        message = f"Insufficient disk space for download.\nAvailable: {self._format_bytes(available_space)}\nRequired: {self._format_bytes(required_space)}"
        
        self._send_notification(title, message, timeout=15)
    
    def notify_scheduled_download(self, task: DownloadTask) -> None:
        """Notify when a scheduled download starts."""
        if not self.notifications_enabled:
            return
        
        title = "Scheduled Download Started"
        message = f"Scheduled download '{task.filename}' has started."
        
        self._send_notification(title, message, timeout=5)
    
    def _send_notification(self, title: str, message: str, timeout: int = 10) -> None:
        """Send a system notification."""
        try:
            if PLYER_AVAILABLE:
                self._send_plyer_notification(title, message, timeout)
            else:
                self._send_fallback_notification(title, message)
                
        except Exception as e:
            print(f"Failed to send notification: {e}")
            # Fallback to console output
            print(f"NOTIFICATION: {title} - {message}")
    
    def _send_plyer_notification(self, title: str, message: str, timeout: int) -> None:
        """Send notification using plyer."""
        notification.notify(
            title=title,
            message=message,
            app_name=self.app_name,
            app_icon=self.app_icon,
            timeout=timeout
        )
    
    def _send_fallback_notification(self, title: str, message: str) -> None:
        """Send notification using platform-specific methods."""
        system = platform.system().lower()
        
        if system == "windows":
            self._send_windows_notification(title, message)
        elif system == "darwin":  # macOS
            self._send_macos_notification(title, message)
        elif system == "linux":
            self._send_linux_notification(title, message)
        else:
            print(f"NOTIFICATION: {title} - {message}")
    
    def _send_windows_notification(self, title: str, message: str) -> None:
        """Send Windows toast notification."""
        try:
            import win10toast
            toaster = win10toast.ToastNotifier()
            toaster.show_toast(
                title,
                message,
                icon_path=self.app_icon,
                duration=10,
                threaded=True
            )
        except ImportError:
            # Fallback to Windows balloon tip
            try:
                import win32gui
                import win32con
                
                # This is a simplified approach - in a real app you'd want a proper system tray
                print(f"WINDOWS NOTIFICATION: {title} - {message}")
            except ImportError:
                print(f"NOTIFICATION: {title} - {message}")
    
    def _send_macos_notification(self, title: str, message: str) -> None:
        """Send macOS notification."""
        try:
            os.system(f'''
                osascript -e 'display notification "{message}" with title "{title}" sound name "default"'
            ''')
        except Exception:
            print(f"NOTIFICATION: {title} - {message}")
    
    def _send_linux_notification(self, title: str, message: str) -> None:
        """Send Linux notification using notify-send."""
        try:
            icon_arg = f"--icon={self.app_icon}" if self.app_icon else ""
            os.system(f'notify-send {icon_arg} "{title}" "{message}"')
        except Exception:
            print(f"NOTIFICATION: {title} - {message}")
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def enable_notifications(self) -> None:
        """Enable notifications."""
        self.notifications_enabled = True
        settings.set('enable_notifications', True)
        settings.save_settings()
    
    def disable_notifications(self) -> None:
        """Disable notifications."""
        self.notifications_enabled = False
        settings.set('enable_notifications', False)
        settings.save_settings()
    
    def is_notifications_enabled(self) -> bool:
        """Check if notifications are enabled."""
        return self.notifications_enabled
    
    def test_notification(self) -> None:
        """Send a test notification."""
        title = "Download Manager"
        message = "Notifications are working correctly!"
        self._send_notification(title, message, timeout=5)
