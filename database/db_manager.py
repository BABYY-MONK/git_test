"""
Database Manager for the Download Manager application.
Handles persistent storage of download metadata using SQLite.
"""

import sqlite3
import json
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from config.settings import settings
from core.download_task import DownloadTask, DownloadStatus


class DatabaseManager:
    """Manages SQLite database operations for download persistence."""
    
    def __init__(self):
        self.db_path = self._get_database_path()
        self.lock = threading.Lock()
        self._initialize_database()
    
    def _get_database_path(self) -> Path:
        """Get the database file path."""
        config_dir = Path(settings.config_dir)
        return config_dir / "downloads.db"
    
    def _initialize_database(self) -> None:
        """Initialize the database with required tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create downloads table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS downloads (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    destination TEXT,
                    file_size INTEGER DEFAULT 0,
                    downloaded_bytes INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at REAL NOT NULL,
                    started_at REAL,
                    completed_at REAL,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    supports_range_requests BOOLEAN DEFAULT 0,
                    num_threads INTEGER DEFAULT 1,
                    download_speed REAL DEFAULT 0.0,
                    eta REAL DEFAULT 0,
                    progress_percentage REAL DEFAULT 0.0,
                    content_type TEXT,
                    headers TEXT,
                    checksum TEXT,
                    is_video BOOLEAN DEFAULT 0,
                    video_quality TEXT,
                    scheduled_time REAL,
                    priority INTEGER DEFAULT 0
                )
            ''')
            
            # Create download_parts table for multi-threaded downloads
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS download_parts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    download_id TEXT NOT NULL,
                    part_number INTEGER NOT NULL,
                    start_byte INTEGER NOT NULL,
                    end_byte INTEGER NOT NULL,
                    downloaded_bytes INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    temp_file_path TEXT,
                    FOREIGN KEY (download_id) REFERENCES downloads (id),
                    UNIQUE (download_id, part_number)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads (status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads_created_at ON downloads (created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_download_parts_download_id ON download_parts (download_id)')
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper locking."""
        with self.lock:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            try:
                yield conn
            finally:
                conn.close()
    
    def save_download(self, task: DownloadTask) -> bool:
        """Save or update a download task in the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Convert task to database format
                data = task.to_dict()
                data['headers'] = json.dumps(data['headers'])
                data['supports_range_requests'] = int(data['supports_range_requests'])
                data['is_video'] = int(data['is_video'])
                
                # Insert or replace the download
                cursor.execute('''
                    INSERT OR REPLACE INTO downloads (
                        id, url, filename, destination, file_size, downloaded_bytes,
                        status, created_at, started_at, completed_at, error_message,
                        retry_count, max_retries, supports_range_requests, num_threads,
                        download_speed, eta, progress_percentage, content_type, headers,
                        checksum, is_video, video_quality, scheduled_time, priority
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['id'], data['url'], data['filename'], data['destination'],
                    data['file_size'], data['downloaded_bytes'], data['status'],
                    data['created_at'], data['started_at'], data['completed_at'],
                    data['error_message'], data['retry_count'], data['max_retries'],
                    data['supports_range_requests'], data['num_threads'],
                    data['download_speed'], data['eta'], data['progress_percentage'],
                    data['content_type'], data['headers'], data['checksum'],
                    data['is_video'], data['video_quality'], data['scheduled_time'],
                    data['priority']
                ))
                
                # Save download parts if they exist
                if task.parts:
                    # Delete existing parts
                    cursor.execute('DELETE FROM download_parts WHERE download_id = ?', (task.id,))
                    
                    # Insert new parts
                    for part in task.parts:
                        cursor.execute('''
                            INSERT INTO download_parts (
                                download_id, part_number, start_byte, end_byte,
                                downloaded_bytes, status, temp_file_path
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            task.id, part.part_number, part.start_byte, part.end_byte,
                            part.downloaded_bytes, part.status.value, part.temp_file_path
                        ))
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            print(f"Database error saving download {task.id}: {e}")
            return False
    
    def load_download(self, download_id: str) -> Optional[DownloadTask]:
        """Load a download task from the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Load download data
                cursor.execute('SELECT * FROM downloads WHERE id = ?', (download_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                # Convert row to dictionary
                data = dict(row)
                data['headers'] = json.loads(data['headers'] or '{}')
                data['supports_range_requests'] = bool(data['supports_range_requests'])
                data['is_video'] = bool(data['is_video'])
                
                # Create task from data
                task = DownloadTask.from_dict(data)
                
                # Load download parts
                cursor.execute('''
                    SELECT * FROM download_parts 
                    WHERE download_id = ? 
                    ORDER BY part_number
                ''', (download_id,))
                
                parts_rows = cursor.fetchall()
                if parts_rows:
                    from core.download_task import DownloadPart
                    task.parts = []
                    for part_row in parts_rows:
                        part = DownloadPart(
                            part_number=part_row['part_number'],
                            start_byte=part_row['start_byte'],
                            end_byte=part_row['end_byte'],
                            downloaded_bytes=part_row['downloaded_bytes'],
                            status=DownloadStatus(part_row['status']),
                            temp_file_path=part_row['temp_file_path']
                        )
                        task.parts.append(part)
                
                return task
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            print(f"Database error loading download {download_id}: {e}")
            return None
    
    def load_all_downloads(self) -> List[DownloadTask]:
        """Load all download tasks from the database."""
        downloads = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM downloads ORDER BY created_at DESC')
                
                for row in cursor.fetchall():
                    download = self.load_download(row['id'])
                    if download:
                        downloads.append(download)
                        
        except sqlite3.Error as e:
            print(f"Database error loading all downloads: {e}")
        
        return downloads
    
    def delete_download(self, download_id: str) -> bool:
        """Delete a download task from the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete download parts first (foreign key constraint)
                cursor.execute('DELETE FROM download_parts WHERE download_id = ?', (download_id,))
                
                # Delete download
                cursor.execute('DELETE FROM downloads WHERE id = ?', (download_id,))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            print(f"Database error deleting download {download_id}: {e}")
            return False
    
    def get_downloads_by_status(self, status: DownloadStatus) -> List[DownloadTask]:
        """Get all downloads with a specific status."""
        downloads = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id FROM downloads WHERE status = ? ORDER BY created_at DESC',
                    (status.value,)
                )
                
                for row in cursor.fetchall():
                    download = self.load_download(row['id'])
                    if download:
                        downloads.append(download)
                        
        except sqlite3.Error as e:
            print(f"Database error getting downloads by status {status}: {e}")
        
        return downloads
    
    def update_download_progress(self, download_id: str, downloaded_bytes: int,
                               progress_percentage: float, download_speed: float,
                               eta: float) -> bool:
        """Update download progress in the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE downloads 
                    SET downloaded_bytes = ?, progress_percentage = ?, 
                        download_speed = ?, eta = ?
                    WHERE id = ?
                ''', (downloaded_bytes, progress_percentage, download_speed, eta, download_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            print(f"Database error updating progress for {download_id}: {e}")
            return False
    
    def cleanup_completed_downloads(self, days_old: int = 30) -> int:
        """Clean up completed downloads older than specified days."""
        try:
            import time
            cutoff_time = time.time() - (days_old * 24 * 3600)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get IDs of downloads to delete
                cursor.execute('''
                    SELECT id FROM downloads 
                    WHERE status = 'completed' AND completed_at < ?
                ''', (cutoff_time,))
                
                download_ids = [row['id'] for row in cursor.fetchall()]
                
                # Delete download parts
                for download_id in download_ids:
                    cursor.execute('DELETE FROM download_parts WHERE download_id = ?', (download_id,))
                
                # Delete downloads
                cursor.execute('''
                    DELETE FROM downloads 
                    WHERE status = 'completed' AND completed_at < ?
                ''', (cutoff_time,))
                
                conn.commit()
                return len(download_ids)
                
        except sqlite3.Error as e:
            print(f"Database error during cleanup: {e}")
            return 0
    
    def get_download_statistics(self) -> Dict[str, Any]:
        """Get download statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Count downloads by status
                cursor.execute('''
                    SELECT status, COUNT(*) as count 
                    FROM downloads 
                    GROUP BY status
                ''')
                status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
                
                # Total downloads
                cursor.execute('SELECT COUNT(*) as total FROM downloads')
                total_downloads = cursor.fetchone()['total']
                
                # Total downloaded bytes
                cursor.execute('SELECT SUM(downloaded_bytes) as total_bytes FROM downloads')
                total_bytes = cursor.fetchone()['total_bytes'] or 0
                
                return {
                    'total_downloads': total_downloads,
                    'status_counts': status_counts,
                    'total_downloaded_bytes': total_bytes
                }
                
        except sqlite3.Error as e:
            print(f"Database error getting statistics: {e}")
            return {
                'total_downloads': 0,
                'status_counts': {},
                'total_downloaded_bytes': 0
            }
