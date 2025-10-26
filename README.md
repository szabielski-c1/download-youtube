# YouTube Downloader API

A simple FastAPI-based web service for downloading YouTube videos in MP4 format with H.264 encoding.

## Features

- Download YouTube videos via REST API or web interface
- Configurable resolution (defaults to 1080p)
- Automatic conversion to H.264/MP4 for maximum compatibility
- Videos saved to organized `downloads/` folder
- One-click deployment to Railway

## Quick Start

### Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)

1. Click the "Deploy on Railway" button above
2. Connect your GitHub account and select this repository
3. Railway will automatically detect and deploy the application
4. Once deployed, Railway will provide your public URL

**Live Demo:** [https://download-youtube-production-f849.up.railway.app](https://download-youtube-production-f849.up.railway.app)

### Local Development

#### Requirements

- Python 3.13+
- FFmpeg (for video conversion)

#### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
uvicorn download-youtube:app --reload
```

The server will run on `http://127.0.0.1:8000`

## Usage

> **Note:** Replace `http://127.0.0.1:8000` with your Railway deployment URL when using the deployed version.

### Web Interface

Open your browser and navigate to:
```
# Local development
http://127.0.0.1:8000

# Railway deployment
https://download-youtube-production-f849.up.railway.app
```

Use the form to:
1. Enter a YouTube URL
2. Select desired resolution (240p - 4K)
3. Click "Download Video"

### API Endpoint

#### Download Video

**Endpoint:** `GET /download`

**Parameters:**
- `url` (required): YouTube video URL
- `resolution` (optional): Desired resolution. Default: `1080p`
  - Supported values: `240p`, `360p`, `480p`, `720p`, `1080p`, `1440p`, `2160p`

**Example Request:**
```bash
# Local development
curl "http://127.0.0.1:8000/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&resolution=1080p"

# Railway deployment
curl "https://download-youtube-production-f849.up.railway.app/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&resolution=1080p"
```

**Success Response:**
```json
{
  "message": "Video 'Rick Astley - Never Gonna Give You Up' downloaded successfully in 1080p!",
  "title": "Rick Astley - Never Gonna Give You Up",
  "resolution": "1080p",
  "download_url": "/files/a1b2c3d4_Rick Astley - Never Gonna Give You Up.mp4",
  "filename": "a1b2c3d4_Rick Astley - Never Gonna Give You Up.mp4"
}
```

The `download_url` is a relative path. To download the file, make a GET request to:
```
https://download-youtube-production-f849.up.railway.app/files/{filename}
```

**Error Response:**
```json
{
  "detail": "Error: Video is not available or cannot be downloaded"
}
```

### Python Example

```python
import requests

# Set your API base URL
BASE_URL = "http://127.0.0.1:8000"  # Local development
# BASE_URL = "https://download-youtube-production-f849.up.railway.app"  # Railway deployment

# Step 1: Request video download
response = requests.get(
    f"{BASE_URL}/download",
    params={
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "resolution": "720p"
    }
)

if response.status_code == 200:
    data = response.json()
    print(data["message"])

    # Step 2: Download the video file
    download_url = f"{BASE_URL}{data['download_url']}"
    filename = data['filename']

    video_response = requests.get(download_url)
    with open(filename, 'wb') as f:
        f.write(video_response.content)

    print(f"Video saved as: {filename}")
else:
    print(f"Error: {response.json()['detail']}")
```

### JavaScript Example

```javascript
// Set your API base URL
const BASE_URL = 'http://127.0.0.1:8000';  // Local development
// const BASE_URL = 'https://download-youtube-production-f849.up.railway.app';  // Railway deployment

async function downloadVideo(url, resolution = '1080p') {
    // Step 1: Request video download
    const response = await fetch(
        `${BASE_URL}/download?url=${encodeURIComponent(url)}&resolution=${resolution}`
    );

    const data = await response.json();

    if (response.ok) {
        console.log(data.message);
        console.log('Download URL:', `${BASE_URL}${data.download_url}`);

        // Step 2: Trigger browser download
        const downloadUrl = `${BASE_URL}${data.download_url}`;
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = data.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    } else {
        console.error(data.detail);
    }
}

// Usage
downloadVideo('https://www.youtube.com/watch?v=dQw4w9WgXcQ', '720p');
```

### cURL Examples

**Step 1: Request video download and get download URL**
```bash
# Local
curl "http://127.0.0.1:8000/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&resolution=720p"

# Railway
curl "https://download-youtube-production-f849.up.railway.app/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&resolution=720p"
```

**Step 2: Download the video file using the returned download_url**
```bash
# Railway example (replace {filename} with actual filename from response)
curl -O "https://download-youtube-production-f849.up.railway.app/files/{filename}"
```

**Complete example with jq (JSON processor):**
```bash
# Get the video info and extract download URL
RESPONSE=$(curl -s "https://download-youtube-production-f849.up.railway.app/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&resolution=720p")
DOWNLOAD_URL=$(echo $RESPONSE | jq -r '.download_url')
FILENAME=$(echo $RESPONSE | jq -r '.filename')

# Download the actual video file
curl -o "$FILENAME" "https://download-youtube-production-f849.up.railway.app${DOWNLOAD_URL}"
echo "Downloaded: $FILENAME"
```

## API Endpoints

### `GET /download`
Initiates a video download and returns the download URL.

**Returns:** JSON with video information and download URL

### `GET /files/{filename}`
Serves the downloaded video file.

**Returns:** MP4 video file

## Output

All downloaded videos are saved to the `downloads/` folder with the format:
```
downloads/[unique_id]_[Video Title].mp4
```

Each file has a unique ID prefix to prevent filename conflicts.

## Video Format

All videos are automatically converted to:
- **Container:** MP4
- **Video Codec:** H.264 (libx264)
- **Audio Codec:** AAC
- **Quality:** CRF 23 (balanced quality/file size)

This ensures maximum compatibility across all devices and players.

## API Documentation

FastAPI provides interactive API documentation:

**Local Development:**
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

**Railway Deployment:**
- **Swagger UI:** https://download-youtube-production-f849.up.railway.app/docs
- **ReDoc:** https://download-youtube-production-f849.up.railway.app/redoc

## Notes

- If the requested resolution is not available, the app will download the closest available resolution
- Download time varies based on video size and internet speed
- Videos with video-only or audio-only streams will be automatically merged
- Some videos may require conversion to H.264, which adds processing time

## Error Handling

Common errors:

| Error | Cause | Solution |
|-------|-------|----------|
| `Video is not available` | Video is private, deleted, or age-restricted | Check the URL and video availability |
| `Invalid URL` | Malformed YouTube URL | Ensure the URL is a valid YouTube link |
| `Error downloading video` | Network or permission issues | Check internet connection and disk space |

## Deployment Configuration

The application is configured for Railway deployment with:

- **Port binding:** Automatically uses Railway's `$PORT` environment variable
- **Host configuration:** Binds to `0.0.0.0` for external access
- **Restart policy:** Automatically restarts on failure (up to 10 retries)
- **Build system:** Uses Nixpacks for automatic Python environment setup

### Railway Configuration Files

- `railway.json` - Deployment configuration
- `Procfile` - Process start command
- `requirements.txt` - Python dependencies

### Environment Variables

No additional environment variables are required for basic operation. Railway automatically provides:
- `PORT` - The port your application should listen on

## Tech Stack

- **FastAPI** - Modern Python web framework
- **yt-dlp** - Robust YouTube downloader
- **FFmpeg** - Video conversion and processing
- **Uvicorn** - ASGI server
- **Railway** - Deployment platform

## License

This tool is for personal and educational use only. Please respect YouTube's Terms of Service.
