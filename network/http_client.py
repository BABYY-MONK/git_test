"""
HTTP Client for the Download Manager application.
Handles all network operations including range requests and connection management.
"""

import requests
import aiohttp
import asyncio
from typing import Optional, Dict, Any, Tuple, AsyncGenerator
from urllib.parse import urlparse
import time
import ssl
from config.settings import settings


class HTTPClient:
    """Handles HTTP/HTTPS requests for downloading files."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DownloadManager/1.0 (compatible; like IDM)'
        })
        self.timeout = settings.get('connection_timeout', 30)
        self.chunk_size = settings.get('chunk_size', 8192)
    
    def get_file_info(self, url: str) -> Dict[str, Any]:
        """Get file information including size and range support."""
        try:
            response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            
            file_info = {
                'url': response.url,  # Final URL after redirects
                'file_size': int(response.headers.get('Content-Length', 0)),
                'supports_range': response.headers.get('Accept-Ranges') == 'bytes',
                'content_type': response.headers.get('Content-Type', ''),
                'filename': self._extract_filename_from_headers(response.headers, url),
                'headers': dict(response.headers),
                'status_code': response.status_code
            }
            
            return file_info
            
        except requests.RequestException as e:
            raise Exception(f"Failed to get file info: {str(e)}")
    
    def _extract_filename_from_headers(self, headers: Dict[str, str], url: str) -> Optional[str]:
        """Extract filename from Content-Disposition header or URL."""
        content_disposition = headers.get('Content-Disposition', '')
        if 'filename=' in content_disposition:
            try:
                filename = content_disposition.split('filename=')[1].strip('"\'')
                return filename
            except (IndexError, AttributeError):
                pass
        
        # Fallback to URL
        try:
            parsed_url = urlparse(url)
            filename = parsed_url.path.split('/')[-1]
            if filename and '.' in filename:
                return filename
        except Exception:
            pass
        
        return None
    
    def download_range(self, url: str, start_byte: int, end_byte: int, 
                      progress_callback=None) -> bytes:
        """Download a specific byte range from a URL."""
        headers = {'Range': f'bytes={start_byte}-{end_byte}'}
        
        try:
            response = self.session.get(
                url, 
                headers=headers, 
                stream=True, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            if response.status_code not in (206, 200):
                raise Exception(f"Server returned status {response.status_code}")
            
            data = b''
            downloaded = 0
            
            for chunk in response.iter_content(chunk_size=self.chunk_size):
                if chunk:
                    data += chunk
                    downloaded += len(chunk)
                    
                    if progress_callback:
                        progress_callback(downloaded)
            
            return data
            
        except requests.RequestException as e:
            raise Exception(f"Failed to download range {start_byte}-{end_byte}: {str(e)}")
    
    def download_full(self, url: str, progress_callback=None) -> bytes:
        """Download the entire file."""
        try:
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            data = b''
            downloaded = 0
            
            for chunk in response.iter_content(chunk_size=self.chunk_size):
                if chunk:
                    data += chunk
                    downloaded += len(chunk)
                    
                    if progress_callback:
                        progress_callback(downloaded)
            
            return data
            
        except requests.RequestException as e:
            raise Exception(f"Failed to download file: {str(e)}")
    
    def test_connection(self, url: str) -> bool:
        """Test if the URL is accessible."""
        try:
            response = self.session.head(url, timeout=self.timeout)
            return response.status_code < 400
        except requests.RequestException:
            return False
    
    def close(self):
        """Close the HTTP session."""
        self.session.close()


class AsyncHTTPClient:
    """Asynchronous HTTP client for concurrent downloads."""
    
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=settings.get('connection_timeout', 30))
        self.chunk_size = settings.get('chunk_size', 8192)
        self.connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            ssl=ssl.create_default_context()
        )
    
    async def get_file_info(self, url: str) -> Dict[str, Any]:
        """Asynchronously get file information."""
        async with aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout,
            headers={'User-Agent': 'DownloadManager/1.0 (compatible; like IDM)'}
        ) as session:
            try:
                async with session.head(url, allow_redirects=True) as response:
                    response.raise_for_status()
                    
                    file_info = {
                        'url': str(response.url),
                        'file_size': int(response.headers.get('Content-Length', 0)),
                        'supports_range': response.headers.get('Accept-Ranges') == 'bytes',
                        'content_type': response.headers.get('Content-Type', ''),
                        'filename': self._extract_filename_from_headers(response.headers, url),
                        'headers': dict(response.headers),
                        'status_code': response.status
                    }
                    
                    return file_info
                    
            except aiohttp.ClientError as e:
                raise Exception(f"Failed to get file info: {str(e)}")
    
    def _extract_filename_from_headers(self, headers: Dict[str, str], url: str) -> Optional[str]:
        """Extract filename from Content-Disposition header or URL."""
        content_disposition = headers.get('Content-Disposition', '')
        if 'filename=' in content_disposition:
            try:
                filename = content_disposition.split('filename=')[1].strip('"\'')
                return filename
            except (IndexError, AttributeError):
                pass
        
        # Fallback to URL
        try:
            parsed_url = urlparse(url)
            filename = parsed_url.path.split('/')[-1]
            if filename and '.' in filename:
                return filename
        except Exception:
            pass
        
        return None
    
    async def download_range(self, url: str, start_byte: int, end_byte: int,
                           progress_callback=None) -> AsyncGenerator[bytes, None]:
        """Asynchronously download a specific byte range."""
        headers = {'Range': f'bytes={start_byte}-{end_byte}'}
        
        async with aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout,
            headers={'User-Agent': 'DownloadManager/1.0 (compatible; like IDM)'}
        ) as session:
            try:
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    
                    if response.status not in (206, 200):
                        raise Exception(f"Server returned status {response.status}")
                    
                    downloaded = 0
                    async for chunk in response.content.iter_chunked(self.chunk_size):
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded)
                        yield chunk
                        
            except aiohttp.ClientError as e:
                raise Exception(f"Failed to download range {start_byte}-{end_byte}: {str(e)}")
    
    async def download_full(self, url: str, progress_callback=None) -> AsyncGenerator[bytes, None]:
        """Asynchronously download the entire file."""
        async with aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout,
            headers={'User-Agent': 'DownloadManager/1.0 (compatible; like IDM)'}
        ) as session:
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    
                    downloaded = 0
                    async for chunk in response.content.iter_chunked(self.chunk_size):
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded)
                        yield chunk
                        
            except aiohttp.ClientError as e:
                raise Exception(f"Failed to download file: {str(e)}")
    
    async def test_connection(self, url: str) -> bool:
        """Test if the URL is accessible."""
        async with aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout
        ) as session:
            try:
                async with session.head(url) as response:
                    return response.status < 400
            except aiohttp.ClientError:
                return False
    
    async def close(self):
        """Close the connector."""
        await self.connector.close()
