import yt_dlp
from typing import Dict, Any, List, Optional
import os

def get_opts(base_opts: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to add common options like cookies."""
    if os.path.exists('cookies.txt'):
        base_opts['cookiefile'] = 'cookies.txt'
    return base_opts

def get_video_info(url: str) -> Dict[str, Any]:
    """
    Fetches video metadata and formats from YouTube using yt-dlp.
    """
    ydl_opts = get_opts({
        'quiet': True,
        'no_warnings': True,
        'format': 'best',  # Default to best, but we will list all
    })
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return process_info(info)
        except Exception as e:
            raise Exception(f"Error fetching video info: {str(e)}")

def process_info(info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cleans and structures the raw yt-dlp info dictionary.
    Groups formats by usability.
    """
    video_audio = []
    video_only = []
    audio_only = []
    
    # Extract formats
    if 'formats' in info:
        for f in info['formats']:
            # Basic filtering
            if 'url' not in f:
                continue
            
            # Skip manifest formats if we intend to offer direct downloads, 
            # though they are fine for streaming players. 
            # For simplicity, let's keep everything but categorize them.
            
            fmt = {
                'format_id': f.get('format_id'),
                'ext': f.get('ext'),
                'resolution': f.get('resolution') or (f'{f.get("width")}x{f.get("height")}' if f.get("width") else 'audio only'),
                'filesize': f.get('filesize'),
                'filesize_approx': f.get('filesize_approx'),
                'vcodec': f.get('vcodec'),
                'acodec': f.get('acodec'),
                'tbr': f.get('tbr'), # Total bitrate
                'note': f.get('format_note', ''),
                'height': f.get('height', 0) or 0,
            }
            
            is_video = f.get('vcodec') != 'none'
            is_audio = f.get('acodec') != 'none'

            if is_video and is_audio:
                fmt['type'] = 'video+audio'
                video_audio.append(fmt)
            elif is_video:
                fmt['type'] = 'video'
                video_only.append(fmt)
            elif is_audio:
                fmt['type'] = 'audio'
                audio_only.append(fmt)

    # Sort by quality (height or bitrate) descending
    video_audio.sort(key=lambda x: x['height'] or 0, reverse=True)
    video_only.sort(key=lambda x: x['height'] or 0, reverse=True)
    audio_only.sort(key=lambda x: x['tbr'] or 0, reverse=True)

    return {
        'id': info.get('id'),
        'title': info.get('title'),
        'thumbnail': info.get('thumbnail'),
        'uploader': info.get('uploader'),
        'duration': info.get('duration'),
        'view_count': info.get('view_count'),
        'webpage_url': info.get('webpage_url'),
        'formats': {
            'video_audio': video_audio,
            'video_only': video_only,
            'audio_only': audio_only
        }
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
    Prioritizes direct progressive links (m4a/webm) over HLS manifests to ensure compatibility with simple downloaders.
    """
    ydl_opts = get_opts({
        # We explicitly ask for m4a or webm audio that is NOT a manifest (protocol starts with http)
        # This string tells yt-dlp: Look for best audio with m4a extension, OR best audio with webm extension, OR just best audio.
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True
    })
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            
            # Additional safety check preventing HLS/M3U8 return
            if info.get('url', '').endswith('.m3u8') or info.get('protocol') == 'm3u8':
                # Manifest detected despite preferences. Fallback to manual scan.
                print("Manifest detected, scanning formats for progressive stream...")
                formats = info.get('formats', [])
                valid_formats = [
                    f for f in formats 
                    if f.get('acodec') != 'none' 
                    and f.get('vcodec') == 'none'
                    and (f.get('protocol') in ['https', 'http'] or f.get('protocol', '').startswith('http'))
                    and not f.get('url', '').endswith('.m3u8')
                ]
                
                if valid_formats:
                    # Sort by size (proxy for quality)
                    best = sorted(valid_formats, key=lambda x: x.get('filesize') or 0, reverse=True)[0]
                    return best['url']

            return info.get('url')
        except Exception as e:
            print(f"Audio URL Extraction Error: {e}")
            return None
