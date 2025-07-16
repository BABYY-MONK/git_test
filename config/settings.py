"""
Configuration management for the Download Manager application.
Handles application settings, user preferences, and default values.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


class Settings:
    """Manages application settings and user preferences."""
    
    def __init__(self):
        self.app_name = "DownloadManager"
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "settings.json"
        self.default_settings = self._get_default_settings()
        self.settings = self._load_settings()
    
    def _get_config_dir(self) -> Path:
        """Get the configuration directory based on the operating system."""
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get('APPDATA', '')) / self.app_name
        else:  # Linux/macOS
            config_dir = Path.home() / f'.{self.app_name.lower()}'
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Return default application settings."""
        return {
            "download_directory": str(Path.home() / "Downloads"),
            "max_concurrent_downloads": 3,
            "max_threads_per_download": 8,
            "chunk_size": 8192,
            "connection_timeout": 30,
            "retry_attempts": 3,
            "retry_delay": 5,
            "enable_notifications": True,
            "enable_browser_integration": True,
            "enable_video_detection": True,
            "bandwidth_limit": 0,  # 0 means no limit (in KB/s)
            "auto_start_downloads": True,
            "show_system_tray": True,
            "minimize_to_tray": True,
            "auto_organize_files": True,
            "file_categories": {
                "videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
                "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"],
                "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
                "documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt"],
                "archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
                "executables": [".exe", ".msi", ".deb", ".rpm", ".dmg", ".pkg"]
            },
            "ui_theme": "light",
            "window_geometry": {
                "width": 800,
                "height": 600,
                "x": 100,
                "y": 100
            }
        }
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file or return defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                settings = self.default_settings.copy()
                settings.update(loaded_settings)
                return settings
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading settings: {e}. Using defaults.")
        
        return self.default_settings.copy()
    
    def save_settings(self) -> bool:
        """Save current settings to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Error saving settings: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value."""
        self.settings[key] = value
    
    def get_download_directory(self) -> str:
        """Get the download directory, creating it if it doesn't exist."""
        download_dir = Path(self.get("download_directory"))
        download_dir.mkdir(parents=True, exist_ok=True)
        return str(download_dir)
    
    def get_category_directory(self, file_extension: str) -> str:
        """Get the directory for a specific file category."""
        if not self.get("auto_organize_files"):
            return self.get_download_directory()
        
        categories = self.get("file_categories", {})
        for category, extensions in categories.items():
            if file_extension.lower() in extensions:
                category_dir = Path(self.get_download_directory()) / category
                category_dir.mkdir(parents=True, exist_ok=True)
                return str(category_dir)
        
        return self.get_download_directory()
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        self.settings = self.default_settings.copy()


# Global settings instance
settings = Settings()
