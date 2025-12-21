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
            # If we asked for a specific format_id handled by yt-dlp selector (unlikely to match exact id syntax if complex),
            # but usually we iterate.
            # However, if format_id was None, info['url'] is the 'best' url.
            # If format_id was specific, we might still get a full list if we didn't specify format in opts correctly for finding JUST that one.
            # But let's stick to the previous filtered logic for specific ID, and direct info['url'] for default.
            
            if format_id:
                # If specific ID requested, we might need to look for it if 'format' opt didn't filter it alone (it can be tricky).
                # Re-using previous logic is safer for specific IDs unless we trust yt-dlp 'format' opt to just return that one.
                # Actually, if we pass 'format': format_id, extract_info should return that format's info or trigger selector.
                # But 'formats' list is often still present.
                if 'url' in info:
                    return info['url']
                for f in info.get('formats', []):
                    if f.get('format_id') == format_id:
                        return f.get('url')
            else:
               # specific case: just return the url of the simple 'best' selection
               return info.get('url')
               
            return None
        except Exception:
            # If 'best' fails (e.g. video only), we might fall back or just return None
            return None

def get_audio_url(url: str) -> Optional[str]:
    """
    Get the direct download URL for the best audio stream.
    """
    ydl_opts = get_opts({
        'quiet': True,
        'no_warnings': True,
        'format': 'bestaudio/best',
    })
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info.get('url')
        except Exception:
            return None
