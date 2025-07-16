"""
Main Download Manager for the Download Manager application.
Orchestrates all download operations and manages the download queue.
"""

import threading
import time
from typing import List, Optional, Callable, Dict, Any
from queue import Queue, PriorityQueue
from dataclasses import dataclass
import validators

from core.download_task import DownloadTask, DownloadStatus
from core.download_engine import DownloadEngine
from core.scheduler import DownloadScheduler
from database.db_manager import DatabaseManager
from video.video_detector import VideoDetector
from notifications.notifier import Notifier
from config.settings import settings


@dataclass
class QueuedDownload:
    """Represents a queued download with priority."""
    priority: int
    task: DownloadTask
    
    def __lt__(self, other):
        return self.priority > other.priority  # Higher priority first


class DownloadManager:
    """Main download manager that orchestrates all download operations."""
    
    def __init__(self):
        # Core components
        self.db_manager = DatabaseManager()
        self.download_engine = DownloadEngine(
            progress_callback=self._on_progress_update,
            status_callback=self._on_status_change
        )
        self.scheduler = DownloadScheduler(self._start_scheduled_download)
        self.video_detector = VideoDetector()
        self.notifier = Notifier()
        
        # Download management
        self.download_queue = PriorityQueue()
        self.active_downloads: Dict[str, DownloadTask] = {}
        self.all_downloads: Dict[str, DownloadTask] = {}
        
        # Threading
        self.queue_processor_thread = None
        self.is_running = False
        self.lock = threading.Lock()
        
        # Callbacks
        self.progress_callbacks: List[Callable] = []
        self.status_callbacks: List[Callable] = []
        
        # Load existing downloads
        self._load_downloads()
        
        # Start queue processor
        self.start()
    
    def start(self) -> None:
        """Start the download manager."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start queue processor
        self.queue_processor_thread = threading.Thread(
            target=self._process_queue,
            daemon=True
        )
        self.queue_processor_thread.start()
        
        # Start scheduler
        self.scheduler.start()
    
    def stop(self) -> None:
        """Stop the download manager."""
        self.is_running = False
        
        # Stop scheduler
        self.scheduler.stop()
        
        # Pause all active downloads
        for task in list(self.active_downloads.values()):
            self.pause_download(task.id)
        
        # Shutdown download engine
        self.download_engine.shutdown()
        
        # Wait for queue processor to finish
        if self.queue_processor_thread and self.queue_processor_thread.is_alive():
            self.queue_processor_thread.join(timeout=5.0)
    
    def add_download(self, url: str, filename: Optional[str] = None,
                    destination: Optional[str] = None, 
                    scheduled_time: Optional[float] = None,
                    priority: int = 0) -> Optional[DownloadTask]:
        """Add a new download task."""
        try:
            # Validate URL
            if not validators.url(url):
                raise ValueError("Invalid URL")
            
            # Check for duplicates
            if self._is_duplicate_url(url):
                raise ValueError("URL already exists in downloads")
            
            # Create download task
            task = DownloadTask(url, filename, destination)
            task.scheduled_time = scheduled_time
            task.priority = priority
            
            # Detect if it's a video
            if settings.get('enable_video_detection', True):
                video_info = self.video_detector.detect_video(url)
                if video_info:
                    task.is_video = True
                    task.video_quality = video_info.get('quality')
                    # Update URL if video detector provides a direct link
                    if video_info.get('direct_url'):
                        task.url = video_info['direct_url']
            
            # Set destination if not provided
            if not task.destination:
                task.destination = settings.get_download_directory()
            
            # Save to database
            self.db_manager.save_download(task)
            
            # Add to internal tracking
            with self.lock:
                self.all_downloads[task.id] = task
            
            # Schedule or queue the download
            if scheduled_time and scheduled_time > time.time():
                self.scheduler.schedule_download(task)
                task.status = DownloadStatus.QUEUED
            else:
                self._queue_download(task)
            
            # Notify callbacks
            self._notify_status_callbacks(task)
            
            return task
            
        except Exception as e:
            print(f"Error adding download: {e}")
            return None
    
    def start_download(self, download_id: str) -> bool:
        """Start a specific download."""
        task = self.get_download(download_id)
        if not task:
            return False
        
        if task.status in [DownloadStatus.PENDING, DownloadStatus.PAUSED]:
            self._queue_download(task)
            return True
        
        return False
    
    def pause_download(self, download_id: str) -> bool:
        """Pause a download."""
        task = self.get_download(download_id)
        if not task:
            return False
        
        if task.status == DownloadStatus.DOWNLOADING:
            success = self.download_engine.pause_download(task)
            if success:
                with self.lock:
                    if download_id in self.active_downloads:
                        del self.active_downloads[download_id]
                self.db_manager.save_download(task)
            return success
        
        return False
    
    def resume_download(self, download_id: str) -> bool:
        """Resume a paused download."""
        task = self.get_download(download_id)
        if not task:
            return False
        
        if task.status == DownloadStatus.PAUSED:
            self._queue_download(task)
            return True
        
        return False
    
    def cancel_download(self, download_id: str) -> bool:
        """Cancel a download."""
        task = self.get_download(download_id)
        if not task:
            return False
        
        # Cancel if active
        if task.status == DownloadStatus.DOWNLOADING:
            self.download_engine.cancel_download(task)
        
        # Remove from queue if queued
        task.cancel()
        
        # Update database
        self.db_manager.save_download(task)
        
        # Remove from active downloads
        with self.lock:
            if download_id in self.active_downloads:
                del self.active_downloads[download_id]
        
        # Notify callbacks
        self._notify_status_callbacks(task)
        
        return True
    
    def delete_download(self, download_id: str) -> bool:
        """Delete a download from the manager."""
        # Cancel first if active
        self.cancel_download(download_id)
        
        # Remove from database
        success = self.db_manager.delete_download(download_id)
        
        # Remove from internal tracking
        with self.lock:
            if download_id in self.all_downloads:
                del self.all_downloads[download_id]
        
        return success
    
    def retry_download(self, download_id: str) -> bool:
        """Retry a failed download."""
        task = self.get_download(download_id)
        if not task:
            return False
        
        if task.status == DownloadStatus.ERROR and task.can_retry():
            task.retry()
            self.db_manager.save_download(task)
            self._queue_download(task)
            return True
        
        return False
    
    def get_download(self, download_id: str) -> Optional[DownloadTask]:
        """Get a download task by ID."""
        with self.lock:
            return self.all_downloads.get(download_id)
    
    def get_all_downloads(self) -> List[DownloadTask]:
        """Get all download tasks."""
        with self.lock:
            return list(self.all_downloads.values())
    
    def get_downloads_by_status(self, status: DownloadStatus) -> List[DownloadTask]:
        """Get downloads by status."""
        with self.lock:
            return [task for task in self.all_downloads.values() 
                   if task.status == status]
    
    def get_active_downloads(self) -> List[DownloadTask]:
        """Get currently active downloads."""
        with self.lock:
            return list(self.active_downloads.values())
    
    def add_progress_callback(self, callback: Callable) -> None:
        """Add a progress update callback."""
        self.progress_callbacks.append(callback)
    
    def add_status_callback(self, callback: Callable) -> None:
        """Add a status change callback."""
        self.status_callbacks.append(callback)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get download statistics."""
        db_stats = self.db_manager.get_download_statistics()
        
        with self.lock:
            active_count = len(self.active_downloads)
            queued_count = self.download_queue.qsize()
        
        return {
            **db_stats,
            'active_downloads': active_count,
            'queued_downloads': queued_count
        }

    def _load_downloads(self) -> None:
        """Load existing downloads from database."""
        downloads = self.db_manager.load_all_downloads()

        with self.lock:
            for task in downloads:
                self.all_downloads[task.id] = task

                # Resume incomplete downloads
                if task.status == DownloadStatus.DOWNLOADING:
                    task.status = DownloadStatus.PAUSED
                    self.db_manager.save_download(task)

                # Schedule future downloads
                if task.is_scheduled():
                    self.scheduler.schedule_download(task)

    def _is_duplicate_url(self, url: str) -> bool:
        """Check if URL already exists in downloads."""
        with self.lock:
            return any(task.url == url for task in self.all_downloads.values()
                      if task.status not in [DownloadStatus.COMPLETED, DownloadStatus.CANCELLED])

    def _queue_download(self, task: DownloadTask) -> None:
        """Add a download to the queue."""
        queued_download = QueuedDownload(task.priority, task)
        self.download_queue.put(queued_download)
        task.status = DownloadStatus.QUEUED
        self.db_manager.save_download(task)
        self._notify_status_callbacks(task)

    def _process_queue(self) -> None:
        """Process the download queue."""
        while self.is_running:
            try:
                # Check if we can start more downloads
                max_concurrent = settings.get('max_concurrent_downloads', 3)

                with self.lock:
                    active_count = len(self.active_downloads)

                if active_count >= max_concurrent:
                    time.sleep(1)
                    continue

                # Get next download from queue
                try:
                    queued_download = self.download_queue.get(timeout=1.0)
                    task = queued_download.task

                    # Start the download
                    if self._start_download_internal(task):
                        with self.lock:
                            self.active_downloads[task.id] = task

                    self.download_queue.task_done()

                except:
                    continue  # Timeout or empty queue

            except Exception as e:
                print(f"Error processing download queue: {e}")
                time.sleep(1)

    def _start_download_internal(self, task: DownloadTask) -> bool:
        """Internal method to start a download."""
        try:
            success = self.download_engine.start_download(task)
            if success:
                self.db_manager.save_download(task)
            return success
        except Exception as e:
            task.error(f"Failed to start download: {str(e)}")
            self.db_manager.save_download(task)
            return False

    def _start_scheduled_download(self, task: DownloadTask) -> None:
        """Callback for starting scheduled downloads."""
        self._queue_download(task)

    def _on_progress_update(self, task: DownloadTask) -> None:
        """Handle progress updates from download engine."""
        # Update database periodically
        current_time = time.time()
        if not hasattr(task, '_last_db_update'):
            task._last_db_update = 0

        if current_time - task._last_db_update > 5.0:  # Update every 5 seconds
            self.db_manager.update_download_progress(
                task.id, task.downloaded_bytes, task.progress_percentage,
                task.download_speed, task.eta
            )
            task._last_db_update = current_time

        # Notify progress callbacks
        self._notify_progress_callbacks(task)

    def _on_status_change(self, task: DownloadTask) -> None:
        """Handle status changes from download engine."""
        # Update database
        self.db_manager.save_download(task)

        # Remove from active downloads if completed/cancelled/error
        if task.status in [DownloadStatus.COMPLETED, DownloadStatus.CANCELLED, DownloadStatus.ERROR]:
            with self.lock:
                if task.id in self.active_downloads:
                    del self.active_downloads[task.id]

            # Send notification
            if task.status == DownloadStatus.COMPLETED:
                self.notifier.notify_download_completed(task)
            elif task.status == DownloadStatus.ERROR:
                self.notifier.notify_download_failed(task)

        # Notify status callbacks
        self._notify_status_callbacks(task)

    def _notify_progress_callbacks(self, task: DownloadTask) -> None:
        """Notify all progress callbacks."""
        for callback in self.progress_callbacks:
            try:
                callback(task)
            except Exception as e:
                print(f"Error in progress callback: {e}")

    def _notify_status_callbacks(self, task: DownloadTask) -> None:
        """Notify all status callbacks."""
        for callback in self.status_callbacks:
            try:
                callback(task)
            except Exception as e:
                print(f"Error in status callback: {e}")
