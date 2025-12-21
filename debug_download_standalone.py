import os
import urllib.request
import urllib.error

MY_API_URL = "https://civic-robby-uhhy5-a19ca05d.koyeb.app"

def download_song(link):
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    if not video_id or len(video_id) < 3:
        print("Invalid Video ID")
        return None

    DOWNLOAD_DIR = "downloads"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")

    if os.path.exists(file_path):
        os.remove(file_path)

    api_url = MY_API_URL
    stream_url = f"{api_url}/audio?url=https://www.youtube.com/watch?v={video_id}"
    print(f"Fetching: {stream_url}")

    try:
        with urllib.request.urlopen(stream_url) as response:
            print(f"Status Code: {response.getcode()}")
            if response.getcode() == 200:
                with open(file_path, "wb") as f:
                    while True:
                        chunk = response.read(16384)
                        if not chunk:
                            break
                        f.write(chunk)
                
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    return file_path
            else:
                print(f"Error: {response.read()}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
    except Exception as e:
        print(f"Error: {e}")
    
    return None

if __name__ == "__main__":
    print("Attempting to download...")
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    result = download_song(url)
    if result:
        print(f"Success! File saved at: {result}")
        print(f"File size: {os.path.getsize(result)} bytes")
    else:
        print("Failed!")
