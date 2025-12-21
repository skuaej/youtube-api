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
    Tries to find a progressive stream (m4a/webm) to avoid HLS issues.
    """
    # Common headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Sec-Fetch-Mode': 'navigate',
    }

    # Strategy 1: Try with cookies (if available) to bypass age-gates/premium checks
    try:
        ydl_opts_cookies = get_opts({
            'quiet': True,
            'noplaylist': True,
            # 'format': ... # We scan all formats manually
        })
        # Add headers manually to opts (yt-dlp usually handles this, but we force it)
        # Note: yt-dlp uses 'http_headers' key inside params, or we can pass it to YoutubeDL constructor?
        # Actually, standard way is just letting yt-dlp pick, but if we want to force:
        # We can't easily pass http_headers inside 'get_opts' dict directly for YoutubeDL unless using key 'http_headers'
        # BUT yt-dlp might override. Let's try passing it in the dict.
        ydl_opts_cookies['http_headers'] = headers
        
        return extract_audio_url_with_opts(url, ydl_opts_cookies)
    except Exception as e:
        print(f"Extraction with cookies failed: {e}")
        # Strategy 2: If cookies failed (e.g. flagged account, challenge error), try WITHOUT cookies
        # Some server IPs work better anonymously for certain videos.
        if os.path.exists('cookies.txt'):
             print("Retrying without cookies...")
             ydl_opts_no_cookies = {
                'quiet': True,
                'noplaylist': True,
                'http_headers': headers
             }
             try:
                return extract_audio_url_with_opts(url, ydl_opts_no_cookies)
             except Exception as e2:
                 # If both fail, raise the original error (or the new one)
                 raise Exception(f"Failed with and without cookies. Last error: {e2}")
        else:
            raise e

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
