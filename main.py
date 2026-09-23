from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import requests
import os
import traceback
from utils import get_video_info, get_direct_url, get_audio_url

# Secure Cookie Injection for Deployment
# Checks for COOKIES_TXT_CONTENT env var and creates/overwrites the file
VERSION = "1.1.0-debug"
WRITE_STATUS = "Not Attempted"

if 'COOKIES_TXT_CONTENT' in os.environ:
    print("Injecting cookies.txt from environment variable (Overwriting if exists)...")
    try:
        content = os.environ['COOKIES_TXT_CONTENT']
        if os.path.exists('cookies.txt'):
            os.remove('cookies.txt')
            
        with open('cookies.txt', 'w') as f:
            f.write(content)
            
        # Verify write
        size = os.path.getsize('cookies.txt')
        WRITE_STATUS = f"Success. Wrote {size} bytes. Env Var len: {len(content)}"
        print(WRITE_STATUS)
    except Exception as e:
        WRITE_STATUS = f"Error: {e}"
        print(f"Error writing cookies.txt: {e}")
else:
    WRITE_STATUS = "Skipped (Env Var missing)"
    print("WARNING: COOKIES_TXT_CONTENT env var not set. YouTube sign-in issues may occur.")

app = FastAPI(title="YouTube API", description="API to fetch YouTube video info and download links", version=VERSION)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Only mount static files if the directory exists
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

class VideoRequest(BaseModel):
    url: str

@app.get("/")
def read_root():
    if os.path.exists('static/index.html'):
        return FileResponse('static/index.html')
    return {"message": "API is running, but static/index.html was not found."}

@app.get("/debug-config")
def debug_config():
    """
    Returns debug information about the server configuration.
    WARNING: Do not expose this in production if it contains sensitive data.
    """
    cookies_exists = os.path.exists("cookies.txt")
    cookies_size = os.path.getsize("cookies.txt") if cookies_exists else 0
    
    # Read first line to verify content (without exposing full cookie)
    first_line = ""
    tail = ""
    if cookies_exists:
        try:
            with open("cookies.txt", "r") as f:
                content = f.read()
                first_line = content.splitlines()[0] if content else "Empty File"
                tail = content[-20:] if content else "Empty"
        except Exception as e:
            first_line = f"Error reading: {e}"

    return {
        "version": VERSION,
        "startup_write_status": WRITE_STATUS,
        "cwd": os.getcwd(),
        "cookies_txt_exists": cookies_exists,
        "cookies_txt_size": cookies_size,
        "env_var_present": "COOKIES_TXT_CONTENT" in os.environ,
        "env_var_length": len(os.environ.get("COOKIES_TXT_CONTENT", "")),
        "cookies_head": first_line[:30] + "..." if first_line else "Empty",
        "cookies_tail": tail
    }

@app.post("/info")
def get_info(request: VideoRequest):
    """
    Get metadata and formats for a YouTube video.
    """
    try:
        info = get_video_info(request.url)
        return info
    except Exception as e:
        print("CRITICAL ERROR IN /info ROUTE:")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=repr(e))

@app.get("/audio")
def stream_audio(url: str = Query(..., description="YouTube Video URL")):
    """
    Streams the best available audio for the given video.
    """
    try:
        audio_url = get_audio_url(url)
        if not audio_url:
            raise HTTPException(status_code=404, detail="Could not resolve audio URL.")
        
        r = requests.get(audio_url, stream=True)
        r.raise_for_status()
        
        content_type = r.headers.get("Content-Type", "application/octet-stream")
        content_length = r.headers.get("Content-Length")
        
        ext = "audio"
        if "webm" in content_type:
            ext = "webm"
        elif "mp4" in content_type:
            ext = "m4a"
        elif "mpeg" in content_type:
            ext = "mp3"
            
        headers = {
            "Content-Disposition": f'inline; filename="audio.{ext}"',
        }
        if content_length:
            headers["Content-Length"] = content_length

        return StreamingResponse(
            r.iter_content(chunk_size=256*1024),
            media_type=content_type,
            headers=headers
        )
    except Exception as e:
        print("CRITICAL ERROR IN /audio ROUTE:")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=repr(e))

@app.get("/download")
def download_video(
    url: str = Query(..., description="YouTube Video URL"), 
    format_id: str = Query(None, description="Format ID to download (optional, defaults to best)"),
    range_header: str = Header(None, alias="range")
):
    """
    Proxies the download through the server.
    """
    try:
        direct_url = get_direct_url(url, format_id)
        if not direct_url:
            raise HTTPException(status_code=404, detail="Could not resolve download URL for this format.")
        
        req_headers = {}
        if range_header:
            req_headers['Range'] = range_header

        r = requests.get(direct_url, stream=True, headers=req_headers)
        r.raise_for_status()

        resp_headers = {
            "Content-Disposition": f"attachment; filename=video.{format_id if format_id else 'mp4'}",
            "Accept-Ranges": "bytes"
        }
        
        for header in ['Content-Type', 'Content-Length', 'Content-Range']:
            if header in r.headers:
                resp_headers[header] = r.headers[header]

        return StreamingResponse(
            r.iter_content(chunk_size=256*1024),
            status_code=r.status_code,
            media_type=r.headers.get("Content-Type", "application/octet-stream"),
            headers=resp_headers
        )
    except Exception as e:
        print("CRITICAL ERROR IN /download ROUTE:")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=repr(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
