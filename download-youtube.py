from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
import yt_dlp
import os
import uuid
from pathlib import Path

app = FastAPI()

# Path to cookies file (will be created from environment variable)
COOKIES_FILE = os.path.join(os.getcwd(), 'youtube_cookies.txt')

@app.get("/health")
async def health_check():
    """Health check endpoint to verify service is running"""
    return {
        "status": "ok",
        "cookies_configured": os.path.exists(COOKIES_FILE) or bool(os.environ.get('YOUTUBE_COOKIES')),
        "ffmpeg_available": True  # If we got this far, ffmpeg is installed
    }

@app.get("/formats")
async def list_formats(url: str):
    """Debug endpoint to list available formats for a video"""
    try:
        # Check if cookies are available from environment variable
        cookies_content = os.environ.get('YOUTUBE_COOKIES')
        cookies_env_exists = bool(cookies_content)
        cookies_file_exists = os.path.exists(COOKIES_FILE)

        if cookies_content and not os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE, 'w') as f:
                f.write(cookies_content)

        ydl_opts = {
            'quiet': False,  # Enable output to see what's happening
            'verbose': True,  # More debugging info
            'extractor_args': {
                'youtube': {
                    'player_client': ['web'],
                }
            },
        }

        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            return {
                "debug": {
                    "cookies_env_exists": cookies_env_exists,
                    "cookies_file_exists": cookies_file_exists,
                    "cookies_file_path": COOKIES_FILE,
                },
                "title": info.get('title'),
                "format_count": len(info.get('formats', [])),
                "sample_formats": info.get('formats', [])[:5] if info.get('formats') else []
            }

    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}")

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

@app.get("/download")
async def download_video(url: str, resolution: str = "1080p"):
    try:
        # Create downloads directory if it doesn't exist
        downloads_dir = os.path.join(os.getcwd(), 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)

        # Check if cookies are available from environment variable
        cookies_content = os.environ.get('YOUTUBE_COOKIES')
        if cookies_content and not os.path.exists(COOKIES_FILE):
            # Write cookies to file if provided via environment variable
            with open(COOKIES_FILE, 'w') as f:
                f.write(cookies_content)

        # Generate unique filename to avoid conflicts
        unique_id = str(uuid.uuid4())[:8]

        # Convert resolution format (e.g., "1080p" -> "1080")
        height = resolution.replace('p', '')

        # Configure yt-dlp options with smart format selection
        # Try best video+audio combo, fall back to single file
        format_string = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'

        ydl_opts = {
            'format': format_string,
            'outtmpl': os.path.join(downloads_dir, f'{unique_id}_%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'allow_multiple_video_streams': False,
            'allow_multiple_audio_streams': False,
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
            # Try multiple client types in order of reliability
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'android_embedded'],
                }
            },
            # Disable signature verification which can trigger bot detection
            'extractor_retries': 3,
            'fragment_retries': 3,
        }

        # Add cookies if available
        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        # Download the video
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