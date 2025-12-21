from utils import get_audio_url
import requests

video_url = "https://youtu.be/wGj4n0afEFk"

print(f"Fetching audio info for: {video_url}")
audio_url = get_audio_url(video_url)
print(f"Audio URL: {audio_url}")

if audio_url:
    try:
        head = requests.head(audio_url, allow_redirects=True)
        print(f"Status: {head.status_code}")
        print(f"Content-Type: {head.headers.get('Content-Type')}")
        print(f"Content-Length: {head.headers.get('Content-Length')}")
    except Exception as e:
        print(f"Error checking headers: {e}")
else:
    print("No audio URL found.")
