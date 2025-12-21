from utils import get_direct_url
import requests

video_url = "https://youtu.be/wGj4n0afEFk"

print(f"Fetching info for: {video_url}")
direct_url = get_direct_url(video_url, format_id=None)
print(f"Direct URL: {direct_url}")

if direct_url:
    try:
        # Check headers without downloading body
        head = requests.head(direct_url, allow_redirects=True)
        print(f"Status: {head.status_code}")
        print(f"Content-Type: {head.headers.get('Content-Type')}")
        print(f"Content-Length: {head.headers.get('Content-Length')}")
        
        # If head fails (some servers deny it), try get with stream
        if head.status_code != 200:
             with requests.get(direct_url, stream=True) as r:
                print(f"GET Status: {r.status_code}")
                print(f"GET Content-Type: {r.headers.get('Content-Type')}")
                print(f"GET Content-Length: {r.headers.get('Content-Length')}")
                
    except Exception as e:
        print(f"Error checking headers: {e}")
else:
    print("No direct URL found.")
