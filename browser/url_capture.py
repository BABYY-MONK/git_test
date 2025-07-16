"""
Browser Integration module for the Download Manager application.
Handles URL capture from web browsers and protocol registration.
"""

import os
import sys
import json
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from urllib.parse import unquote
import platform

from config.settings import settings


class URLCapture:
    """Handles browser integration and URL capture."""
    
    def __init__(self, url_callback: Optional[Callable[[str], None]] = None):
        self.url_callback = url_callback
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.protocol_name = "downloadmanager"
        
        # Browser extension communication
        self.native_messaging_host = "com.downloadmanager.native"
        self.temp_dir = Path(tempfile.gettempdir()) / "DownloadManager"
        self.temp_dir.mkdir(exist_ok=True)
        
        # URL patterns to capture
        self.capture_patterns = [
            r'\.zip$', r'\.rar$', r'\.7z$', r'\.tar\.gz$',  # Archives
            r'\.exe$', r'\.msi$', r'\.dmg$', r'\.pkg$',     # Executables
            r'\.mp4$', r'\.avi$', r'\.mkv$', r'\.mov$',     # Videos
            r'\.mp3$', r'\.wav$', r'\.flac$',               # Audio
            r'\.pdf$', r'\.doc$', r'\.docx$',               # Documents
            r'\.iso$', r'\.img$'                            # Disk images
        ]
    
    def start_monitoring(self) -> bool:
        """Start monitoring for browser URLs."""
        if self.is_monitoring:
            return True
        
        try:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True
            )
            self.monitor_thread.start()
            return True
            
        except Exception as e:
            print(f"Failed to start URL monitoring: {e}")
            self.is_monitoring = False
            return False
    
    def stop_monitoring(self) -> None:
        """Stop monitoring for browser URLs."""
        self.is_monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
    
    def register_protocol_handler(self) -> bool:
        """Register custom protocol handler for browser integration."""
        try:
            system = platform.system().lower()
            
            if system == "windows":
                return self._register_windows_protocol()
            elif system == "darwin":  # macOS
                return self._register_macos_protocol()
            elif system == "linux":
                return self._register_linux_protocol()
            
        except Exception as e:
            print(f"Failed to register protocol handler: {e}")
        
        return False
    
    def unregister_protocol_handler(self) -> bool:
        """Unregister custom protocol handler."""
        try:
            system = platform.system().lower()
            
            if system == "windows":
                return self._unregister_windows_protocol()
            elif system == "darwin":  # macOS
                return self._unregister_macos_protocol()
            elif system == "linux":
                return self._unregister_linux_protocol()
            
        except Exception as e:
            print(f"Failed to unregister protocol handler: {e}")
        
        return False
    
    def install_browser_extension(self, browser: str) -> bool:
        """Install native messaging host for browser extension."""
        try:
            if browser.lower() == "chrome":
                return self._install_chrome_extension()
            elif browser.lower() == "firefox":
                return self._install_firefox_extension()
            
        except Exception as e:
            print(f"Failed to install browser extension for {browser}: {e}")
        
        return False
    
    def handle_protocol_url(self, url: str) -> None:
        """Handle URLs received through protocol handler."""
        try:
            # Remove protocol prefix
            if url.startswith(f"{self.protocol_name}://"):
                actual_url = url[len(f"{self.protocol_name}://"):]
                actual_url = unquote(actual_url)
                
                if self.url_callback:
                    self.url_callback(actual_url)
                    
        except Exception as e:
            print(f"Error handling protocol URL: {e}")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop for URL capture."""
        while self.is_monitoring:
            try:
                # Check for URLs from browser extensions
                self._check_extension_messages()
                
                # Check for protocol handler URLs
                self._check_protocol_urls()
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                print(f"Error in URL monitoring loop: {e}")
                time.sleep(5)
    
    def _check_extension_messages(self) -> None:
        """Check for messages from browser extensions."""
        try:
            message_file = self.temp_dir / "extension_messages.json"
            
            if message_file.exists():
                with open(message_file, 'r') as f:
                    messages = json.load(f)
                
                for message in messages:
                    if message.get('type') == 'download_url':
                        url = message.get('url')
                        if url and self.url_callback:
                            self.url_callback(url)
                
                # Clear processed messages
                message_file.unlink()
                
        except Exception as e:
            print(f"Error checking extension messages: {e}")
    
    def _check_protocol_urls(self) -> None:
        """Check for URLs from protocol handler."""
        try:
            protocol_file = self.temp_dir / "protocol_urls.txt"
            
            if protocol_file.exists():
                with open(protocol_file, 'r') as f:
                    urls = f.read().strip().split('\n')
                
                for url in urls:
                    if url.strip():
                        self.handle_protocol_url(url.strip())
                
                # Clear processed URLs
                protocol_file.unlink()
                
        except Exception as e:
            print(f"Error checking protocol URLs: {e}")
    
    def _register_windows_protocol(self) -> bool:
        """Register protocol handler on Windows."""
        try:
            import winreg
            
            # Get current executable path
            exe_path = sys.executable
            if hasattr(sys, 'frozen'):
                exe_path = sys.executable
            else:
                exe_path = f'"{sys.executable}" "{__file__}"'
            
            # Create registry entries
            key_path = f"SOFTWARE\\Classes\\{self.protocol_name}"
            
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:Download Manager Protocol")
                winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{key_path}\\shell\\open\\command") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'{exe_path} "%1"')
            
            return True
            
        except Exception as e:
            print(f"Windows protocol registration error: {e}")
            return False
    
    def _register_macos_protocol(self) -> bool:
        """Register protocol handler on macOS."""
        try:
            # Create a simple app bundle for protocol handling
            app_name = "DownloadManager"
            app_path = Path.home() / "Applications" / f"{app_name}.app"
            
            # This is a simplified approach - in practice you'd want a proper app bundle
            print(f"macOS protocol registration not fully implemented")
            return False
            
        except Exception as e:
            print(f"macOS protocol registration error: {e}")
            return False
    
    def _register_linux_protocol(self) -> bool:
        """Register protocol handler on Linux."""
        try:
            # Create .desktop file
            desktop_content = f"""[Desktop Entry]
Name=Download Manager
Exec=python3 {__file__} %u
Type=Application
NoDisplay=true
StartupNotify=true
MimeType=x-scheme-handler/{self.protocol_name};
"""
            
            desktop_file = Path.home() / ".local/share/applications/downloadmanager.desktop"
            desktop_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(desktop_file, 'w') as f:
                f.write(desktop_content)
            
            # Update MIME database
            os.system("update-desktop-database ~/.local/share/applications/")
            
            return True
            
        except Exception as e:
            print(f"Linux protocol registration error: {e}")
            return False
    
    def _unregister_windows_protocol(self) -> bool:
        """Unregister protocol handler on Windows."""
        try:
            import winreg
            
            key_path = f"SOFTWARE\\Classes\\{self.protocol_name}"
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
            return True
            
        except Exception as e:
            print(f"Windows protocol unregistration error: {e}")
            return False
    
    def _unregister_macos_protocol(self) -> bool:
        """Unregister protocol handler on macOS."""
        # Implementation would depend on how the protocol was registered
        return False
    
    def _unregister_linux_protocol(self) -> bool:
        """Unregister protocol handler on Linux."""
        try:
            desktop_file = Path.home() / ".local/share/applications/downloadmanager.desktop"
            if desktop_file.exists():
                desktop_file.unlink()
            
            os.system("update-desktop-database ~/.local/share/applications/")
            return True
            
        except Exception as e:
            print(f"Linux protocol unregistration error: {e}")
            return False
    
    def _install_chrome_extension(self) -> bool:
        """Install native messaging host for Chrome extension."""
        try:
            # Create native messaging host manifest
            manifest = {
                "name": self.native_messaging_host,
                "description": "Download Manager Native Host",
                "path": sys.executable,
                "type": "stdio",
                "allowed_origins": [
                    "chrome-extension://downloadmanager/"
                ]
            }
            
            # Determine manifest location based on OS
            system = platform.system().lower()
            
            if system == "windows":
                manifest_dir = Path.home() / "AppData/Local/Google/Chrome/User Data/NativeMessagingHosts"
            elif system == "darwin":
                manifest_dir = Path.home() / "Library/Application Support/Google/Chrome/NativeMessagingHosts"
            else:  # Linux
                manifest_dir = Path.home() / ".config/google-chrome/NativeMessagingHosts"
            
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest_file = manifest_dir / f"{self.native_messaging_host}.json"
            
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Chrome extension installation error: {e}")
            return False
    
    def _install_firefox_extension(self) -> bool:
        """Install native messaging host for Firefox extension."""
        try:
            # Similar to Chrome but for Firefox
            manifest = {
                "name": self.native_messaging_host,
                "description": "Download Manager Native Host",
                "path": sys.executable,
                "type": "stdio",
                "allowed_extensions": [
                    "downloadmanager@example.com"
                ]
            }
            
            # Firefox manifest location
            system = platform.system().lower()
            
            if system == "windows":
                manifest_dir = Path.home() / "AppData/Roaming/Mozilla/NativeMessagingHosts"
            elif system == "darwin":
                manifest_dir = Path.home() / "Library/Application Support/Mozilla/NativeMessagingHosts"
            else:  # Linux
                manifest_dir = Path.home() / ".mozilla/native-messaging-hosts"
            
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest_file = manifest_dir / f"{self.native_messaging_host}.json"
            
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Firefox extension installation error: {e}")
            return False


# Command line handler for protocol URLs
if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        
        # Write URL to temp file for main application to pick up
        temp_dir = Path(tempfile.gettempdir()) / "DownloadManager"
        temp_dir.mkdir(exist_ok=True)
        
        protocol_file = temp_dir / "protocol_urls.txt"
        with open(protocol_file, 'a') as f:
            f.write(f"{url}\n")
