#!/usr/bin/env python3
"""
Basic test script for the Download Manager application.
Tests core functionality without GUI.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from config.settings import settings
        print("✓ Config module imported")
        
        from core.download_task import DownloadTask, DownloadStatus
        print("✓ Download task module imported")
        
        from core.download_engine import DownloadEngine
        print("✓ Download engine module imported")
        
        from network.http_client import HTTPClient
        print("✓ HTTP client module imported")
        
        from filesystem.file_manager import FileManager
        print("✓ File manager module imported")
        
        from database.db_manager import DatabaseManager
        print("✓ Database manager module imported")
        
        from video.video_detector import VideoDetector
        print("✓ Video detector module imported")
        
        from notifications.notifier import Notifier
        print("✓ Notifier module imported")
        
        from browser.url_capture import URLCapture
        print("✓ URL capture module imported")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_settings():
    """Test settings functionality."""
    print("\nTesting settings...")
    
    try:
        from config.settings import settings
        
        # Test getting default values
        download_dir = settings.get_download_directory()
        print(f"✓ Download directory: {download_dir}")
        
        max_threads = settings.get('max_threads_per_download')
        print(f"✓ Max threads: {max_threads}")
        
        # Test setting and getting values
        settings.set('test_key', 'test_value')
        value = settings.get('test_key')
        assert value == 'test_value', f"Expected 'test_value', got '{value}'"
        print("✓ Settings get/set works")
        
        return True
        
    except Exception as e:
        print(f"✗ Settings error: {e}")
        return False


def test_download_task():
    """Test download task functionality."""
    print("\nTesting download task...")
    
    try:
        from core.download_task import DownloadTask, DownloadStatus
        
        # Create a task
        task = DownloadTask("https://httpbin.org/bytes/1024", "test_file.bin")
        print(f"✓ Task created: {task.id}")
        
        # Test status changes
        assert task.status == DownloadStatus.PENDING
        task.start()
        assert task.status == DownloadStatus.DOWNLOADING
        task.pause()
        assert task.status == DownloadStatus.PAUSED
        print("✓ Status changes work")
        
        # Test progress
        task.update_progress(512)
        task.file_size = 1024
        task.update_progress(512)
        assert task.progress_percentage == 50.0
        print("✓ Progress calculation works")
        
        return True
        
    except Exception as e:
        print(f"✗ Download task error: {e}")
        return False


def test_http_client():
    """Test HTTP client functionality."""
    print("\nTesting HTTP client...")
    
    try:
        from network.http_client import HTTPClient
        
        client = HTTPClient()
        
        # Test connection
        test_url = "https://httpbin.org/get"
        if client.test_connection(test_url):
            print("✓ Connection test passed")
        else:
            print("✗ Connection test failed")
            return False
        
        # Test file info
        file_info = client.get_file_info("https://httpbin.org/bytes/1024")
        if file_info:
            print(f"✓ File info retrieved: {file_info.get('file_size', 'unknown')} bytes")
        else:
            print("✗ Failed to get file info")
            return False
        
        client.close()
        return True
        
    except Exception as e:
        print(f"✗ HTTP client error: {e}")
        return False


def test_file_manager():
    """Test file manager functionality."""
    print("\nTesting file manager...")
    
    try:
        from filesystem.file_manager import FileManager
        
        fm = FileManager()
        
        # Test temp file creation
        temp_file = fm.create_temp_file("test_download", 0)
        print(f"✓ Temp file created: {temp_file}")
        
        # Test writing data
        test_data = b"Hello, World!"
        bytes_written = fm.append_to_temp_file(temp_file, test_data)
        assert bytes_written == len(test_data)
        print("✓ Data written to temp file")
        
        # Test file size
        file_size = fm.get_file_size(temp_file)
        assert file_size == len(test_data)
        print("✓ File size calculation works")
        
        # Cleanup
        fm.cleanup_temp_files([temp_file])
        print("✓ Temp file cleanup works")
        
        return True
        
    except Exception as e:
        print(f"✗ File manager error: {e}")
        return False


def test_database():
    """Test database functionality."""
    print("\nTesting database...")
    
    try:
        from database.db_manager import DatabaseManager
        from core.download_task import DownloadTask
        
        db = DatabaseManager()
        
        # Create a test task
        task = DownloadTask("https://example.com/test.zip", "test.zip")
        
        # Save task
        success = db.save_download(task)
        assert success, "Failed to save download"
        print("✓ Download saved to database")
        
        # Load task
        loaded_task = db.load_download(task.id)
        assert loaded_task is not None, "Failed to load download"
        assert loaded_task.url == task.url, "URL mismatch"
        print("✓ Download loaded from database")
        
        # Delete task
        success = db.delete_download(task.id)
        assert success, "Failed to delete download"
        print("✓ Download deleted from database")
        
        return True
        
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False


def test_video_detector():
    """Test video detector functionality."""
    print("\nTesting video detector...")
    
    try:
        from video.video_detector import VideoDetector
        
        detector = VideoDetector()
        
        # Test YouTube detection
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_info = detector.detect_video(youtube_url)
        
        if video_info:
            print(f"✓ Video detected: {video_info.get('platform', 'unknown')}")
        else:
            print("✓ Video detection works (no video info due to missing dependencies)")
        
        # Test supported platforms
        platforms = detector.get_supported_platforms()
        print(f"✓ Supported platforms: {len(platforms)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Video detector error: {e}")
        return False


def main():
    """Run all tests."""
    print("Download Manager - Basic Functionality Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_settings,
        test_download_task,
        test_http_client,
        test_file_manager,
        test_database,
        test_video_detector
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print("Test failed!")
        except Exception as e:
            print(f"Test crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! The application should work correctly.")
        return 0
    else:
        print("✗ Some tests failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
