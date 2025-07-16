"""
Download Engine for the Download Manager application.
Implements multi-threaded downloading with pause/resume support.
"""

import threading
import time
import os
from typing import List, Optional, Callable, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from core.download_task import DownloadTask, DownloadStatus, DownloadPart
from network.http_client import HTTPClient
from filesystem.file_manager import FileManager
from config.settings import settings


class DownloadEngine:
    """Multi-threaded download engine with pause/resume support."""
    
    def __init__(self, progress_callback: Optional[Callable] = None,
                 status_callback: Optional[Callable] = None):
        self.http_client = HTTPClient()
        self.file_manager = FileManager()
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        
        # Thread management
        self.active_downloads: Dict[str, threading.Event] = {}
        self.download_threads: Dict[str, List[threading.Thread]] = {}
        self.stop_events: Dict[str, threading.Event] = {}
        
        # Progress tracking
        self.progress_data: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
    
    def start_download(self, task: DownloadTask) -> bool:
        """Start downloading a task."""
        try:
            # Check if already downloading
            if task.id in self.active_downloads:
                return False
            
            # Validate task
            if not self._validate_task(task):
                task.error("Invalid download task")
                return False
            
            # Get file information
            file_info = self._get_file_info(task)
            if not file_info:
                task.error("Failed to get file information")
                return False
            
            # Update task with file info
            self._update_task_with_file_info(task, file_info)
            
            # Check disk space
            if not self._check_disk_space(task):
                task.error("Insufficient disk space")
                return False
            
            # Setup download
            self._setup_download(task)
            
            # Start download threads
            return self._start_download_threads(task)
            
        except Exception as e:
            task.error(f"Failed to start download: {str(e)}")
            return False
    
    def pause_download(self, task: DownloadTask) -> bool:
        """Pause a download."""
        try:
            if task.id not in self.active_downloads:
                return False
            
            # Set stop event
            if task.id in self.stop_events:
                self.stop_events[task.id].set()
            
            # Wait for threads to finish
            self._wait_for_threads(task.id)
            
            # Update task status
            task.pause()
            self._notify_status_change(task)
            
            return True
            
        except Exception as e:
            print(f"Error pausing download {task.id}: {e}")
            return False
    
    def resume_download(self, task: DownloadTask) -> bool:
        """Resume a paused download."""
        try:
            if task.status != DownloadStatus.PAUSED:
                return False
            
            # Clear stop event
            if task.id in self.stop_events:
                self.stop_events[task.id].clear()
            
            # Resume download
            return self._start_download_threads(task)
            
        except Exception as e:
            task.error(f"Failed to resume download: {str(e)}")
            return False
    
    def cancel_download(self, task: DownloadTask) -> bool:
        """Cancel a download."""
        try:
            # Set stop event
            if task.id in self.stop_events:
                self.stop_events[task.id].set()
            
            # Wait for threads to finish
            self._wait_for_threads(task.id)
            
            # Clean up temporary files
            self._cleanup_download(task)
            
            # Update task status
            task.cancel()
            self._notify_status_change(task)
            
            return True
            
        except Exception as e:
            print(f"Error cancelling download {task.id}: {e}")
            return False
    
    def _validate_task(self, task: DownloadTask) -> bool:
        """Validate download task."""
        if not task.url:
            return False
        
        # Test connection
        if not self.http_client.test_connection(task.url):
            return False
        
        return True
    
    def _get_file_info(self, task: DownloadTask) -> Optional[Dict[str, Any]]:
        """Get file information from the server."""
        try:
            return self.http_client.get_file_info(task.url)
        except Exception as e:
            print(f"Error getting file info for {task.url}: {e}")
            return None
    
    def _update_task_with_file_info(self, task: DownloadTask, file_info: Dict[str, Any]) -> None:
        """Update task with file information."""
        task.file_size = file_info.get('file_size', 0)
        task.supports_range_requests = file_info.get('supports_range', False)
        task.content_type = file_info.get('content_type', '')
        task.headers = file_info.get('headers', {})
        
        # Update filename if not set or if server provides a better one
        server_filename = file_info.get('filename')
        if server_filename and (not task.filename or task.filename.startswith('download_')):
            task.filename = server_filename
    
    def _check_disk_space(self, task: DownloadTask) -> bool:
        """Check if there's sufficient disk space."""
        if task.file_size <= 0:
            return True  # Can't check without file size
        
        destination = task.destination or settings.get_download_directory()
        return self.file_manager.ensure_sufficient_space(destination, task.file_size)
    
    def _setup_download(self, task: DownloadTask) -> None:
        """Setup download configuration."""
        # Determine number of threads
        max_threads = settings.get('max_threads_per_download', 8)
        if task.supports_range_requests and task.file_size > 1024 * 1024:  # 1MB
            num_threads = min(max_threads, max(1, task.file_size // (1024 * 1024)))
        else:
            num_threads = 1
        
        # Setup multi-threaded download
        task.setup_multithread_download(num_threads, task.file_size)
        
        # Create temporary files for each part
        for part in task.parts:
            part.temp_file_path = self.file_manager.create_temp_file(task.id, part.part_number)
        
        # Initialize progress tracking
        with self.lock:
            self.progress_data[task.id] = {
                'start_time': time.time(),
                'last_update': time.time(),
                'last_bytes': 0
            }
        
        # Create stop event
        self.stop_events[task.id] = threading.Event()
        
        # Mark as started
        task.start()
        self._notify_status_change(task)
    
    def _start_download_threads(self, task: DownloadTask) -> bool:
        """Start download threads for each part."""
        try:
            # Mark as active
            self.active_downloads[task.id] = threading.Event()
            
            # Create threads for each part
            threads = []
            for part in task.parts:
                thread = threading.Thread(
                    target=self._download_part,
                    args=(task, part),
                    daemon=True
                )
                threads.append(thread)
                thread.start()
            
            self.download_threads[task.id] = threads
            
            # Start progress monitoring thread
            monitor_thread = threading.Thread(
                target=self._monitor_progress,
                args=(task,),
                daemon=True
            )
            monitor_thread.start()
            
            return True
            
        except Exception as e:
            print(f"Error starting download threads for {task.id}: {e}")
            return False
    
    def _download_part(self, task: DownloadTask, part: DownloadPart) -> None:
        """Download a specific part of the file."""
        try:
            part.status = DownloadStatus.DOWNLOADING
            
            # Calculate resume position
            resume_position = part.downloaded_bytes
            start_byte = part.start_byte + resume_position
            
            if start_byte > part.end_byte:
                part.status = DownloadStatus.COMPLETED
                return
            
            # Progress callback for this part
            def part_progress_callback(bytes_downloaded):
                if self.stop_events[task.id].is_set():
                    raise Exception("Download cancelled")
                
                part.downloaded_bytes = resume_position + bytes_downloaded
                self._update_overall_progress(task)
            
            # Download the part
            if task.supports_range_requests and len(task.parts) > 1:
                data = self.http_client.download_range(
                    task.url, start_byte, part.end_byte, part_progress_callback
                )
            else:
                data = self.http_client.download_full(task.url, part_progress_callback)
            
            # Write data to temporary file
            if data:
                self.file_manager.append_to_temp_file(part.temp_file_path, data)
                part.downloaded_bytes = len(data) + resume_position
                part.status = DownloadStatus.COMPLETED
            
        except Exception as e:
            if not self.stop_events[task.id].is_set():
                part.status = DownloadStatus.ERROR
                print(f"Error downloading part {part.part_number} of {task.id}: {e}")
    
    def _monitor_progress(self, task: DownloadTask) -> None:
        """Monitor download progress and update task."""
        while task.id in self.active_downloads and not self.stop_events[task.id].is_set():
            try:
                # Check if all parts are completed
                completed_parts = sum(1 for part in task.parts 
                                    if part.status == DownloadStatus.COMPLETED)
                
                if completed_parts == len(task.parts):
                    # All parts completed, merge files
                    self._complete_download(task)
                    break
                
                # Check for errors
                error_parts = [part for part in task.parts 
                             if part.status == DownloadStatus.ERROR]
                
                if error_parts and not task.can_retry():
                    task.error("Download failed after maximum retries")
                    self._cleanup_download(task)
                    break
                
                time.sleep(1)  # Update every second
                
            except Exception as e:
                print(f"Error monitoring progress for {task.id}: {e}")
                break
        
        # Clean up
        if task.id in self.active_downloads:
            del self.active_downloads[task.id]

    def _update_overall_progress(self, task: DownloadTask) -> None:
        """Update overall download progress."""
        with self.lock:
            # Calculate total downloaded bytes
            total_downloaded = task.get_total_downloaded_bytes()
            task.update_progress(total_downloaded)

            # Calculate speed and ETA
            current_time = time.time()
            progress_data = self.progress_data.get(task.id, {})

            time_elapsed = current_time - progress_data.get('start_time', current_time)
            if time_elapsed > 0:
                task.calculate_speed(time_elapsed)
                task.calculate_eta()

            # Update last update time
            progress_data['last_update'] = current_time
            progress_data['last_bytes'] = total_downloaded

            # Notify progress callback
            if self.progress_callback:
                self.progress_callback(task)

    def _complete_download(self, task: DownloadTask) -> None:
        """Complete the download by merging parts."""
        try:
            # Get temporary file paths in order
            temp_files = [part.temp_file_path for part in task.parts
                         if part.temp_file_path and os.path.exists(part.temp_file_path)]

            if not temp_files:
                task.error("No temporary files found")
                return

            # Determine final file path
            if not task.destination:
                task.destination = self.file_manager.get_file_category_directory(task.filename)

            final_path = os.path.join(task.destination, task.filename)

            # Merge temporary files
            if self.file_manager.merge_temp_files(temp_files, final_path):
                # Verify file integrity
                if self.file_manager.verify_file_integrity(final_path, task.file_size):
                    # Clean up temporary files
                    self.file_manager.cleanup_temp_files(temp_files)

                    # Mark as completed
                    task.complete()
                    self._notify_status_change(task)
                else:
                    task.error("File integrity verification failed")
            else:
                task.error("Failed to merge temporary files")

        except Exception as e:
            task.error(f"Failed to complete download: {str(e)}")

    def _cleanup_download(self, task: DownloadTask) -> None:
        """Clean up download resources."""
        try:
            # Clean up temporary files
            temp_files = [part.temp_file_path for part in task.parts
                         if part.temp_file_path]
            self.file_manager.cleanup_temp_files(temp_files)

            # Clean up tracking data
            with self.lock:
                if task.id in self.progress_data:
                    del self.progress_data[task.id]

            # Clean up thread tracking
            if task.id in self.download_threads:
                del self.download_threads[task.id]

            if task.id in self.stop_events:
                del self.stop_events[task.id]

        except Exception as e:
            print(f"Error cleaning up download {task.id}: {e}")

    def _wait_for_threads(self, download_id: str, timeout: float = 30.0) -> None:
        """Wait for download threads to finish."""
        if download_id not in self.download_threads:
            return

        threads = self.download_threads[download_id]
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=timeout)

    def _notify_status_change(self, task: DownloadTask) -> None:
        """Notify about status changes."""
        if self.status_callback:
            self.status_callback(task)

    def get_active_downloads(self) -> List[str]:
        """Get list of active download IDs."""
        return list(self.active_downloads.keys())

    def is_download_active(self, download_id: str) -> bool:
        """Check if a download is currently active."""
        return download_id in self.active_downloads

    def shutdown(self) -> None:
        """Shutdown the download engine."""
        # Stop all active downloads
        for download_id in list(self.active_downloads.keys()):
            if download_id in self.stop_events:
                self.stop_events[download_id].set()

        # Wait for all threads to finish
        for download_id in list(self.download_threads.keys()):
            self._wait_for_threads(download_id)

        # Close HTTP client
        self.http_client.close()
