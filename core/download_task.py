"""
Download Task model for the Download Manager application.
Represents individual download tasks with their state and metadata.
"""

import time
import hashlib
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path


class DownloadStatus(Enum):
    """Enumeration of possible download states."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"
    QUEUED = "queued"


@dataclass
class DownloadPart:
    """Represents a part of a multi-threaded download."""
    part_number: int
    start_byte: int
    end_byte: int
    downloaded_bytes: int = 0
    status: DownloadStatus = DownloadStatus.PENDING
    temp_file_path: Optional[str] = None


class DownloadTask:
    """Represents a download task with all its metadata and state."""
    
    def __init__(self, url: str, filename: Optional[str] = None, 
                 destination: Optional[str] = None):
        self.id = self._generate_id(url)
        self.url = url
        self.filename = filename or self._extract_filename_from_url(url)
        self.destination = destination
        self.file_size = 0
        self.downloaded_bytes = 0
        self.status = DownloadStatus.PENDING
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.error_message: Optional[str] = None
        self.retry_count = 0
        self.max_retries = 3
        
        # Multi-threading support
        self.supports_range_requests = False
        self.parts: List[DownloadPart] = []
        self.num_threads = 1
        
        # Progress tracking
        self.download_speed = 0.0  # bytes per second
        self.eta = 0  # estimated time to completion in seconds
        self.progress_percentage = 0.0
        
        # Additional metadata
        self.content_type: Optional[str] = None
        self.headers: Dict[str, str] = {}
        self.checksum: Optional[str] = None
        self.is_video = False
        self.video_quality: Optional[str] = None
        
        # Scheduling
        self.scheduled_time: Optional[float] = None
        self.priority = 0  # Higher number = higher priority
    
    def _generate_id(self, url: str) -> str:
        """Generate a unique ID for the download task."""
        return hashlib.md5(f"{url}{time.time()}".encode()).hexdigest()[:12]
    
    def _extract_filename_from_url(self, url: str) -> str:
        """Extract filename from URL."""
        try:
            from urllib.parse import urlparse, unquote
            parsed = urlparse(url)
            filename = unquote(parsed.path.split('/')[-1])
            if not filename or '.' not in filename:
                filename = f"download_{self.id}"
            return filename
        except Exception:
            return f"download_{self.id}"
    
    def get_full_path(self) -> str:
        """Get the full file path for the download."""
        if self.destination:
            return str(Path(self.destination) / self.filename)
        return self.filename
    
    def update_progress(self, downloaded_bytes: int) -> None:
        """Update download progress."""
        self.downloaded_bytes = downloaded_bytes
        if self.file_size > 0:
            self.progress_percentage = (downloaded_bytes / self.file_size) * 100
        else:
            self.progress_percentage = 0
    
    def calculate_speed(self, time_elapsed: float) -> None:
        """Calculate download speed."""
        if time_elapsed > 0:
            self.download_speed = self.downloaded_bytes / time_elapsed
    
    def calculate_eta(self) -> None:
        """Calculate estimated time to completion."""
        if self.download_speed > 0 and self.file_size > 0:
            remaining_bytes = self.file_size - self.downloaded_bytes
            self.eta = remaining_bytes / self.download_speed
        else:
            self.eta = 0
    
    def start(self) -> None:
        """Mark the download as started."""
        self.status = DownloadStatus.DOWNLOADING
        self.started_at = time.time()
    
    def pause(self) -> None:
        """Pause the download."""
        if self.status == DownloadStatus.DOWNLOADING:
            self.status = DownloadStatus.PAUSED
    
    def resume(self) -> None:
        """Resume the download."""
        if self.status == DownloadStatus.PAUSED:
            self.status = DownloadStatus.DOWNLOADING
    
    def complete(self) -> None:
        """Mark the download as completed."""
        self.status = DownloadStatus.COMPLETED
        self.completed_at = time.time()
        self.progress_percentage = 100.0
        self.downloaded_bytes = self.file_size
    
    def error(self, message: str) -> None:
        """Mark the download as failed with an error message."""
        self.status = DownloadStatus.ERROR
        self.error_message = message
    
    def cancel(self) -> None:
        """Cancel the download."""
        self.status = DownloadStatus.CANCELLED
    
    def can_retry(self) -> bool:
        """Check if the download can be retried."""
        return self.retry_count < self.max_retries
    
    def retry(self) -> None:
        """Retry the download."""
        if self.can_retry():
            self.retry_count += 1
            self.status = DownloadStatus.PENDING
            self.error_message = None
    
    def setup_multithread_download(self, num_threads: int, file_size: int) -> None:
        """Setup multi-threaded download parts."""
        self.num_threads = num_threads
        self.file_size = file_size
        self.supports_range_requests = True
        self.parts = []
        
        if num_threads <= 1:
            # Single-threaded download
            part = DownloadPart(0, 0, file_size - 1)
            self.parts.append(part)
        else:
            # Multi-threaded download
            part_size = file_size // num_threads
            for i in range(num_threads):
                start_byte = i * part_size
                end_byte = start_byte + part_size - 1
                if i == num_threads - 1:  # Last part gets remaining bytes
                    end_byte = file_size - 1
                
                part = DownloadPart(i, start_byte, end_byte)
                self.parts.append(part)
    
    def get_total_downloaded_bytes(self) -> int:
        """Get total downloaded bytes from all parts."""
        return sum(part.downloaded_bytes for part in self.parts)
    
    def is_scheduled(self) -> bool:
        """Check if the download is scheduled for later."""
        return self.scheduled_time is not None and self.scheduled_time > time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a dictionary for serialization."""
        return {
            'id': self.id,
            'url': self.url,
            'filename': self.filename,
            'destination': self.destination,
            'file_size': self.file_size,
            'downloaded_bytes': self.downloaded_bytes,
            'status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'supports_range_requests': self.supports_range_requests,
            'num_threads': self.num_threads,
            'download_speed': self.download_speed,
            'eta': self.eta,
            'progress_percentage': self.progress_percentage,
            'content_type': self.content_type,
            'headers': self.headers,
            'checksum': self.checksum,
            'is_video': self.is_video,
            'video_quality': self.video_quality,
            'scheduled_time': self.scheduled_time,
            'priority': self.priority
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DownloadTask':
        """Create a DownloadTask from a dictionary."""
        task = cls(data['url'], data.get('filename'), data.get('destination'))
        task.id = data['id']
        task.file_size = data.get('file_size', 0)
        task.downloaded_bytes = data.get('downloaded_bytes', 0)
        task.status = DownloadStatus(data.get('status', 'pending'))
        task.created_at = data.get('created_at', time.time())
        task.started_at = data.get('started_at')
        task.completed_at = data.get('completed_at')
        task.error_message = data.get('error_message')
        task.retry_count = data.get('retry_count', 0)
        task.max_retries = data.get('max_retries', 3)
        task.supports_range_requests = data.get('supports_range_requests', False)
        task.num_threads = data.get('num_threads', 1)
        task.download_speed = data.get('download_speed', 0.0)
        task.eta = data.get('eta', 0)
        task.progress_percentage = data.get('progress_percentage', 0.0)
        task.content_type = data.get('content_type')
        task.headers = data.get('headers', {})
        task.checksum = data.get('checksum')
        task.is_video = data.get('is_video', False)
        task.video_quality = data.get('video_quality')
        task.scheduled_time = data.get('scheduled_time')
        task.priority = data.get('priority', 0)
        return task
