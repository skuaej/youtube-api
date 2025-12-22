from utils import get_audio_url

if __name__ == "__main__":
    url = "https://youtu.be/NeXbmEnpSz0"
    print(f"Fetching audio info for: {url}")
    audio_url = get_audio_url(url)
    if audio_url:
        print(f"Audio URL: {audio_url}")
    else:
        print("No audio URL found.")
