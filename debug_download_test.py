import asyncio
from custom_client import download_song

async def main():
    print("Attempting to download...")
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    result = await download_song(url)
    if result:
        print(f"Success! File saved at: {result}")
    else:
        print("Failed! download_song returned None.")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
