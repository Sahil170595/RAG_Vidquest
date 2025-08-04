import os
import webvtt
import logging
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = MongoClient("mongodb://localhost:27017/")
db = client["video_rag"]
subs_col = db["subtitles"]

def extract_subtitles(vtt_file):
    subtitles = []
    try:
        for caption in webvtt.read(vtt_file):
            subtitles.append({
                "start": caption.start,
                "end": caption.end,
                "text": caption.text.strip()
            })
    except Exception as e:
        logger.error(f"Error reading {vtt_file}: {e}")
    return subtitles

def process_vtt_files(dataset_dir):
    logger.info(f"Scanning for VTT files in {dataset_dir}...")
    count = 0
    for root, _, files in os.walk(dataset_dir):
        for f in files:
            if f.endswith(".vtt"):
                video_key = os.path.splitext(f)[0]
                full_path = os.path.join(root, f)
                subtitles = extract_subtitles(full_path)
                if subtitles:
                    subs_col.update_one(
                        {"video_key": video_key},
                        {"$set": {"video_key": video_key, "subtitles": subtitles}},
                        upsert=True
                    )
                    count += 1
    logger.info(f"✅ Processed {count} subtitle files.")

if __name__ == "__main__":
    dataset_dir = r"C:\\Users\\sahil\\Downloads\\AIVideos\\processed_data"
    process_vtt_files(dataset_dir)
