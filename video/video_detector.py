"""
Video Detection module for the Download Manager application.
Detects and extracts video URLs from various platforms.
"""

import re
import requests
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs
import json

try:
    import youtube_dl
    YOUTUBE_DL_AVAILABLE = True
except ImportError:
    YOUTUBE_DL_AVAILABLE = False

try:
    from pytube import YouTube
    PYTUBE_AVAILABLE = True
except ImportError:
    PYTUBE_AVAILABLE = False


class VideoDetector:
    """Detects and extracts video information from URLs."""
    
    def __init__(self):
        self.supported_platforms = {
            'youtube.com': self._detect_youtube,
            'youtu.be': self._detect_youtube,
            'vimeo.com': self._detect_vimeo,
            'dailymotion.com': self._detect_dailymotion,
            'twitch.tv': self._detect_twitch,
            'facebook.com': self._detect_facebook,
            'instagram.com': self._detect_instagram,
            'twitter.com': self._detect_twitter,
            'tiktok.com': self._detect_tiktok
        }
        
        # Quality preferences (highest to lowest)
        self.quality_preferences = ['1080p', '720p', '480p', '360p', '240p']
    
    def detect_video(self, url: str) -> Optional[Dict[str, Any]]:
        """Detect if URL contains video and extract information."""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check if domain is supported
            for supported_domain, detector_func in self.supported_platforms.items():
                if domain == supported_domain or domain.endswith('.' + supported_domain):
                    return detector_func(url)
            
            # Try generic video detection
            return self._detect_generic_video(url)
            
        except Exception as e:
            print(f"Error detecting video from {url}: {e}")
            return None
    
    def _detect_youtube(self, url: str) -> Optional[Dict[str, Any]]:
        """Detect YouTube videos."""
        try:
            # Try pytube first (more reliable for YouTube)
            if PYTUBE_AVAILABLE:
                return self._detect_youtube_pytube(url)
            
            # Fallback to youtube-dl
            if YOUTUBE_DL_AVAILABLE:
                return self._detect_youtube_dl(url)
            
            # Manual extraction as last resort
            return self._detect_youtube_manual(url)
            
        except Exception as e:
            print(f"Error detecting YouTube video: {e}")
            return None
    
    def _detect_youtube_pytube(self, url: str) -> Optional[Dict[str, Any]]:
        """Detect YouTube video using pytube."""
        try:
            yt = YouTube(url)
            
            # Get available streams
            streams = yt.streams.filter(progressive=True, file_extension='mp4')
            
            if not streams:
                streams = yt.streams.filter(adaptive=True, file_extension='mp4')
            
            if streams:
                # Get the best quality stream
                best_stream = streams.order_by('resolution').desc().first()
                
                return {
                    'platform': 'youtube',
                    'title': yt.title,
                    'direct_url': best_stream.url,
                    'quality': best_stream.resolution,
                    'file_size': best_stream.filesize,
                    'duration': yt.length,
                    'thumbnail': yt.thumbnail_url,
                    'description': yt.description
                }
            
        except Exception as e:
            print(f"Pytube error: {e}")
        
        return None
    
    def _detect_youtube_dl(self, url: str) -> Optional[Dict[str, Any]]:
        """Detect YouTube video using youtube-dl."""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'best[ext=mp4]'
            }
            
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info:
                    return {
                        'platform': 'youtube',
                        'title': info.get('title', ''),
                        'direct_url': info.get('url', ''),
                        'quality': info.get('height', ''),
                        'file_size': info.get('filesize', 0),
                        'duration': info.get('duration', 0),
                        'thumbnail': info.get('thumbnail', ''),
                        'description': info.get('description', '')
                    }
            
        except Exception as e:
            print(f"YouTube-dl error: {e}")
        
        return None
    
    def _detect_youtube_manual(self, url: str) -> Optional[Dict[str, Any]]:
        """Manual YouTube video detection (basic)."""
        try:
            # Extract video ID
            video_id = None
            
            if 'youtu.be/' in url:
                video_id = url.split('youtu.be/')[-1].split('?')[0]
            elif 'watch?v=' in url:
                video_id = url.split('watch?v=')[-1].split('&')[0]
            
            if video_id:
                return {
                    'platform': 'youtube',
                    'title': f'YouTube Video {video_id}',
                    'direct_url': None,  # Would need API key for direct URL
                    'quality': 'unknown',
                    'video_id': video_id
                }
            
        except Exception as e:
            print(f"Manual YouTube detection error: {e}")
        
        return None
    
    def _detect_vimeo(self, url: str) -> Optional[Dict[str, Any]]:
        """Detect Vimeo videos."""
        try:
            # Extract video ID from URL
            video_id_match = re.search(r'vimeo\.com/(\d+)', url)
            if not video_id_match:
                return None
            
            video_id = video_id_match.group(1)
            
            # Get video info from Vimeo API
            api_url = f"https://vimeo.com/api/v2/video/{video_id}.json"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()[0]
                
                return {
                    'platform': 'vimeo',
                    'title': data.get('title', ''),
                    'direct_url': None,  # Vimeo requires authentication for direct URLs
                    'quality': 'unknown',
                    'duration': data.get('duration', 0),
                    'thumbnail': data.get('thumbnail_large', ''),
                    'description': data.get('description', ''),
                    'video_id': video_id
                }
            
        except Exception as e:
            print(f"Vimeo detection error: {e}")
        
        return None
    
    def _detect_dailymotion(self, url: str) -> Optional[Dict[str, Any]]:
        """Detect Dailymotion videos."""
        try:
            # Extract video ID
            video_id_match = re.search(r'dailymotion\.com/video/([^_]+)', url)
            if not video_id_match:
                return None
            
            video_id = video_id_match.group(1)
            
            return {
                'platform': 'dailymotion',
                'title': f'Dailymotion Video {video_id}',
                'direct_url': None,
                'quality': 'unknown',
                'video_id': video_id
            }
            
        except Exception as e:
            print(f"Dailymotion detection error: {e}")
        
        return None
    
    def _detect_twitch(self, url: str) -> Optional[Dict[str, Any]]:
        """Detect Twitch videos/clips."""
        try:
            if 'clips.twitch.tv' in url or '/clip/' in url:
                return {
                    'platform': 'twitch',
                    'title': 'Twitch Clip',
                    'direct_url': None,
                    'quality': 'unknown'
                }
            elif '/videos/' in url:
                return {
                    'platform': 'twitch',
                    'title': 'Twitch VOD',
                    'direct_url': None,
                    'quality': 'unknown'
                }
            
        except Exception as e:
            print(f"Twitch detection error: {e}")
        
        return None
    
    def _detect_facebook(self, url: str) -> Optional[Dict[str, Any]]:
        """Detect Facebook videos."""
        try:
            if 'facebook.com' in url and '/videos/' in url:
                return {
                    'platform': 'facebook',
                    'title': 'Facebook Video',
                    'direct_url': None,
                    'quality': 'unknown'
                }
            
        except Exception as e:
            print(f"Facebook detection error: {e}")
        
        return None
    
    def _detect_instagram(self, url: str) -> Optional[Dict[str, Any]]:
        """Detect Instagram videos."""
        try:
            if 'instagram.com' in url and ('/p/' in url or '/reel/' in url):
                return {
                    'platform': 'instagram',
                    'title': 'Instagram Video',
                    'direct_url': None,
                    'quality': 'unknown'
                }
            
        except Exception as e:
            print(f"Instagram detection error: {e}")
        
        return None
    
    def _detect_twitter(self, url: str) -> Optional[Dict[str, Any]]:
        """Detect Twitter videos."""
        try:
            if 'twitter.com' in url and '/status/' in url:
                return {
                    'platform': 'twitter',
                    'title': 'Twitter Video',
                    'direct_url': None,
                    'quality': 'unknown'
                }
            
        except Exception as e:
            print(f"Twitter detection error: {e}")
        
        return None
    
    def _detect_tiktok(self, url: str) -> Optional[Dict[str, Any]]:
        """Detect TikTok videos."""
        try:
            if 'tiktok.com' in url:
                return {
                    'platform': 'tiktok',
                    'title': 'TikTok Video',
                    'direct_url': None,
                    'quality': 'unknown'
                }
            
        except Exception as e:
            print(f"TikTok detection error: {e}")
        
        return None
    
    def _detect_generic_video(self, url: str) -> Optional[Dict[str, Any]]:
        """Detect generic video files by extension."""
        try:
            parsed_url = urlparse(url)
            path = parsed_url.path.lower()
            
            video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
            
            for ext in video_extensions:
                if path.endswith(ext):
                    return {
                        'platform': 'direct',
                        'title': path.split('/')[-1],
                        'direct_url': url,
                        'quality': 'unknown'
                    }
            
        except Exception as e:
            print(f"Generic video detection error: {e}")
        
        return None
    
    def get_supported_platforms(self) -> List[str]:
        """Get list of supported platforms."""
        return list(self.supported_platforms.keys())
    
    def is_video_url(self, url: str) -> bool:
        """Check if URL is likely a video."""
        return self.detect_video(url) is not None
