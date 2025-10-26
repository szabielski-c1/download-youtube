from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import yt_dlp
import os

app = FastAPI()

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
                        message.textContent = data.message;
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

        # Convert resolution format (e.g., "1080p" -> "1080")
        height = resolution.replace('p', '')

        # Configure yt-dlp options
        ydl_opts = {
            'format': f'bestvideo[height<={height}][vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[height<={height}]+bestaudio/best[height<={height}]/best',
            'outtmpl': os.path.join(downloads_dir, '%(title)s.%(ext)s'),
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

        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')
            actual_height = info.get('height', 'unknown')

        return {"message": f"Video '{title}' downloaded successfully to downloads/ folder in {actual_height}p!"}

    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=f"Error: Video is not available or cannot be downloaded - {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error downloading video: " + str(e))