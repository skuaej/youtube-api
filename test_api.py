import requests
import json

URL = "http://127.0.0.1:8000"
VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # Rick Roll - safe bet for availability

def test_info():
    print("Testing /info endpoint...")
    payload = {"url": VIDEO_URL}
    try:
        response = requests.post(f"{URL}/info", json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"Success! Title: {data.get('title')}")
        print(f"Formats found: {len(data.get('formats', []))}")
        
        # Return first format ID for download test
        if data.get('formats'):
            return data['formats'][0]['format_id']
    except Exception as e:
        print(f"Error testing /info: {e}")
        print(response.text if 'response' in locals() else "No response")
    return None

def test_download(format_id):
    print(f"\nTesting /download endpoint for format {format_id}...")
    try:
        # We don't verify SSL for this local test if needed, but it's local so it's fine.
        # We use allow_redirects=False to see the 307
        response = requests.get(f"{URL}/download", params={"url": VIDEO_URL, "format_id": format_id}, allow_redirects=False)
        
        if response.status_code == 307:
            print(f"Success! Redirected to: {response.headers.get('Location')[:50]}...")
        else:
            print(f"Unexpected status: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error testing /download: {e}")

if __name__ == "__main__":
    fmt_id = test_info()
    if fmt_id:
        test_download(fmt_id)
