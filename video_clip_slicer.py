import os
import subprocess

VIDEO_ROOT = r"C:\\Users\\sahil\\Downloads\\AIVideos\\processed_data"
CLIP_OUTPUT = r"C:\\Users\\sahil\\Downloads\\AIVideos\\clips_output"
os.makedirs(CLIP_OUTPUT, exist_ok=True)

def find_video_path(video_key):
    """Search for the actual .mp4 file matching the video_key."""
    for root, _, files in os.walk(VIDEO_ROOT):
        for f in files:
            if f == f"{video_key}.mp4":
                return os.path.join(root, f)
    return None

def slice_clip(video_path, start, end, output_path):
    """Use FFmpeg to extract a clip between start and end timestamps."""
    cmd = [
        "ffmpeg", "-ss", start, "-to", end,
        "-i", video_path, "-c:v", "copy", "-c:a", "copy", "-y", output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return output_path if result.returncode == 0 else None
