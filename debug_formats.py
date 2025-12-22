import yt_dlp
import json

url = "https://youtu.be/wGj4n0afEFk"

ydl_opts = {
    'quiet': True,
    'noplaylist': True
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    print(f"Primary URL: {info.get('url')}")
    print(f"Primary Protocol: {info.get('protocol')}")
    
    print("\n--- HTTP Audio Formats ---")
    for f in info.get('formats', []):
        proto = f.get('protocol', '')
        if f.get('acodec') != 'none' and (proto.startswith('http') or proto in ['https', 'http']) and 'm3u8' not in proto:
            print(f"ID: {f.get('format_id')} | Ext: {f.get('ext')} | Proto: {f.get('protocol')} | Acodec: {f.get('acodec')} | Vcodec: {f.get('vcodec')}")
