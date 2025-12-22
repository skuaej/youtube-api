import yt_dlp
from typing import Dict, Any, List, Optional
import os

def get_opts(base_opts: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to add common options like cookies and headers."""
    # 1. Add Cookies
    if os.path.exists('cookies.txt'):
        base_opts['cookiefile'] = 'cookies.txt'
    
    # 2. Add User Agent (REMOVED: Use default to match user's working bot)
    # forcing a UA might conflict with the cookies provided.
    # base_opts['user_agent'] = '...' 
    pass
    
    # 3. Explicitly enable Node.js
    # yt-dlp defaults to Deno-only recently. We must tell it to use node.
    # Error fix: js_runtimes must be a dict {name: config_dict}
    # Log said 'nodejs' is unsupported, used 'node' only.
    base_opts['js_runtimes'] = {'node': {}}
    
    return base_opts

from youtubesearchpython import VideosSearch

def get_video_info(url: str) -> Dict[str, Any]:
    """
    Fetches video metadata using youtubesearchpython (Hybrid Strategy).
    Avoids yt-dlp "Sign in" blocks for basic metadata.
    """
    try:
        # Extract ID from URL if possible, or search
        videosSearch = VideosSearch(url, limit = 1)
        result = videosSearch.result()
        
        if not result['result']:
            raise Exception("No video found")
            
        video = result['result'][0]
        
        # Map to our expected format
        return {
            'id': video.get('id'),
            'title': video.get('title'),
            'thumbnail': video.get('thumbnails', [{}])[-1].get('url'),
            'uploader': video.get('channel', {}).get('name'),
            'duration': video.get('duration'),
            'view_count': video.get('viewCount', {}).get('short'), # approximate
            'webpage_url': video.get('link'),
            'formats': {
                'video_audio': [], # Not available via search
                'video_only': [],
                'audio_only': []
            }
        }
    except Exception as e:
         # Fallback to yt-dlp if search fails (rare)
         print(f"Hybrid search failed: {e}. Falling back to yt-dlp...")
         ydl_opts = get_opts({
            'quiet': True,
            'no_warnings': True,
            'format': 'best',
        })
         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                return process_info(info)
            except Exception as e2:
                raise Exception(f"Hybrid and yt-dlp both failed: {str(e2)}")

def process_info(info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy helper - kept for fallback compatibility.
    """
    return {
        'id': info.get('id'),
        'title': info.get('title'),
        'thumbnail': info.get('thumbnail'),
        'uploader': info.get('uploader'),
        'duration': info.get('duration'),
        'view_count': info.get('view_count'),
        'webpage_url': info.get('webpage_url'),
        'formats': {'video_audio': [], 'video_only': [], 'audio_only': []} # Simplified
    }

def get_direct_url(url: str, format_id: Optional[str] = None) -> Optional[str]:
    """
    Get the direct download URL.
    If format_id is provided, tries to find that specific format.
    If format_id is None, asks yt-dlp for 'best' (best single file with v+a).
    """
    ydl_opts = get_opts({
        'quiet': True,
        'no_warnings': True,
        # Prefer mp4 with http protocol (progressive) over manifests
        'format': format_id if format_id else 'best[ext=mp4][protocol^=http]/best[protocol^=http]/best',
    })
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            
            if format_id:
                if 'url' in info:
                    return info['url']
                for f in info.get('formats', []):
                    if f.get('format_id') == format_id:
                        return f.get('url')
            else:
               return info.get('url')
               
            return None
        except Exception:
            return None

def get_audio_url(url: str) -> Optional[str]:
    """
    Get the direct download URL for the best audio stream.
    Tries to find a progressive stream (m4a/webm) to avoid HLS issues.
    """
    
    # Strategy 1: Android Client
    # This mimics the mobile app API, which is often less restrictive on datacenter IPs
    # and doesn't require "Sign in to confirm" web checks.
    android_opts = get_opts({
        'quiet': True,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'] # Try mobile clients
            }
        }
    })
    # Critical: yt-dlp skips Android client if cookies are present. We must remove them.
    if 'cookiefile' in android_opts:
        del android_opts['cookiefile']

    try:
        return extract_audio_url_with_opts(url, android_opts)
    except Exception as e:
        print(f"Extraction with Android client failed: {e}")
        
        # Strategy 2: Standard Web Client (No Cookies)
        # If Android fails (e.g. video blocked on mobile), try generic web request.
        # We NOW try with cookies if available, as that is the standard fix for "Sign in" errors.
        print("Retrying with standard Web client...")
        # Use get_opts to include cookies.txt if present
        web_opts = get_opts({
            'quiet': True,
            'noplaylist': True,
            # No custom headers, let yt-dlp mimic default
        })
        try:
            return extract_audio_url_with_opts(url, web_opts)
            raise Exception(f"Failed with Android and Web clients. Last error: {e2}")
            
        except Exception as e2:
            print(f"Web client failed: {e2}")
            
            # Strategy 3: TV Embedded Client
            # Last resort: Mimic a Smart TV. Often has different rate limits.
            print("Retrying with TV client...")
            tv_opts = get_opts({
                'quiet': True,
                'noplaylist': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['tv']
                    }
                }
            })
            # TV client usually works better WITHOUT cookies for public videos, 
            # or WITH them if premium. Let's try WITH cookies first since we have them.
            try:
                return extract_audio_url_with_opts(url, tv_opts)
            except Exception as e3:
                 raise Exception(f"All strategies failed (Android, Web, TV). Last error: {e3}")

def extract_audio_url_with_opts(url: str, opts: Dict[str, Any]) -> Optional[str]:
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # 1. Start by scanning ALL formats for the best progressive audio
        formats = info.get('formats', [])
        
        # Filter: Audio Only, Progressive (http/https), No Manifests
        valid_formats = [
            f for f in formats 
            if f.get('acodec') != 'none' 
            and (f.get('vcodec') == 'none' or f.get('vcodec') == 'null') # Strict audio only
            and (f.get('protocol') in ['https', 'http'] or f.get('protocol', '').startswith('http'))
            and not f.get('url', '').endswith('.m3u8')
        ]
        
        if valid_formats:
            # Sort by quality (filesize or bitrate), picking the best one
            best = sorted(valid_formats, key=lambda x: x.get('filesize') or x.get('tbr') or 0, reverse=True)[0]
            print(f"Selected Format: {best.get('format_id')} ({best.get('ext')})") # Debug
            return best['url']

        # 2. Fallback: If no strict progressive audio found, try primary URL if it's safe
        if info.get('url') and not info['url'].endswith('.m3u8') and info.get('protocol') != 'm3u8':
            return info['url']
            
        raise Exception("No progressive audio stream found (HLS only).")
