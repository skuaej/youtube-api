import yt_dlp
from typing import Dict, Any, Optional
import os

def get_opts(base_opts: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to add common options like cookies and Node.js runtime."""
    if os.path.exists('cookies.txt'):
        base_opts['cookiefile'] = 'cookies.txt'
    
    base_opts['js_runtimes'] = {'node': {}}
    return base_opts

def get_video_info(url: str) -> Dict[str, Any]:
    """Fetches video metadata and formats securely using yt-dlp and cookies."""
    ydl_opts = get_opts({
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
    })
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                'id': info.get('id'),
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'uploader': info.get('uploader'),
                'duration': info.get('duration'),
                'view_count': info.get('view_count'),
                'webpage_url': info.get('webpage_url'),
                'formats': info.get('formats', []) # Passes actual download links to frontend
            }
        except Exception as e:
            raise Exception(f"yt-dlp failed to fetch video info: {str(e)}")

def get_direct_url(url: str, format_id: Optional[str] = None) -> Optional[str]:
    """Gets the direct download URL for a specific format or best available."""
    ydl_opts = get_opts({
        'quiet': True,
        'no_warnings': True,
        'format': format_id if format_id else 'best[ext=mp4][protocol^=http]/best[protocol^=http]/best',
    })
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if format_id:
                for f in info.get('formats', []):
                    if f.get('format_id') == format_id:
                        return f.get('url')
            return info.get('url')
        except Exception:
            return None

def get_audio_url(url: str) -> Optional[str]:
    """Gets the direct download URL for the best audio stream using fallback strategies."""
    # Strategy 1: Android Client (Usually bypasses blocks, no cookies allowed)
    android_opts = get_opts({
        'quiet': True,
        'noplaylist': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}}
    })
    if 'cookiefile' in android_opts:
        del android_opts['cookiefile']

    try:
        return extract_audio_url_with_opts(url, android_opts)
    except Exception as e:
        print(f"Extraction with Android client failed: {e}")
        
        # Strategy 2: Standard Web Client (Requires cookies)
        web_opts = get_opts({
            'quiet': True,
            'noplaylist': True,
        })
        try:
            return extract_audio_url_with_opts(url, web_opts)
        except Exception as e2:
            print(f"Web client failed: {e2}")
            
            # Strategy 3: TV Embedded Client
            tv_opts = get_opts({
                'quiet': True,
                'noplaylist': True,
                'extractor_args': {'youtube': {'player_client': ['tv']}}
            })
            try:
                return extract_audio_url_with_opts(url, tv_opts)
            except Exception as e3:
                 raise Exception(f"All strategies failed. Last error: {e3}")

def extract_audio_url_with_opts(url: str, opts: Dict[str, Any]) -> Optional[str]:
    """Helper to extract progressive audio from yt-dlp formats."""
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get('formats', [])
        
        valid_formats = [
            f for f in formats 
            if f.get('acodec') != 'none' 
            and (f.get('vcodec') == 'none' or f.get('vcodec') == 'null')
            and (f.get('protocol') in ['https', 'http'] or f.get('protocol', '').startswith('http'))
            and not f.get('url', '').endswith('.m3u8')
        ]
        
        if valid_formats:
            best = sorted(valid_formats, key=lambda x: x.get('filesize') or x.get('tbr') or 0, reverse=True)[0]
            return best['url']

        if info.get('url') and not info['url'].endswith('.m3u8') and info.get('protocol') != 'm3u8':
            return info['url']
            
        raise Exception("No progressive audio stream found.")
