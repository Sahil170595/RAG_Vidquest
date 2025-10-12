"""
Data Migration Script for RAG Vidquest

This script copies and integrates the video data from Downloads/AIVideos
into the enterprise-grade RAG Vidquest system structure.
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Source and destination paths
SOURCE_BASE = Path(r"C:\Users\sahil\Downloads\AIVideos")
DEST_BASE = Path("./data")

def create_directory_structure():
    """Create the enterprise data directory structure."""
    directories = [
        "videos",
        "subtitles", 
        "frames",
        "clips",
        "processed",
        "embeddings",
        "metadata"
    ]
    
    for directory in directories:
        (DEST_BASE / directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {DEST_BASE / directory}")

def copy_video_files():
    """Copy video files from source to destination."""
    logger.info("Copying video files...")
    
    # Copy from shard directories
    shard_dirs = [d for d in SOURCE_BASE.glob("processed_data/shard-*") if d.is_dir()]
    
    video_count = 0
    for shard_dir in shard_dirs:
        videos_dir = shard_dir / "videos"
        if videos_dir.exists():
            for video_dir in videos_dir.iterdir():
                if video_dir.is_dir():
                    video_id = video_dir.name
                    
                    # Create destination directory
                    dest_dir = DEST_BASE / "videos" / video_id
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Copy video files
                    for file in video_dir.iterdir():
                        if file.is_file():
                            dest_file = dest_dir / file.name
                            shutil.copy2(file, dest_file)
                            logger.info(f"Copied: {file} -> {dest_file}")
                            video_count += 1
    
    logger.info(f"Copied {video_count} video files")

def copy_subtitle_files():
    """Copy subtitle files from source to destination."""
    logger.info("Copying subtitle files...")
    
    subtitles_source = SOURCE_BASE / "subtitles_output"
    if not subtitles_source.exists():
        logger.warning("Subtitles source directory not found")
        return
    
    subtitle_count = 0
    for subtitle_dir in subtitles_source.iterdir():
        if subtitle_dir.is_dir():
            video_id = subtitle_dir.name
            
            # Create destination directory
            dest_dir = DEST_BASE / "subtitles" / video_id
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy subtitle files
            for file in subtitle_dir.iterdir():
                if file.is_file():
                    dest_file = dest_dir / file.name
                    shutil.copy2(file, dest_file)
                    logger.info(f"Copied subtitle: {file} -> {dest_file}")
                    subtitle_count += 1
    
    logger.info(f"Copied {subtitle_count} subtitle files")

def copy_frame_files():
    """Copy frame files from source to destination."""
    logger.info("Copying frame files...")
    
    frames_source = SOURCE_BASE / "frames_output"
    if not frames_source.exists():
        logger.warning("Frames source directory not found")
        return
    
    frame_count = 0
    for frame_dir in frames_source.iterdir():
        if frame_dir.is_dir():
            video_id = frame_dir.name
            
            # Create destination directory
            dest_dir = DEST_BASE / "frames" / video_id
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy frame files
            for file in frame_dir.iterdir():
                if file.is_file():
                    dest_file = dest_dir / file.name
                    shutil.copy2(file, dest_file)
                    logger.info(f"Copied frame: {file} -> {dest_file}")
                    frame_count += 1
    
    logger.info(f"Copied {frame_count} frame files")

def copy_clip_files():
    """Copy clip files from source to destination."""
    logger.info("Copying clip files...")
    
    clips_source = SOURCE_BASE / "clips_output"
    if not clips_source.exists():
        logger.warning("Clips source directory not found")
        return
    
    clip_count = 0
    for file in clips_source.iterdir():
        if file.is_file() and file.suffix == '.mp4':
            dest_file = DEST_BASE / "clips" / file.name
            shutil.copy2(file, dest_file)
            logger.info(f"Copied clip: {file} -> {dest_file}")
            clip_count += 1
    
    logger.info(f"Copied {clip_count} clip files")

def process_metadata():
    """Process and consolidate metadata files."""
    logger.info("Processing metadata files...")
    
    # Process frame JSON files
    frame_files = list(SOURCE_BASE.glob("videos_*_frames.json"))
    
    consolidated_metadata = {
        "videos": {},
        "frames": {},
        "subtitles": {},
        "clips": {},
        "created_at": str(Path().cwd()),
        "source": str(SOURCE_BASE)
    }
    
    for frame_file in frame_files:
        try:
            with open(frame_file, 'r', encoding='utf-8') as f:
                frame_data = json.load(f)
            
            video_id = frame_file.stem.replace('_frames', '')
            consolidated_metadata["frames"][video_id] = frame_data
            
            logger.info(f"Processed frame metadata: {video_id}")
            
        except Exception as e:
            logger.error(f"Error processing {frame_file}: {e}")
    
    # Process question files
    questions_dir = SOURCE_BASE / "questions"
    if questions_dir.exists():
        question_files = [
            "gemma_questions.json",
            "gemma3_subtitle_questions.json", 
            "llm_subtitle_questions.json",
            "subtitle_questions.json"
        ]
        
        for q_file in question_files:
            q_path = questions_dir / q_file
            if q_path.exists():
                try:
                    with open(q_path, 'r', encoding='utf-8') as f:
                        question_data = json.load(f)
                    
                    consolidated_metadata["questions"] = question_data
                    logger.info(f"Processed questions: {q_file}")
                    
                except Exception as e:
                    logger.error(f"Error processing {q_file}: {e}")
    
    # Save consolidated metadata
    metadata_file = DEST_BASE / "metadata" / "consolidated_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(consolidated_metadata, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved consolidated metadata: {metadata_file}")

def create_data_inventory():
    """Create an inventory of all copied data."""
    logger.info("Creating data inventory...")
    
    inventory = {
        "videos": {},
        "subtitles": {},
        "frames": {},
        "clips": {},
        "total_files": 0,
        "total_size_mb": 0
    }
    
    # Inventory videos
    videos_dir = DEST_BASE / "videos"
    if videos_dir.exists():
        for video_dir in videos_dir.iterdir():
            if video_dir.is_dir():
                video_files = list(video_dir.glob("*"))
                inventory["videos"][video_dir.name] = {
                    "files": [f.name for f in video_files],
                    "count": len(video_files)
                }
                inventory["total_files"] += len(video_files)
                
                # Calculate size
                for file in video_files:
                    if file.is_file():
                        inventory["total_size_mb"] += file.stat().st_size / (1024 * 1024)
    
    # Inventory subtitles
    subtitles_dir = DEST_BASE / "subtitles"
    if subtitles_dir.exists():
        for subtitle_dir in subtitles_dir.iterdir():
            if subtitle_dir.is_dir():
                subtitle_files = list(subtitle_dir.glob("*"))
                inventory["subtitles"][subtitle_dir.name] = {
                    "files": [f.name for f in subtitle_files],
                    "count": len(subtitle_files)
                }
                inventory["total_files"] += len(subtitle_files)
    
    # Inventory frames
    frames_dir = DEST_BASE / "frames"
    if frames_dir.exists():
        for frame_dir in frames_dir.iterdir():
            if frame_dir.is_dir():
                frame_files = list(frame_dir.glob("*"))
                inventory["frames"][frame_dir.name] = {
                    "files": [f.name for f in frame_files],
                    "count": len(frame_files)
                }
                inventory["total_files"] += len(frame_files)
    
    # Inventory clips
    clips_dir = DEST_BASE / "clips"
    if clips_dir.exists():
        clip_files = list(clips_dir.glob("*.mp4"))
        inventory["clips"] = {
            "files": [f.name for f in clip_files],
            "count": len(clip_files)
        }
        inventory["total_files"] += len(clip_files)
    
    # Save inventory
    inventory_file = DEST_BASE / "metadata" / "data_inventory.json"
    with open(inventory_file, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Created data inventory: {inventory_file}")
    logger.info(f"Total files copied: {inventory['total_files']}")
    logger.info(f"Total size: {inventory['total_size_mb']:.2f} MB")

def update_configuration():
    """Update configuration to point to the new data location."""
    logger.info("Updating configuration...")
    
    # Update the configuration file to point to the new data location
    config_update = {
        "paths": {
            "video_root": "./data/videos",
            "clip_output": "./data/clips", 
            "frame_output": "./data/frames",
            "subtitle_output": "./data/subtitles"
        },
        "data_migration": {
            "completed": True,
            "source": str(SOURCE_BASE),
            "destination": str(DEST_BASE),
            "migration_date": str(Path().cwd())
        }
    }
    
    config_file = Path("./data/migration_config.json")
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_update, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Updated configuration: {config_file}")

def main():
    """Main migration function."""
    logger.info("Starting RAG Vidquest data migration...")
    
    try:
        # Create directory structure
        create_directory_structure()
        
        # Copy all data files
        copy_video_files()
        copy_subtitle_files()
        copy_frame_files()
        copy_clip_files()
        
        # Process metadata
        process_metadata()
        
        # Create inventory
        create_data_inventory()
        
        # Update configuration
        update_configuration()
        
        logger.info("Data migration completed successfully!")
        
        # Print summary
        print("\n" + "="*60)
        print("RAG VIDQUEST DATA MIGRATION COMPLETE")
        print("="*60)
        print(f"Source: {SOURCE_BASE}")
        print(f"Destination: {DEST_BASE}")
        print("\nData Structure:")
        print(f"├── videos/     (Video files)")
        print(f"├── subtitles/  (Subtitle files)")
        print(f"├── frames/     (Extracted frames)")
        print(f"├── clips/      (Generated clips)")
        print(f"└── metadata/   (Consolidated metadata)")
        print("\nNext Steps:")
        print("1. Start the enterprise RAG Vidquest system:")
        print("   docker-compose up -d")
        print("2. Access the API at: http://localhost:8000/docs")
        print("3. Query your video data using the REST API")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    main()
