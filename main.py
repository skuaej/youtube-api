from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import requests
from utils import get_video_info, get_direct_url, get_audio_url

app = FastAPI(title="YouTube API", description="API to fetch YouTube video info and download links", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

class VideoRequest(BaseModel):
    url: str

@app.get("/")
def read_root():
    return FileResponse('static/index.html')

@app.post("/info")
def get_info(request: VideoRequest):
    """
    Get metadata and formats for a YouTube video.
    """
    try:
        info = get_video_info(request.url)
        return info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/audio")
def stream_audio(url: str = Query(..., description="YouTube Video URL")):
    """
    Streams the best available audio for the given video.
    """
    try:
        audio_url = get_audio_url(url)
        if not audio_url:
            raise HTTPException(status_code=404, detail="Could not resolve audio URL.")
        
        # Get headers/stream from the direct URL
        r = requests.get(audio_url, stream=True)
        r.raise_for_status()
        
        content_type = r.headers.get("Content-Type", "application/octet-stream")
        content_length = r.headers.get("Content-Length")
        
        # Determine extension
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
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/download")
def download_video(
    url: str = Query(..., description="YouTube Video URL"), 
    format_id: str = Query(None, description="Format ID to download (optional, defaults to best)"),
    range: str = Header(None)
):
    """
    Proxies the download through the server.
    Supports Range headers for seeking.
    """
    try:
        direct_url = get_direct_url(url, format_id)
        if not direct_url:
            raise HTTPException(status_code=404, detail="Could not resolve download URL for this format.")
        
        # Forward Range header if present
        req_headers = {}
        if range:
            req_headers['Range'] = range

        # Open stream
        r = requests.get(direct_url, stream=True, headers=req_headers)
        r.raise_for_status()

        # Prepare response headers
        resp_headers = {
            "Content-Disposition": f"attachment; filename=video.{format_id if format_id else 'mp4'}",
            "Accept-Ranges": "bytes"
        }
        
        # Forward specific headers related to range/content
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
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
