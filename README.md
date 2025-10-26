# YouTube Downloader API

A simple FastAPI-based web service for downloading YouTube videos in MP4 format with H.264 encoding.

## Features

- Download YouTube videos via REST API or web interface
- Configurable resolution (defaults to 1080p)
- Automatic conversion to H.264/MP4 for maximum compatibility
- Videos saved to organized `downloads/` folder

## Installation

### Requirements

- Python 3.13+
- FFmpeg (for video conversion)

### Setup

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

### Web Interface

Open your browser and navigate to:
```
http://127.0.0.1:8000
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
curl "http://127.0.0.1:8000/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&resolution=1080p"
```

**Success Response:**
```json
{
  "message": "Video 'Rick Astley - Never Gonna Give You Up' downloaded successfully to downloads/ folder in 1080p!"
}
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

# Download a video in 720p
response = requests.get(
    "http://127.0.0.1:8000/download",
    params={
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "resolution": "720p"
    }
)

if response.status_code == 200:
    print(response.json()["message"])
else:
    print(f"Error: {response.json()['detail']}")
```

### JavaScript Example

```javascript
async function downloadVideo(url, resolution = '1080p') {
    const response = await fetch(
        `http://127.0.0.1:8000/download?url=${encodeURIComponent(url)}&resolution=${resolution}`
    );

    const data = await response.json();

    if (response.ok) {
        console.log(data.message);
    } else {
        console.error(data.detail);
    }
}

// Usage
downloadVideo('https://www.youtube.com/watch?v=dQw4w9WgXcQ', '720p');
```

### cURL Examples

**Download in default 1080p:**
```bash
curl "http://127.0.0.1:8000/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

**Download in 720p:**
```bash
curl "http://127.0.0.1:8000/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&resolution=720p"
```

**Download in 4K:**
```bash
curl "http://127.0.0.1:8000/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&resolution=2160p"
```

## Output

All downloaded videos are saved to the `downloads/` folder in your project directory with the format:
```
downloads/[Video Title].mp4
```

## Video Format

All videos are automatically converted to:
- **Container:** MP4
- **Video Codec:** H.264 (libx264)
- **Audio Codec:** AAC
- **Quality:** CRF 23 (balanced quality/file size)

This ensures maximum compatibility across all devices and players.

## API Documentation

FastAPI provides interactive API documentation:

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

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

## Tech Stack

- **FastAPI** - Modern Python web framework
- **yt-dlp** - Robust YouTube downloader
- **FFmpeg** - Video conversion and processing
- **Uvicorn** - ASGI server

## License

This tool is for personal and educational use only. Please respect YouTube's Terms of Service.
