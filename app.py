import os
import subprocess
from flask import Flask, request, Response

# Automatically downloads and sets up FFmpeg on Render without root access
import static_ffmpeg
static_ffmpeg.add_paths()

app = Flask(__name__)

def get_stream_url(video_url):
    command = [
        "yt-dlp",
        # Force low resolution to save server bandwidth and decoding power
        "-f", "b[height<=360][ext=mp4]/b[height<=240]",
        "--get-url",
        video_url
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return result.stdout.strip()

@app.route("/stream")
def stream_video():
    video_url = request.args.get("url", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    try:
        stream_url = get_stream_url(video_url)
    except subprocess.CalledProcessError:
        return Response("Failed to extract video URL", status=500)

    # FFmpeg tuned for legacy mobile hardware (H.264 Baseline, low resolution, AAC)
    ffmpeg_command = [
        "ffmpeg",
        "-i", stream_url,
        "-vf", "scale=320:-2",               # Downscale width to 320px
        "-c:v", "libx264",                   # Transcode to H.264
        "-profile:v", "baseline",            # Constrained Baseline Profile for old GPUs
        "-level", "3.0",
        "-preset", "ultrafast",              # Fast encoding
        "-tune", "zerolatency",
        "-c:a", "aac",                       # Standard AAC audio output
        "-b:a", "64k",                       # Low audio bitrate
        "-f", "mp4",
        "-movflags", "frag_keyframe+empty_moov",
        "pipe:1"
    ]

    def generate():
        process = subprocess.Popen(
            ffmpeg_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        try:
            while True:
                chunk = process.stdout.read(4096)
                if not chunk:
                    break
                yield chunk
        finally:
            process.terminate()

    return Response(generate(), mimetype="video/mp4")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
