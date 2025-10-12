import os
import logging
import webvtt
import subprocess
from datetime import datetime
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = MongoClient("mongodb://localhost:27017/")
db = client["video_rag"]
questions_col = db["questions"]


def extract_subtitles(vtt_file):
    subtitles = []
    for caption in webvtt.read(vtt_file):
        subtitles.append({
            "start": caption.start,
            "end": caption.end,
            "text": caption.text
        })
    return subtitles


def get_midpoint_timestamp(start, end):
    fmt = "%H:%M:%S.%f"
    t1 = datetime.strptime(start, fmt)
    t2 = datetime.strptime(end, fmt)
    mid = t1 + (t2 - t1) / 2
    return mid.strftime("%H:%M:%S.%f")[:-3]


def extract_frame(video_path, timestamp, output_path):
    cmd = ["ffmpeg", "-ss", timestamp, "-i", video_path,
           "-frames:v", "1", "-q:v", "2", "-y", output_path]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def extract_frames_for_questions(video_key, video_path, frame_output_dir):
    video_doc = questions_col.find_one({"video_key": video_key})
    if not video_doc:
        return
    frame_dir = os.path.join(frame_output_dir, video_key)
    os.makedirs(frame_dir, exist_ok=True)
    updated_questions = []
    for i, q in enumerate(video_doc["questions"]):
        ts_mid = get_midpoint_timestamp(q["timestamp"]["start"], q["timestamp"]["end"])
        frame_name = f"q{i:04d}.jpg"
        frame_path = os.path.join(frame_dir, frame_name)
        extract_frame(video_path, ts_mid, frame_path)
        q["frame_path"] = frame_path
        q["frame_timestamp"] = ts_mid
        updated_questions.append(q)
    questions_col.update_one({"_id": video_doc["_id"]}, {"$set": {"questions": updated_questions}})


def process_all_videos(dataset_dir, frame_output_dir):
    video_paths = {}
    for root, _, files in os.walk(dataset_dir):
        for file in files:
            if file.endswith(".mp4"):
                video_key = os.path.splitext(file)[0]
                video_paths[video_key] = os.path.join(root, file)
    for video_key, video_path in video_paths.items():
        extract_frames_for_questions(video_key, video_path, frame_output_dir)