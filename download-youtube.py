from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional
import yt_dlp
import os
import uuid
import asyncio
import httpx
import json
from datetime import datetime
from enum import Enum
import time

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get proxy URL from environment variable if set
PROXY_URL = os.getenv('PROXY_URL')
print(f"[Startup] PROXY_URL configured: {bool(PROXY_URL)}")

# Concurrency control
MAX_CONCURRENT_DOWNLOADS = 5
download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

# Job storage (in-memory - consider Redis for production)
jobs = {}

class JobStatus(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"

class DownloadRequest(BaseModel):
    url: str
    resolution: str = "1080p"
    webhook_url: HttpUrl

class Job(BaseModel):
    job_id: str
    status: JobStatus
    url: str
    resolution: str
    webhook_url: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    # Progress tracking
    progress_percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed: Optional[str] = None
    eta: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>YouTube Downloader</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 500px;
                width: 100%;
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 28px;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                font-size: 14px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: 500;
                font-size: 14px;
            }
            input[type="url"], select {
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
            input[type="url"]:focus, select:focus {
                outline: none;
                border-color: #667eea;
            }
            button {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }
            button:active {
                transform: translateY(0);
            }
            button:disabled {
                background: #ccc;
                cursor: not-allowed;
                transform: none;
            }
            .message {
                margin-top: 20px;
                padding: 12px;
                border-radius: 8px;
                font-size: 14px;
                display: none;
            }
            .message.success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .message.error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .loading {
                display: none;
                margin-top: 20px;
            }
            .progress-container {
                background: #f0f0f0;
                border-radius: 8px;
                overflow: hidden;
                height: 30px;
                margin-bottom: 10px;
            }
            .progress-bar {
                height: 100%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                width: 0%;
                transition: width 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: 600;
                font-size: 12px;
            }
            .progress-message {
                font-size: 14px;
                color: #666;
                text-align: center;
            }
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 10px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>YouTube Downloader</h1>
            <p class="subtitle">Download YouTube videos in your preferred resolution</p>

            <form id="downloadForm">
                <div class="form-group">
                    <label for="url">YouTube URL</label>
                    <input
                        type="url"
                        id="url"
                        name="url"
                        placeholder="https://www.youtube.com/watch?v=..."
                        required
                    >
                </div>

                <div class="form-group">
                    <label for="resolution">Resolution</label>
                    <select id="resolution" name="resolution">
                        <option value="2160p">4K (2160p)</option>
                        <option value="1440p">2K (1440p)</option>
                        <option value="1080p" selected>Full HD (1080p)</option>
                        <option value="720p">HD (720p)</option>
                        <option value="480p">SD (480p)</option>
                        <option value="360p">360p</option>
                        <option value="240p">240p</option>
                    </select>
                </div>

                <button type="submit" id="downloadBtn">Download Video</button>
            </form>

            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p style="margin-top: 10px; color: #666;">Downloading...</p>
            </div>

            <div class="message" id="message"></div>
        </div>

        <script>
            const form = document.getElementById('downloadForm');
            const message = document.getElementById('message');
            const loading = document.getElementById('loading');
            const downloadBtn = document.getElementById('downloadBtn');

            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                const url = document.getElementById('url').value;
                const resolution = document.getElementById('resolution').value;

                // Hide previous messages
                message.style.display = 'none';
                message.className = 'message';

                // Show loading
                loading.style.display = 'block';
                downloadBtn.disabled = true;

                try {
                    const response = await fetch(`/download?url=${encodeURIComponent(url)}&resolution=${resolution}`);
                    const data = await response.json();

                    loading.style.display = 'none';
                    downloadBtn.disabled = false;

                    if (response.ok) {
                        message.className = 'message success';
                        message.innerHTML = `
                            ${data.message}<br>
                            <a href="${data.download_url}" download="${data.filename}"
                               style="color: #155724; font-weight: bold; text-decoration: underline; margin-top: 10px; display: inline-block;">
                                Click here to download ${data.filename}
                            </a>
                        `;
                        message.style.display = 'block';
                        form.reset();
                        document.getElementById('resolution').value = '1080p';
                    } else {
                        message.className = 'message error';
                        message.textContent = data.detail || 'An error occurred';
                        message.style.display = 'block';
                    }
                } catch (error) {
                    loading.style.display = 'none';
                    downloadBtn.disabled = false;
                    message.className = 'message error';
                    message.textContent = 'Network error: ' + error.message;
                    message.style.display = 'block';
                }
            });
        </script>
    </body>
    </html>
    """

# Webhook delivery with retry logic
async def send_webhook(webhook_url: str, payload: dict, max_retries: int = 3):
    """Send webhook with exponential backoff retry"""
    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    timeout=30.0
                )
                if response.status_code < 400:
                    return True
            except Exception as e:
                pass

            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s backoff

    return False

# Background download worker
async def download_worker(job_id: str):
    """Process download in background with concurrency limiting"""
    job = jobs[job_id]

    async with download_semaphore:
        job.status = JobStatus.DOWNLOADING

        try:
            # Create downloads directory if it doesn't exist
            downloads_dir = os.path.join(os.getcwd(), 'downloads')
            os.makedirs(downloads_dir, exist_ok=True)

            unique_id = str(uuid.uuid4())[:8]
            height = job.resolution.replace('p', '')

            ydl_opts = {
                'format': f'bestvideo[height<={height}][vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[height<={height}]+bestaudio/best[height<={height}]/best',
                'outtmpl': os.path.join(downloads_dir, f'{unique_id}_%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'postprocessor_args': [
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-crf', '23',
                    '-preset', 'fast',
                ],
                'quiet': True,
                'no_warnings': True,
                'retries': 1,           # Reduced - we handle retries at app level with proxy rotation
                'fragment_retries': 2,  # Keep some for fragment issues
            }

            if PROXY_URL:
                ydl_opts['proxy'] = PROXY_URL
                print(f"[Download] Using proxy for job {job_id}")
            else:
                print(f"[Download] WARNING: No proxy configured for job {job_id}")

            # Run yt-dlp in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: _sync_download(ydl_opts, job.url, job))

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.result = result

            # Send webhook if configured
            if job.webhook_url:
                await send_webhook(job.webhook_url, {
                    "job_id": job_id,
                    "status": "completed",
                    "title": result["title"],
                    "resolution": result["resolution"],
                    "download_url": result["download_url"],
                    "filename": result["filename"]
                })

        except Exception as e:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now()
            job.error = str(e)

            # Send failure webhook if configured
            if job.webhook_url:
                await send_webhook(job.webhook_url, {
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(e)
                })

def _sync_download(ydl_opts: dict, url: str, job: Job = None, max_proxy_retries: int = 5) -> dict:
    """Synchronous download function with proxy rotation retry on 403 errors"""

    def progress_hook(d):
        """Update job progress from yt-dlp callback"""
        if job is None:
            return

        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)

            job.downloaded_bytes = downloaded
            job.total_bytes = total

            if total > 0:
                job.progress_percent = (downloaded / total) * 100

            # Format speed
            speed = d.get('speed')
            if speed:
                if speed >= 1024 * 1024:
                    job.speed = f"{speed / (1024 * 1024):.1f} MB/s"
                elif speed >= 1024:
                    job.speed = f"{speed / 1024:.1f} KB/s"
                else:
                    job.speed = f"{speed:.0f} B/s"

            # Format ETA
            eta = d.get('eta')
            if eta:
                if eta >= 3600:
                    job.eta = f"{eta // 3600}h {(eta % 3600) // 60}m"
                elif eta >= 60:
                    job.eta = f"{eta // 60}m {eta % 60}s"
                else:
                    job.eta = f"{eta}s"

        elif d['status'] == 'finished':
            job.progress_percent = 100
            job.eta = "Processing..."

    # Add progress hook to options
    ydl_opts_with_hook = ydl_opts.copy()
    ydl_opts_with_hook['progress_hooks'] = [progress_hook]

    last_error = None

    for attempt in range(max_proxy_retries):
        try:
            # Create fresh yt-dlp instance each attempt (new connection = new ProxyJet IP)
            with yt_dlp.YoutubeDL(ydl_opts_with_hook) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'video')
                actual_height = info.get('height', 'unknown')

                downloaded_file = ydl.prepare_filename(info)
                if not os.path.exists(downloaded_file):
                    downloaded_file = os.path.splitext(downloaded_file)[0] + '.mp4'

                filename = os.path.basename(downloaded_file)

                return {
                    "title": title,
                    "resolution": f"{actual_height}p",
                    "download_url": f"/files/{filename}",
                    "filename": filename
                }

        except yt_dlp.utils.DownloadError as e:
            error_str = str(e).lower()
            if '403' in error_str or 'forbidden' in error_str:
                last_error = e
                print(f"[Download] 403 error on attempt {attempt + 1}/{max_proxy_retries}, rotating proxy...")
                if attempt < max_proxy_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s, 8s
                continue  # Retry with new yt-dlp instance
            else:
                raise  # Non-403 errors fail immediately

    # All retries exhausted
    raise last_error or Exception("Download failed after all proxy rotation attempts")

class DownloadRequestNoWebhook(BaseModel):
    url: str
    resolution: str = "1080p"

# New async endpoint with webhook support
@app.post("/download")
async def queue_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    """Queue a video download and receive results via webhook"""
    job_id = str(uuid.uuid4())

    job = Job(
        job_id=job_id,
        status=JobStatus.QUEUED,
        url=request.url,
        resolution=request.resolution,
        webhook_url=str(request.webhook_url),
        created_at=datetime.now()
    )
    jobs[job_id] = job

    # Start background download
    background_tasks.add_task(download_worker, job_id)

    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Download queued. Results will be sent to your webhook URL."
    }

# Async endpoint without webhook - use SSE for progress
@app.post("/download/async")
async def queue_download_async(request: DownloadRequestNoWebhook, background_tasks: BackgroundTasks):
    """Queue a video download and track progress via SSE at /jobs/{job_id}/progress"""
    job_id = str(uuid.uuid4())

    job = Job(
        job_id=job_id,
        status=JobStatus.QUEUED,
        url=request.url,
        resolution=request.resolution,
        webhook_url=None,
        created_at=datetime.now()
    )
    jobs[job_id] = job

    # Start background download
    background_tasks.add_task(download_worker, job_id)

    return {
        "job_id": job_id,
        "status": "queued",
        "progress_url": f"/jobs/{job_id}/progress",
        "message": "Download queued. Stream progress via SSE at the progress_url."
    }

# Job status endpoint
@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Check the status of a download job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return {
        "job_id": job.job_id,
        "status": job.status,
        "url": job.url,
        "resolution": job.resolution,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "result": job.result,
        "error": job.error,
        "progress_percent": job.progress_percent,
        "downloaded_bytes": job.downloaded_bytes,
        "total_bytes": job.total_bytes,
        "speed": job.speed,
        "eta": job.eta
    }

# SSE Progress endpoint
@app.get("/jobs/{job_id}/progress")
async def stream_job_progress(job_id: str):
    """Stream download progress via Server-Sent Events"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        last_progress = -1
        while True:
            if job_id not in jobs:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break

            job = jobs[job_id]
            current_progress = job.progress_percent

            # Send update if progress changed or status changed
            if current_progress != last_progress or job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                event_data = {
                    "job_id": job_id,
                    "status": job.status.value,
                    "progress_percent": round(job.progress_percent, 1),
                    "downloaded_bytes": job.downloaded_bytes,
                    "total_bytes": job.total_bytes,
                    "speed": job.speed,
                    "eta": job.eta
                }

                if job.status == JobStatus.COMPLETED:
                    event_data["result"] = job.result
                    yield f"data: {json.dumps(event_data)}\n\n"
                    break
                elif job.status == JobStatus.FAILED:
                    event_data["error"] = job.error
                    yield f"data: {json.dumps(event_data)}\n\n"
                    break

                yield f"data: {json.dumps(event_data)}\n\n"
                last_progress = current_progress

            await asyncio.sleep(0.5)  # Check every 500ms

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# Keep original sync endpoint for backwards compatibility
@app.get("/download")
async def download_video(url: str, resolution: str = "1080p"):
    try:
        # Create downloads directory if it doesn't exist
        downloads_dir = os.path.join(os.getcwd(), 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)

        # Generate unique filename to avoid conflicts
        unique_id = str(uuid.uuid4())[:8]

        # Convert resolution format (e.g., "1080p" -> "1080")
        height = resolution.replace('p', '')

        # Configure yt-dlp options
        ydl_opts = {
            'format': f'bestvideo[height<={height}][vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[height<={height}]+bestaudio/best[height<={height}]/best',
            'outtmpl': os.path.join(downloads_dir, f'{unique_id}_%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'postprocessor_args': [
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-crf', '23',
                '-preset', 'fast',
            ],
            'quiet': True,
            'no_warnings': True,
        }

        # Add proxy if configured
        if PROXY_URL:
            ydl_opts['proxy'] = PROXY_URL

        # Add reduced retries - we handle proxy rotation at app level
        ydl_opts['retries'] = 1
        ydl_opts['fragment_retries'] = 2

        # Download with proxy rotation retry on 403 errors
        max_proxy_retries = 5
        last_error = None

        for attempt in range(max_proxy_retries):
            try:
                # Create fresh yt-dlp instance each attempt (new connection = new ProxyJet IP)
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get('title', 'video')
                    actual_height = info.get('height', 'unknown')

                    # Get the actual downloaded filename
                    downloaded_file = ydl.prepare_filename(info)
                    # Handle potential format conversion
                    if not os.path.exists(downloaded_file):
                        downloaded_file = os.path.splitext(downloaded_file)[0] + '.mp4'

                    filename = os.path.basename(downloaded_file)

                # Generate download URL
                download_url = f"/files/{filename}"

                return {
                    "message": f"Video '{title}' downloaded successfully in {actual_height}p!",
                    "title": title,
                    "resolution": f"{actual_height}p",
                    "download_url": download_url,
                    "filename": filename
                }

            except yt_dlp.utils.DownloadError as e:
                error_str = str(e).lower()
                if '403' in error_str or 'forbidden' in error_str:
                    last_error = e
                    print(f"[Download] 403 error on attempt {attempt + 1}/{max_proxy_retries}, rotating proxy...")
                    if attempt < max_proxy_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s, 8s
                    continue  # Retry with new yt-dlp instance
                else:
                    raise  # Non-403 errors fail immediately

        # All retries exhausted
        raise last_error or Exception("Download failed after all proxy rotation attempts")

    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=f"Error: Video is not available or cannot be downloaded - {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error downloading video: " + str(e))

@app.get("/files/{filename}")
async def get_file(filename: str):
    """Serve downloaded video files"""
    file_path = os.path.join(os.getcwd(), 'downloads', filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Security: Ensure the file is within the downloads directory
    if not os.path.abspath(file_path).startswith(os.path.abspath(os.path.join(os.getcwd(), 'downloads'))):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        path=file_path,
        media_type='video/mp4',
        filename=filename
    )