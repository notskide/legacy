import os
import subprocess
from flask import Flask, request, Response, render_template_string
import static_ffmpeg

static_ffmpeg.add_paths()
app = Flask(__name__)

VIDEOS = [
    {"title": "Me at the zoo", "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"},
    {"title": "Never Gonna Give You Up", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    {"title": "Charlie bit my finger", "url": "https://www.youtube.com/watch?v=_OBlgSz8sSM"},
    {"title": "Evolution of Dance", "url": "https://www.youtube.com/watch?v=dMH0bHeiRNg"}
]

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Legacy Proxy</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    body { font-family: "Times New Roman", Times, serif; background-color: #d4d0c8; color: #000; margin: 0; padding: 4px; max-width: 320px; }
    h1 { font-size: 16px; color: #000; border-bottom: 1px solid #808080; padding-bottom: 2px; margin-top: 2px; }
    ul { list-style-type: square; padding-left: 15px; margin: 5px 0; }
    li { margin-bottom: 8px; font-size: 14px; }
    a { color: #0000ff; text-decoration: underline; }
    a:visited { color: #800080; }
    .container { background-color: #ffffff; border: 1px solid #808080; padding: 4px; border-right-color: #ffffff; border-bottom-color: #ffffff; box-shadow: 1px 1px 0px #000; }
    .video-container { text-align: center; margin-top: 5px; }
    video { max-width: 100%; border: 1px solid #000; background-color: #000; }
    .back-link { display: block; margin-top: 10px; font-size: 14px; text-align: center; font-weight: bold; }
</style>
</head>
<body>
<div class="container">
{% if mode == 'index' %}
    <h1>Video Directory</h1>
    <ul>
    {% for v in videos %}
        <li><a href="/watch?url={{ v.url }}">{{ v.title }}</a></li>
    {% endfor %}
    </ul>
{% elif mode == 'watch' %}
    <h1>Media Player</h1>
    <div class="video-container">
        <video controls autoplay>
            <source src="/stream?url={{ video_url }}" type="video/mp4">
        </video>
    </div>
    <a class="back-link" href="/">&lt;&lt; Return</a>
{% endif %}
</div>
</body>
</html>
"""

def get_stream_url(video_url):
    command = [
        "yt-dlp",
        "-f", "b[height<=360][ext=mp4]/b[height<=240]",
        "--get-url",
        video_url
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return result.stdout.strip()

@app.route("/")
def home():
    return render_template_string(INDEX_HTML, mode='index', videos=VIDEOS)

@app.route("/watch")
def watch():
    video_url = request.args.get("url")
    return render_template_string(INDEX_HTML, mode='watch', video_url=video_url)

@app.route("/stream")
def stream_video():
    video_url = request.args.get("url", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    try:
        stream_url = get_stream_url(video_url)
    except subprocess.CalledProcessError:
        return Response("Error", status=500)

    ffmpeg_command = [
        "ffmpeg",
        "-i", stream_url,
        "-vf", "scale=320:-2",
        "-c:v", "libx264",
        "-profile:v", "baseline",
        "-level", "3.0",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-c:a", "aac",
        "-b:a", "64k",
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
