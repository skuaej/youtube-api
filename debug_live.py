import yt_dlp
import json

url = "https://youtu.be/YyepU5ztLf4"

ydl_opts = {
    'quiet': True,
    'no_warnings': True,
}

print(f"Inspecting {url}...")
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    try:
        info = ydl.extract_info(url, download=False)
        print(f"Title: {info.get('title')}")
        print(f"Is Live: {info.get('is_live')}")
        print(f"Formats: {len(info.get('formats', []))}")
        
        # Check what our current utils would pick
        # 'format': 'best[ext=mp4][protocol^=http]/best[protocol^=http]/best'
        
        # We can't easily simulate the selector string here without running a download/sim, 
        # but we can look at the formats.
        
        has_progressive = False
        for f in info.get('formats', []):
            if f.get('protocol', '').startswith('http') and f.get('ext') == 'mp4':
                # filter out dashboards/manifests if they are labeled mp4 but are not
                if 'manifest' not in f.get('url', ''):
                     has_progressive = True
                     # print(f"Found progressive: {f['format_id']} - {f['resolution']}")
        
        print(f"Has Progressive MP4: {has_progressive}")

    except Exception as e:
        print(f"Error: {e}")
