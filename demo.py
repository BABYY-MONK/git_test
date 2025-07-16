#!/usr/bin/env python3
"""
Demo script for the Download Manager application.
Demonstrates core functionality without GUI.
"""

import sys
import time
import threading
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.download_manager import DownloadManager
from core.download_task import DownloadStatus

def progress_callback(task):
    """Callback for progress updates."""
    print(f"Progress: {task.filename} - {task.progress_percentage:.1f}% "
          f"({task.downloaded_bytes}/{task.file_size} bytes) "
          f"Speed: {task.download_speed:.0f} B/s")

def status_callback(task):
    """Callback for status changes."""
    print(f"Status: {task.filename} - {task.status.value}")

def demo_download_manager():
    """Demonstrate the download manager functionality."""
    print("Download Manager Demo")
    print("=" * 30)
    
    # Create download manager
    dm = DownloadManager()
    dm.add_progress_callback(progress_callback)
    dm.add_status_callback(status_callback)
    
    print("✓ Download Manager initialized")
    
    # Add some test downloads
    test_urls = [
        "https://httpbin.org/bytes/1024",  # Small test file
        "https://httpbin.org/bytes/2048",  # Another small test file
    ]
    
    tasks = []
    for i, url in enumerate(test_urls):
        task = dm.add_download(url, f"test_file_{i+1}.bin")
        if task:
            tasks.append(task)
            print(f"✓ Added download: {task.filename}")
        else:
            print(f"✗ Failed to add download: {url}")
    
    if not tasks:
        print("No downloads to process")
        return
    
    # Wait for downloads to complete
    print("\nWaiting for downloads to complete...")
    max_wait = 30  # Maximum wait time in seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        all_completed = True
        for task in tasks:
            current_task = dm.get_download(task.id)
            if current_task and current_task.status not in [
                DownloadStatus.COMPLETED, 
                DownloadStatus.ERROR, 
                DownloadStatus.CANCELLED
            ]:
                all_completed = False
                break
        
        if all_completed:
            break
        
        time.sleep(1)
    
    # Show final status
    print("\nFinal Status:")
    print("-" * 20)
    for task in tasks:
        current_task = dm.get_download(task.id)
        if current_task:
            print(f"{current_task.filename}: {current_task.status.value} "
                  f"({current_task.progress_percentage:.1f}%)")
    
    # Show statistics
    stats = dm.get_statistics()
    print(f"\nStatistics:")
    print(f"Total downloads: {stats.get('total_downloads', 0)}")
    print(f"Active downloads: {stats.get('active_downloads', 0)}")
    print(f"Total downloaded: {stats.get('total_downloaded_bytes', 0)} bytes")
    
    # Stop the download manager
    dm.stop()
    print("\n✓ Download Manager stopped")

def demo_video_detection():
    """Demonstrate video detection functionality."""
    print("\nVideo Detection Demo")
    print("=" * 30)
    
    from video.video_detector import VideoDetector
    
    detector = VideoDetector()
    
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://vimeo.com/123456789",
        "https://example.com/video.mp4",
        "https://example.com/document.pdf",
    ]
    
    for url in test_urls:
        video_info = detector.detect_video(url)
        if video_info:
            print(f"✓ Video detected: {url}")
            print(f"  Platform: {video_info.get('platform', 'unknown')}")
            print(f"  Title: {video_info.get('title', 'unknown')}")
        else:
            print(f"✗ No video detected: {url}")

def demo_file_organization():
    """Demonstrate file organization functionality."""
    print("\nFile Organization Demo")
    print("=" * 30)
    
    from config.settings import settings
    
    test_files = [
        "video.mp4",
        "audio.mp3",
        "document.pdf",
        "archive.zip",
        "image.jpg",
        "unknown.xyz"
    ]
    
    for filename in test_files:
        category_dir = settings.get_category_directory(Path(filename).suffix)
        print(f"{filename} -> {category_dir}")

def main():
    """Run all demos."""
    try:
        demo_download_manager()
        demo_video_detection()
        demo_file_organization()
        
        print("\n" + "=" * 50)
        print("✓ Demo completed successfully!")
        print("\nTo run the full GUI application, use:")
        print("  python main.py")
        print("\nOr use the launcher:")
        print("  python run.py")
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
