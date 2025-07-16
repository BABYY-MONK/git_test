"""
File System Manager for the Download Manager application.
Handles file operations, temporary file management, and file merging.
"""

import os
import shutil
import hashlib
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
import threading
from config.settings import settings


class FileManager:
    """Manages file system operations for downloads."""
    
    def __init__(self):
        self.temp_dir = self._get_temp_directory()
        self.lock = threading.Lock()
    
    def _get_temp_directory(self) -> Path:
        """Get or create the temporary directory for download parts."""
        temp_dir = Path(tempfile.gettempdir()) / "DownloadManager"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir
    
    def create_temp_file(self, download_id: str, part_number: int) -> str:
        """Create a temporary file for a download part."""
        temp_filename = f"{download_id}_part_{part_number}.tmp"
        temp_path = self.temp_dir / temp_filename
        
        # Create empty file
        temp_path.touch()
        return str(temp_path)
    
    def write_to_temp_file(self, temp_file_path: str, data: bytes, 
                          offset: int = 0) -> int:
        """Write data to a temporary file at a specific offset."""
        try:
            with open(temp_file_path, 'r+b') as f:
                f.seek(offset)
                bytes_written = f.write(data)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
                return bytes_written
        except IOError as e:
            raise Exception(f"Failed to write to temp file {temp_file_path}: {str(e)}")
    
    def append_to_temp_file(self, temp_file_path: str, data: bytes) -> int:
        """Append data to a temporary file."""
        try:
            with open(temp_file_path, 'ab') as f:
                bytes_written = f.write(data)
                f.flush()
                os.fsync(f.fileno())
                return bytes_written
        except IOError as e:
            raise Exception(f"Failed to append to temp file {temp_file_path}: {str(e)}")
    
    def get_file_size(self, file_path: str) -> int:
        """Get the size of a file."""
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0
    
    def merge_temp_files(self, temp_files: List[str], output_path: str) -> bool:
        """Merge temporary files into the final output file."""
        try:
            with self.lock:
                # Ensure output directory exists
                output_dir = Path(output_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Create or truncate the output file
                with open(output_path, 'wb') as output_file:
                    for temp_file_path in temp_files:
                        if os.path.exists(temp_file_path):
                            with open(temp_file_path, 'rb') as temp_file:
                                shutil.copyfileobj(temp_file, output_file)
                        else:
                            raise Exception(f"Temporary file not found: {temp_file_path}")
                
                # Verify the merged file
                if not os.path.exists(output_path):
                    raise Exception("Failed to create merged file")
                
                return True
                
        except Exception as e:
            raise Exception(f"Failed to merge files: {str(e)}")
    
    def cleanup_temp_files(self, temp_files: List[str]) -> None:
        """Clean up temporary files after merging."""
        for temp_file_path in temp_files:
            try:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except OSError as e:
                print(f"Warning: Failed to remove temp file {temp_file_path}: {e}")
    
    def calculate_checksum(self, file_path: str, algorithm: str = 'md5') -> str:
        """Calculate checksum of a file."""
        hash_func = hashlib.new(algorithm)
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except IOError as e:
            raise Exception(f"Failed to calculate checksum: {str(e)}")
    
    def verify_file_integrity(self, file_path: str, expected_size: int, 
                            expected_checksum: Optional[str] = None) -> bool:
        """Verify file integrity by size and optionally checksum."""
        try:
            # Check file exists
            if not os.path.exists(file_path):
                return False
            
            # Check file size
            actual_size = self.get_file_size(file_path)
            if actual_size != expected_size:
                return False
            
            # Check checksum if provided
            if expected_checksum:
                actual_checksum = self.calculate_checksum(file_path)
                if actual_checksum.lower() != expected_checksum.lower():
                    return False
            
            return True
            
        except Exception:
            return False
    
    def move_to_final_location(self, temp_path: str, final_path: str) -> bool:
        """Move file from temporary location to final destination."""
        try:
            # Ensure destination directory exists
            final_dir = Path(final_path).parent
            final_dir.mkdir(parents=True, exist_ok=True)
            
            # Handle file name conflicts
            final_path = self._resolve_filename_conflict(final_path)
            
            # Move the file
            shutil.move(temp_path, final_path)
            return True
            
        except Exception as e:
            raise Exception(f"Failed to move file to final location: {str(e)}")
    
    def _resolve_filename_conflict(self, file_path: str) -> str:
        """Resolve filename conflicts by adding a number suffix."""
        path = Path(file_path)
        
        if not path.exists():
            return file_path
        
        base_name = path.stem
        extension = path.suffix
        directory = path.parent
        counter = 1
        
        while True:
            new_name = f"{base_name} ({counter}){extension}"
            new_path = directory / new_name
            if not new_path.exists():
                return str(new_path)
            counter += 1
    
    def get_available_space(self, path: str) -> int:
        """Get available disk space in bytes."""
        try:
            statvfs = os.statvfs(path)
            return statvfs.f_frsize * statvfs.f_bavail
        except (OSError, AttributeError):
            # Fallback for Windows
            try:
                import shutil
                return shutil.disk_usage(path).free
            except Exception:
                return 0
    
    def ensure_sufficient_space(self, path: str, required_size: int) -> bool:
        """Check if there's sufficient disk space for the download."""
        available_space = self.get_available_space(path)
        # Add 10% buffer for safety
        required_with_buffer = required_size * 1.1
        return available_space >= required_with_buffer
    
    def create_directory_structure(self, file_path: str) -> None:
        """Create directory structure for the given file path."""
        directory = Path(file_path).parent
        directory.mkdir(parents=True, exist_ok=True)
    
    def get_file_category_directory(self, filename: str) -> str:
        """Get the appropriate directory based on file extension."""
        file_extension = Path(filename).suffix
        return settings.get_category_directory(file_extension)
    
    def is_file_locked(self, file_path: str) -> bool:
        """Check if a file is locked by another process."""
        try:
            # Try to open the file in exclusive mode
            with open(file_path, 'r+b') as f:
                pass
            return False
        except (IOError, OSError):
            return True
    
    def cleanup_old_temp_files(self, max_age_hours: int = 24) -> None:
        """Clean up old temporary files."""
        import time
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        try:
            for file_path in self.temp_dir.glob("*.tmp"):
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                    except OSError:
                        pass  # Ignore errors when deleting old temp files
        except Exception:
            pass  # Ignore errors during cleanup
    
    def get_temp_files_for_download(self, download_id: str) -> List[str]:
        """Get all temporary files for a specific download."""
        pattern = f"{download_id}_part_*.tmp"
        temp_files = list(self.temp_dir.glob(pattern))
        # Sort by part number
        temp_files.sort(key=lambda x: int(x.stem.split('_')[-1]))
        return [str(f) for f in temp_files]
