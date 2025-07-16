"""
Download Scheduler for the Download Manager application.
Handles scheduled downloads and time-based triggers.
"""

import threading
import time
import heapq
from typing import List, Callable, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from core.download_task import DownloadTask


@dataclass
class ScheduledItem:
    """Represents a scheduled download item."""
    scheduled_time: float
    task: DownloadTask
    
    def __lt__(self, other):
        return self.scheduled_time < other.scheduled_time


class DownloadScheduler:
    """Manages scheduled downloads with time-based triggers."""
    
    def __init__(self, start_callback: Callable[[DownloadTask], None]):
        self.start_callback = start_callback
        self.scheduled_downloads: List[ScheduledItem] = []
        self.scheduler_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
    
    def start(self) -> None:
        """Start the scheduler."""
        if self.is_running:
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True
        )
        self.scheduler_thread.start()
    
    def stop(self) -> None:
        """Stop the scheduler."""
        self.is_running = False
        
        with self.condition:
            self.condition.notify()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0)
    
    def schedule_download(self, task: DownloadTask) -> bool:
        """Schedule a download for later execution."""
        if not task.scheduled_time or task.scheduled_time <= time.time():
            return False
        
        with self.condition:
            scheduled_item = ScheduledItem(task.scheduled_time, task)
            heapq.heappush(self.scheduled_downloads, scheduled_item)
            self.condition.notify()
        
        return True
    
    def unschedule_download(self, download_id: str) -> bool:
        """Remove a download from the schedule."""
        with self.condition:
            # Find and remove the scheduled item
            for i, item in enumerate(self.scheduled_downloads):
                if item.task.id == download_id:
                    del self.scheduled_downloads[i]
                    heapq.heapify(self.scheduled_downloads)  # Restore heap property
                    return True
        
        return False
    
    def reschedule_download(self, download_id: str, new_time: float) -> bool:
        """Reschedule a download to a new time."""
        with self.condition:
            # Find the task
            for item in self.scheduled_downloads:
                if item.task.id == download_id:
                    # Remove old schedule
                    self.unschedule_download(download_id)
                    
                    # Add new schedule
                    item.task.scheduled_time = new_time
                    return self.schedule_download(item.task)
        
        return False
    
    def get_scheduled_downloads(self) -> List[Tuple[float, DownloadTask]]:
        """Get all scheduled downloads."""
        with self.lock:
            return [(item.scheduled_time, item.task) for item in self.scheduled_downloads]
    
    def get_next_scheduled_time(self) -> Optional[float]:
        """Get the time of the next scheduled download."""
        with self.lock:
            if self.scheduled_downloads:
                return self.scheduled_downloads[0].scheduled_time
        return None
    
    def schedule_download_at(self, task: DownloadTask, target_datetime: datetime) -> bool:
        """Schedule a download at a specific datetime."""
        scheduled_time = target_datetime.timestamp()
        task.scheduled_time = scheduled_time
        return self.schedule_download(task)
    
    def schedule_download_after(self, task: DownloadTask, delay_seconds: int) -> bool:
        """Schedule a download after a delay in seconds."""
        scheduled_time = time.time() + delay_seconds
        task.scheduled_time = scheduled_time
        return self.schedule_download(task)
    
    def schedule_download_daily(self, task: DownloadTask, hour: int, minute: int = 0) -> bool:
        """Schedule a download to run daily at a specific time."""
        now = datetime.now()
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If the time has already passed today, schedule for tomorrow
        if target_time <= now:
            target_time += timedelta(days=1)
        
        return self.schedule_download_at(task, target_time)
    
    def schedule_download_weekly(self, task: DownloadTask, weekday: int, 
                               hour: int, minute: int = 0) -> bool:
        """Schedule a download to run weekly on a specific day and time."""
        now = datetime.now()
        days_ahead = weekday - now.weekday()
        
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        target_time = now + timedelta(days=days_ahead)
        target_time = target_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return self.schedule_download_at(task, target_time)
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self.is_running:
            try:
                with self.condition:
                    # Check if there are any scheduled downloads
                    if not self.scheduled_downloads:
                        self.condition.wait()  # Wait for new schedules
                        continue
                    
                    # Get the next scheduled download
                    next_item = self.scheduled_downloads[0]
                    current_time = time.time()
                    
                    if next_item.scheduled_time <= current_time:
                        # Time to start this download
                        item = heapq.heappop(self.scheduled_downloads)
                        
                        # Start the download
                        try:
                            self.start_callback(item.task)
                        except Exception as e:
                            print(f"Error starting scheduled download {item.task.id}: {e}")
                    
                    else:
                        # Wait until the next scheduled time
                        wait_time = next_item.scheduled_time - current_time
                        self.condition.wait(timeout=min(wait_time, 60))  # Max 1 minute wait
                        
            except Exception as e:
                print(f"Error in scheduler loop: {e}")
                time.sleep(1)
    
    def get_schedule_info(self, download_id: str) -> Optional[dict]:
        """Get scheduling information for a download."""
        with self.lock:
            for item in self.scheduled_downloads:
                if item.task.id == download_id:
                    scheduled_datetime = datetime.fromtimestamp(item.scheduled_time)
                    time_remaining = item.scheduled_time - time.time()
                    
                    return {
                        'scheduled_time': item.scheduled_time,
                        'scheduled_datetime': scheduled_datetime.isoformat(),
                        'time_remaining_seconds': max(0, time_remaining),
                        'is_due': time_remaining <= 0
                    }
        
        return None
    
    def clear_all_schedules(self) -> int:
        """Clear all scheduled downloads."""
        with self.condition:
            count = len(self.scheduled_downloads)
            self.scheduled_downloads.clear()
            return count
    
    def get_overdue_downloads(self) -> List[DownloadTask]:
        """Get downloads that are overdue (scheduled time has passed)."""
        current_time = time.time()
        overdue = []
        
        with self.lock:
            for item in self.scheduled_downloads:
                if item.scheduled_time <= current_time:
                    overdue.append(item.task)
        
        return overdue
    
    def cleanup_old_schedules(self, max_age_hours: int = 24) -> int:
        """Remove old scheduled downloads that are way overdue."""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        removed_count = 0
        
        with self.condition:
            # Filter out old schedules
            old_schedules = [item for item in self.scheduled_downloads 
                           if item.scheduled_time < cutoff_time]
            
            for old_item in old_schedules:
                self.scheduled_downloads.remove(old_item)
                removed_count += 1
            
            if removed_count > 0:
                heapq.heapify(self.scheduled_downloads)  # Restore heap property
        
        return removed_count
