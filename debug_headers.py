import urllib.request

url = "https://civic-robby-uhhy5-a19ca05d.koyeb.app/audio?url=https://www.youtube.com/watch?v=NeXbmEnpSz0"

try:
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req) as response:
        print(f"Status: {response.status}")
        print("Headers:")
        for k, v in response.getheaders():
            print(f"{k}: {v}")
        # Read a tiny bit to close connection cleanly
        response.read(10)
except Exception as e:
    print(f"Error: {e}")
